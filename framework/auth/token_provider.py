"""The single place where the suite authenticates.

``TokenProvider`` logs a role in through ``POST /auth/login`` the first time that role is needed,
caches the JWT for the rest of the (worker) session and transparently re-authenticates if the
token is about to expire. API clients and browser contexts are built from these tokens by the
fixtures - individual tests never log in, never see a token and never set an Authorization header.
"""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable

from pydantic import SecretStr

from framework.api.auth_api import AuthApi
from framework.auth.roles import UserRole, credentials_for
from framework.config import Settings
from framework.utils.redaction import get_logger, redact_body

log = get_logger("eventhub.auth")

_EXPIRY_SAFETY_MARGIN_S = 120


class AuthenticationError(RuntimeError):
    """Login failed for a configured role (wrong credentials, account missing, API down...)."""


class TokenProvider:
    def __init__(self, settings: Settings, auth_api_factory: Callable[[], AuthApi]) -> None:
        self._settings = settings
        self._auth_api_factory = auth_api_factory
        self._tokens: dict[UserRole, SecretStr] = {}  # SecretStr: never shown by a repr or a traceback
        # A rejected login is remembered for the rest of the session: retrying it for every test would
        # only spam a shared environment (and could trip rate limiting / account lock-out).
        self._failed_logins: dict[UserRole, AuthenticationError] = {}

    def token_for(self, role: UserRole) -> SecretStr:
        if role in self._failed_logins:
            raise self._failed_logins[role]
        cached = self._tokens.get(role)
        if cached and not _is_expiring(cached):
            return cached
        try:
            token = self._login(role)
        except AuthenticationError as exc:
            self._failed_logins[role] = exc
            raise
        self._tokens[role] = token
        return token

    def _login(self, role: UserRole) -> SecretStr:
        credentials = credentials_for(self._settings, role)  # raises MissingCredentialsError
        response = self._auth_api_factory().login(credentials.email, credentials.password.get_secret_value())
        if response.status != 200:
            raise AuthenticationError(
                f"Login failed for the '{role.value}' test user ({credentials.email}): "
                f"HTTP {response.status} {redact_body(response.text)[:300]}"
            )
        token = response.json().get("token")
        if not isinstance(token, str) or not token:
            raise AuthenticationError(f"Login for '{role.value}' returned no token: {redact_body(response.text)[:300]}")
        log.info("Authenticated test user '%s' (%s)", role.value, credentials.email)
        return SecretStr(token)  # already registered as a known secret by AuthApi


def _is_expiring(token: SecretStr) -> bool:
    """True if the JWT ``exp`` claim is within the safety margin. Unparseable tokens are trusted."""
    try:
        payload_b64 = token.get_secret_value().split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload_b64)).get("exp")
    except (IndexError, ValueError):
        return False
    return isinstance(exp, (int, float)) and exp - time.time() < _EXPIRY_SAFETY_MARGIN_S
