"""Secret redaction: one module, applied wherever text leaves the process.

Layered, and failing closed (it would rather mask too much than leak):

1. **Known secrets.** The exact values the run handles - the test accounts' passwords and every token the
   API issues - are registered the moment they enter the process (:func:`register_secret`) and masked
   wherever they appear, whatever surrounds them (the way CI systems mask secrets). This catches what no
   pattern anticipates, e.g. a password echoed inside an error message.
2. **Sensitive keys.** In structured data (JSON bodies, headers, dict reprs) a non-empty value whose key
   names a credential - password, token, secret, api key, authorization, cookie, session id, private key -
   is masked at any depth.
3. **Patterns.** Free text is scanned for the shapes secrets take: ``Bearer``/``Basic`` values, JWTs, and
   ``"key": "value"`` / ``key=value`` pairs with a sensitive key - for secrets that were never registered.

Exits it guards: assertion and error messages (``ApiResponse.describe``, transport and cleanup errors),
every record of the suite's loggers (:func:`get_logger`), and - as the last line of defence - every test
report (console, JUnit, HTML), via ``fixtures/reporting.py``. In memory, passwords and tokens are pydantic
``SecretStr``, so a repr or a traceback argument never shows them in the first place.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from pydantic import SecretStr

MASK = "***"

# Shorter values would mask ordinary words; the API itself requires passwords of at least 6 characters.
MIN_SECRET_LENGTH = 6

_SENSITIVE_KEY = re.compile(
    r"pass(?:word|wd|phrase)|pwd|secret|token|api[-_]?key|authori[sz]ation|cookie|session[-_]?id"
    r"|credential|private[-_]?key",
    re.IGNORECASE,
)
_AUTH_SCHEME = re.compile(r"\b(Bearer|Basic)\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*")
# "key": "value" and 'key': 'value' - JSON text and Python reprs (e.g. a dict in a traceback).
_QUOTED_PAIR = re.compile(
    r"""(?P<kq>["'])(?P<key>[^"'\\\n]{1,64})(?P=kq)(?P<sep>\s*:\s*)(?P<vq>["'])(?P<value>(?:\\.|(?!(?P=vq))[^\\\n])*)(?P=vq)"""
)
# key=value and key: value - query strings, form bodies, header lines, prose.
_PLAIN_PAIR = re.compile(r"(?P<key>\b[A-Za-z][\w-]{0,63})(?P<sep>\s*[=:]\s*)(?P<value>[^\s&;,'\"<>(){}\[\]|]+)")


def is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY.search(key))


class SecretRegistry:
    """The secret values this process has seen, masked verbatim wherever they appear."""

    def __init__(self) -> None:
        self._values: set[str] = set()
        self._pattern: re.Pattern[str] | None = None
        self._lock = threading.Lock()

    def register(self, secret: str | SecretStr | None) -> None:
        value = secret.get_secret_value() if isinstance(secret, SecretStr) else secret
        if not value or len(value) < MIN_SECRET_LENGTH:
            return
        # Also the forms a value takes inside JSON text and URLs.
        variants = {value, json.dumps(value)[1:-1], quote(value, safe="")}
        with self._lock:
            if not variants <= self._values:
                self._values |= variants
                self._pattern = None

    def mask(self, text: str) -> str:
        with self._lock:
            if self._pattern is None and self._values:
                longest_first = sorted(self._values, key=len, reverse=True)
                self._pattern = re.compile("|".join(re.escape(v) for v in longest_first))
            pattern = self._pattern
        return pattern.sub(MASK, text) if pattern else text

    def __len__(self) -> int:
        return len(self._values)


_registry = SecretRegistry()


def register_secret(secret: str | SecretStr | None) -> None:
    """Mask this value everywhere from now on (call where a secret enters the process)."""
    _registry.register(secret)


def redact_text(text: str) -> str:
    """Mask known secrets, credential-shaped values and sensitive key/value pairs in free text."""
    if not text:
        return text
    text = _registry.mask(text)
    text = _AUTH_SCHEME.sub(lambda m: f"{m.group(1)} {MASK}", text)
    text = _JWT.sub(MASK, text)
    text = _QUOTED_PAIR.sub(_mask_quoted_pair, text)
    return _PLAIN_PAIR.sub(_mask_plain_pair, text)


def redact_data(value: Any) -> Any:
    """Copy of JSON-like data with sensitive values masked (keys at any depth, then text in every string)."""
    if isinstance(value, Mapping):
        return {k: _mask_value(v) if is_sensitive_key(str(k)) else redact_data(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_data(v) for v in value]
    if isinstance(value, SecretStr):
        return MASK
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_body(text: str) -> str:
    """An HTTP body: masked structurally when it is JSON, as free text otherwise."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return redact_text(text)
    return json.dumps(redact_data(data), ensure_ascii=False)


class RedactingFilter(logging.Filter):
    """Redacts each record's final message (and traceback) before any handler sees it."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = None
        if record.exc_info and not record.exc_text:
            record.exc_text = redact_text(logging.Formatter().formatException(record.exc_info))
        if record.stack_info:
            record.stack_info = redact_text(record.stack_info)
        return True


_FILTER = RedactingFilter()


def get_logger(name: str) -> logging.Logger:
    """``logging.getLogger`` with redaction attached - the only way the suite creates loggers."""
    logger = logging.getLogger(name)
    if _FILTER not in logger.filters:
        logger.addFilter(_FILTER)
    return logger


def _mask_value(value: Any) -> Any:
    return value if value is None or value == "" else MASK  # keep "absent" visible: it is diagnostic


def _mask_quoted_pair(match: re.Match[str]) -> str:
    if not is_sensitive_key(match["key"]) or not match["value"]:
        return match[0]
    return f"{match['kq']}{match['key']}{match['kq']}{match['sep']}{match['vq']}{MASK}{match['vq']}"


def _mask_plain_pair(match: re.Match[str]) -> str:
    value = match["value"]
    if not is_sensitive_key(match["key"]) or value == MASK or value.lower() in {"bearer", "basic"}:
        return match[0]
    return f"{match['key']}{match['sep']}{MASK}"
