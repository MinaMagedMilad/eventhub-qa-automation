"""GET /api/auth/me - the endpoint the web app uses to validate its stored token on every page load."""

from __future__ import annotations

import pytest

from framework.models import ErrorResponse


@pytest.mark.smoke
def test_me_returns_the_authenticated_user(api, credentials_of):
    user = api.auth.me().expect_status(200).json()["user"]

    assert user["email"].lower() == credentials_of("primary").email.lower()
    assert type(user["userId"]) is int


@pytest.mark.security
@pytest.mark.negative
@pytest.mark.anonymous
def test_me_requires_a_token(api):
    response = api.auth.me().expect_status(401)

    assert response.parse(ErrorResponse).error == "Unauthorized"


@pytest.mark.security
@pytest.mark.negative
def test_me_rejects_an_invalid_token(api_with_token):
    response = api_with_token("not-a-jwt").auth.me().expect_status(401)

    assert response.parse(ErrorResponse).error == "Invalid or expired token"
