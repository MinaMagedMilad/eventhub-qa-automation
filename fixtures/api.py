"""API-client fixtures. All of them come back already authenticated (or deliberately not)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from fixtures.auth import authenticated_client
from framework.api.session import ApiSessionManager, EventHubApi
from framework.auth import UserRole


@pytest.fixture
def api(api_sessions: ApiSessionManager, current_role: UserRole | None) -> EventHubApi:
    """Client for the identity the test runs as (see ``current_role``)."""
    return authenticated_client(api_sessions, current_role)


@pytest.fixture
def api_as(api_sessions: ApiSessionManager) -> Callable[[UserRole | str], EventHubApi]:
    """Factory for tests that need several identities at once, e.g. ``api_as("secondary")``."""

    def _client(role: UserRole | str) -> EventHubApi:
        return authenticated_client(api_sessions, UserRole.parse(role))

    return _client


@pytest.fixture
def anonymous_api(api_sessions: ApiSessionManager) -> EventHubApi:
    """Client that sends no Authorization header."""
    return api_sessions.client_for(None)


@pytest.fixture
def api_with_token(api_sessions: ApiSessionManager) -> Callable[[str], EventHubApi]:
    """Client that sends an arbitrary bearer token (malformed / forged token tests)."""
    return lambda token: api_sessions.raw_client(bearer_token=token)
