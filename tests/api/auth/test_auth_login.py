"""POST /api/auth/login.

These are the only tests (with tests/contract/test_auth_contract.py) that handle raw credentials,
because authentication is their subject. Wrong-password attempts use the *secondary* account and
are limited to two per run, so a lock-out policy could never take down the primary test user.
Tokens are never placed directly in assertions, so they can't appear in failure output.
"""

from __future__ import annotations

import pytest

from framework.constants import WRONG_PASSWORD
from framework.factories import invalid_data as bad


def _looks_like_jwt(token: object) -> bool:
    return isinstance(token, str) and token.count(".") == 2 and token.startswith("eyJ")


@pytest.mark.smoke
@pytest.mark.security
def test_login_returns_a_working_token_for_valid_credentials(anonymous_api, api_with_token, credentials_of):
    credentials = credentials_of("primary")

    response = anonymous_api.auth.login(credentials.email, credentials.password.get_secret_value())

    body = response.expect_status(200).json()
    token_is_jwt = _looks_like_jwt(body.get("token"))
    assert token_is_jwt, "login must return a JWT (header.payload.signature)"
    assert body["user"]["email"].lower() == credentials.email.lower()
    me = api_with_token(body["token"]).auth.me().expect_status(200).json()
    assert me["user"]["email"].lower() == credentials.email.lower(), "the token must identify the same user"


@pytest.mark.security
@pytest.mark.negative
def test_login_with_a_wrong_password_is_rejected(anonymous_api, credentials_of):
    credentials = credentials_of("secondary")

    response = anonymous_api.auth.login(credentials.email, WRONG_PASSWORD)

    body = response.expect_status(400).json()
    assert "token" not in body
    assert body["success"] is False


@pytest.mark.security
@pytest.mark.negative
def test_login_does_not_reveal_whether_an_account_exists(anonymous_api, credentials_of, random_data):
    """OWASP: unknown e-mail and wrong password must look identical, or attackers can enumerate accounts.

    Note: the API docs specify 404 "User not found" for an unknown e-mail, which would leak exactly that.
    """
    wrong_password = anonymous_api.auth.login(credentials_of("secondary").email, WRONG_PASSWORD)
    unknown_user = anonymous_api.auth.login(random_data.email("nobody"), WRONG_PASSWORD)

    observed = (unknown_user.status, unknown_user.json().get("error"))
    expected = (wrong_password.status, wrong_password.json().get("error"))
    assert observed == expected, "unknown e-mail and wrong password produce different responses"


@pytest.mark.negative
@pytest.mark.parametrize(
    "body",
    [
        {"email": "qa@example.com"},
        {"password": "Passw0rd!"},
        {},
        {"email": bad.EMAIL_WITHOUT_AT, "password": "Passw0rd!"},
    ],
    ids=["password-missing", "email-missing", "empty-body", "email-malformed"],
)
def test_login_with_incomplete_or_malformed_input_is_rejected(anonymous_api, body):
    response = anonymous_api.auth.login_raw(body)

    assert response.expect_status(400).json().get("token") is None
