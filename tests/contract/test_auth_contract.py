"""Auth endpoints vs. the published OpenAPI contract (raw credentials are used because auth is the subject)."""

from __future__ import annotations

import pytest

from framework.constants import WRONG_PASSWORD
from framework.factories import invalid_data as bad


@pytest.mark.smoke
def test_login_response_matches_contract(anonymous_api, contract, credentials_of):
    credentials = credentials_of("primary")

    response = anonymous_api.auth.login(credentials.email, credentials.password.get_secret_value())

    contract.assert_conforms(response.expect_status(200), "POST", "/auth/login")


@pytest.mark.negative
def test_failed_login_response_matches_contract(anonymous_api, contract, random_data):
    # An address that has no account: documented as 400 or 404 - either must match its schema.
    response = anonymous_api.auth.login(random_data.email("nobody"), WRONG_PASSWORD)

    contract.assert_conforms(response, "POST", "/auth/login")


def test_me_response_matches_contract(api, contract):
    contract.assert_conforms(api.auth.me().expect_status(200), "GET", "/auth/me")


@pytest.mark.negative
@pytest.mark.anonymous
def test_me_without_token_response_matches_contract(api, contract):
    contract.assert_conforms(api.auth.me().expect_status(401), "GET", "/auth/me")


@pytest.mark.negative
def test_invalid_registration_response_matches_contract(anonymous_api, contract):
    response = anonymous_api.auth.register_raw({"email": bad.EMAIL_WITHOUT_AT, "password": "Passw0rd!1"})

    contract.assert_conforms(response.expect_status(400), "POST", "/auth/register")
