from __future__ import annotations

from typing import Any

from framework.api.http import ApiResponse, BaseApiClient, HttpMethod
from framework.utils.redaction import register_secret


class AuthApi(BaseApiClient):
    """``/auth`` resource: used by the TokenProvider to log in, and tested in its own right (tests/api/auth)."""

    def login(self, email: str, password: str) -> ApiResponse:
        return self.login_raw({"email": email, "password": password})

    def login_raw(self, body: dict[str, Any]) -> ApiResponse:
        """Send any body (missing / malformed fields) - for negative tests."""
        return _register_issued_token(self._send(HttpMethod.POST, "/auth/login", json_body=body))

    def register(self, email: str, password: str) -> ApiResponse:
        return self.register_raw({"email": email, "password": password})

    def register_raw(self, body: dict[str, Any]) -> ApiResponse:
        return _register_issued_token(self._send(HttpMethod.POST, "/auth/register", json_body=body))

    def me(self) -> ApiResponse:
        return self._send(HttpMethod.GET, "/auth/me")


def _register_issued_token(response: ApiResponse) -> ApiResponse:
    """Every token the API issues becomes a known secret the moment it arrives (see redaction)."""
    try:
        token = response.json().get("token") if response.status < 300 else None
    except (AssertionError, AttributeError):  # not JSON / not an object: nothing was issued
        token = None
    if isinstance(token, str):
        register_secret(token)
    return response
