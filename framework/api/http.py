"""Thin HTTP layer on top of Playwright's ``APIRequestContext``.

* :class:`ApiResponse` reads the body eagerly and produces assertion messages that contain the full
  request/response story, so a failing API test is diagnosable from the report alone.
* :class:`BaseApiClient` is what every resource client (bookings, events, auth...) extends. It knows
  nothing about authentication - it is handed a request context that is already authenticated (or
  deliberately anonymous) by :mod:`framework.api.session`.
* :class:`HttpMethod` normalises the verb once (``"get"`` -> ``GET``) and owns the retry policy: only
  idempotent methods are retried, and only by Playwright's built-in, connection-reset-only retry.
* Everything that leaves this module (messages, logs) goes through :mod:`framework.utils.redaction`.
"""

from __future__ import annotations

import json
import time
from enum import Enum
from typing import Any, TypeVar

from playwright.sync_api import APIRequestContext
from playwright.sync_api import Error as PlaywrightError
from pydantic import BaseModel

from framework.utils.redaction import get_logger, redact_body, redact_data, redact_text

log = get_logger("eventhub.api")

M = TypeVar("M", bound=BaseModel)

_MAX_BODY_IN_MESSAGES = 2_000

# Retries of a reset connection ("socket hang up" on the shared public environment), done by Playwright
# itself: it retries only ECONNRESET - never timeouts or HTTP error statuses - with 250 ms / 500 ms
# back-off, inside the request's own timeout.
CONNECTION_RESET_RETRIES = 2


class HttpMethod(str, Enum):
    GET = "GET"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"

    @classmethod
    def parse(cls, method: str | HttpMethod) -> HttpMethod:
        """``"get"``, ``" Get "`` and ``HttpMethod.GET`` are all ``GET``; an unknown verb fails loudly."""
        if isinstance(method, HttpMethod):
            return method
        try:
            return cls(method.strip().upper())
        except ValueError:
            raise ValueError(
                f"Unsupported HTTP method {method!r}; use one of {', '.join(m.value for m in cls)}"
            ) from None

    @property
    def is_idempotent(self) -> bool:
        """RFC 9110 9.2.2: repeating the request has the same effect as sending it once."""
        return self in _IDEMPOTENT

    @property
    def max_retries(self) -> int:
        """POST and PATCH are never retried: a lost response could otherwise double-book or double-apply."""
        return CONNECTION_RESET_RETRIES if self.is_idempotent else 0


_IDEMPOTENT = frozenset({HttpMethod.GET, HttpMethod.HEAD, HttpMethod.OPTIONS, HttpMethod.PUT, HttpMethod.DELETE})


class ApiTransportError(RuntimeError):
    """The HTTP exchange itself failed (connection reset, timeout...). Message is secret-free."""


class UnexpectedResponseError(RuntimeError):
    """A call made to *arrange* test data returned the wrong status.

    Deliberately not an ``AssertionError``: a broken arrange step is a test error, never evidence for
    the behaviour under test (and never mistaken for a reproduced known defect).
    """


class ApiResponse:
    """Immutable snapshot of one HTTP exchange."""

    def __init__(
        self,
        *,
        method: str,
        url: str,
        status: int,
        headers: dict[str, str],
        text: str,
        request_body: Any,
        elapsed_ms: float,
    ) -> None:
        self.method = method
        self.url = url
        self.status = status
        self.headers = headers
        self.text = text
        self.request_body = request_body
        self.elapsed_ms = elapsed_ms

    # ---- body access ---------------------------------------------------------------------
    def json(self) -> Any:
        try:
            return json.loads(self.text)
        except json.JSONDecodeError as exc:
            raise AssertionError(self.describe("Response body is not valid JSON")) from exc

    def parse(self, model: type[M]) -> M:
        """Validate the JSON body against a pydantic model (contract check) and return it."""
        return model.model_validate(self.json())

    # ---- assertions ----------------------------------------------------------------------
    def expect_status(self, *expected: int) -> ApiResponse:
        """Assert the status (the behaviour under test)."""
        if self.status not in expected:
            wanted = " or ".join(str(code) for code in expected)
            raise AssertionError(self.describe(f"Expected HTTP {wanted} but got {self.status}"))
        return self

    def require_status(self, *expected: int) -> ApiResponse:
        """Require the status of an *arrange* step; failure raises UnexpectedResponseError, not AssertionError."""
        if self.status not in expected:
            wanted = " or ".join(str(code) for code in expected)
            raise UnexpectedResponseError(self.describe(f"Arrange step expected HTTP {wanted} but got {self.status}"))
        return self

    def describe(self, headline: str) -> str:
        """The whole exchange for an assertion message - with every secret masked."""
        text = redact_body(self.text)
        body = text if len(text) <= _MAX_BODY_IN_MESSAGES else text[:_MAX_BODY_IN_MESSAGES] + "..."
        sent = "" if self.request_body is None else f"\n  request body: {_redacted_json(self.request_body)}"
        return redact_text(f"{headline}\n  {self.method} {self.url} -> {self.status}{sent}\n  response body: {body}")

    def __repr__(self) -> str:
        return f"<ApiResponse {self.method} {self.url} -> {self.status}>"


class BaseApiClient:
    """Common request plumbing shared by all resource clients."""

    def __init__(self, request_context: APIRequestContext) -> None:
        self._ctx = request_context

    def _send(
        self,
        method: HttpMethod | str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> ApiResponse:
        verb = HttpMethod.parse(method)
        # Paths are resolved against the context base URL ("https://host/api/"); a leading slash would
        # make URL resolution drop the "/api" segment, so it is stripped here once for every client.
        relative_path = path.lstrip("/")
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        started = time.perf_counter()
        try:
            raw = self._ctx.fetch(
                relative_path,
                method=verb.value,
                params=clean_params or None,
                data=json_body,
                max_retries=verb.max_retries,
            )
        except PlaywrightError as exc:
            reason = redact_text(str(exc)).splitlines()[0]
            raise ApiTransportError(f"{verb.value} {relative_path} failed: {reason}") from None
        elapsed_ms = (time.perf_counter() - started) * 1000
        response = ApiResponse(
            method=verb.value,
            url=raw.url,
            status=raw.status,
            headers=raw.headers,
            text=raw.text(),
            request_body=json_body,
            elapsed_ms=elapsed_ms,
        )
        log.info("%s %s -> %s (%.0f ms)", verb.value, raw.url, raw.status, elapsed_ms)
        if json_body is not None:
            log.debug("request body: %s", _redacted_json(json_body))
        return response


def _redacted_json(body: Any) -> str:
    return json.dumps(redact_data(body), ensure_ascii=False, default=str)
