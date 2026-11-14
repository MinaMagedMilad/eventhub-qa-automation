"""POST /api/auth/register - negative paths only.

There is no endpoint to delete an account, so a *successful* registration would leave a permanent
account on a shared environment every run. Only inputs that must be rejected are sent; the duplicate
e-mail case resends the account's current password, so even a buggy "upsert" could not change it.
The documented password rule (6+ characters) vs. the UI's (8+ with upper case, digit and symbol) can't
be settled without creating accounts - it is raised as a question in the README instead (D6).
"""

from __future__ import annotations

import pytest

from framework.factories import invalid_data as bad
from framework.models import ErrorResponse


def _assert_rejected_for(response, field: str) -> None:
    error = response.expect_status(400).parse(ErrorResponse)
    assert error.messages_for(field), f"no validation message for '{field}': {error.details}"


@pytest.mark.negative
@pytest.mark.parametrize(
    "body",
    [{"email": bad.EMAIL_WITHOUT_AT, "password": "Passw0rd!1"}, {"password": "Passw0rd!1"}],
    ids=["email-malformed", "email-missing"],
)
def test_registration_without_a_valid_email_is_rejected(anonymous_api, body):
    response = anonymous_api.auth.register_raw(body)

    _assert_rejected_for(response, "email")


@pytest.mark.negative
@pytest.mark.parametrize("password", [bad.PASSWORD_TOO_SHORT, None], ids=["password-5-chars", "password-missing"])
def test_registration_without_a_valid_password_is_rejected(anonymous_api, random_data, password):
    body = {"email": random_data.email("register")}  # generated per test, so it belongs to no account
    if password is not None:
        body["password"] = password

    response = anonymous_api.auth.register_raw(body)

    _assert_rejected_for(response, "password")


@pytest.mark.negative
def test_registering_an_existing_email_is_rejected(anonymous_api, credentials_of):
    credentials = credentials_of("primary")

    response = anonymous_api.auth.register(credentials.email, credentials.password.get_secret_value())

    body = response.expect_status(400).json()
    assert body.get("token") is None, "no token may be issued for an existing account"
