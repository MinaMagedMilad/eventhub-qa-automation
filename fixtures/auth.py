"""Identity resolution - the only fixtures that know about credentials and tokens.

A test states *who* it acts as with a marker; everything downstream (API clients, browser contexts,
test-data ownership) follows from :func:`current_role`:

    def test_x(api): ...                              # primary user (default)

    @pytest.mark.as_user("secondary")
    def test_y(api, page): ...                        # secondary user, API and browser alike

    @pytest.mark.anonymous
    def test_z(api, page): ...                        # no credentials at all
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Playwright
from pydantic import SecretStr

from framework.api.session import ApiSessionManager, EventHubApi
from framework.auth import AuthenticationError, Credentials, MissingCredentialsError, UserRole, credentials_for
from framework.config import Settings, get_settings


def pytest_sessionstart(session: pytest.Session) -> None:
    """Fail fast, once, when the mandatory test user is not configured.

    Without this, every test would report the same setup error. Runs on the controller only (before
    any xdist worker starts) and not for introspection commands such as ``--collect-only``.
    """
    config = session.config
    if hasattr(config, "workerinput") or config.option.collectonly or getattr(config.option, "showfixtures", False):
        return
    try:
        credentials_for(get_settings(), UserRole.PRIMARY)
    except MissingCredentialsError as exc:
        raise pytest.UsageError(f"{exc}\nNothing was run.") from None


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def api_sessions(playwright: Playwright, settings: Settings) -> Iterator[ApiSessionManager]:
    manager = ApiSessionManager(playwright, settings)
    yield manager
    manager.dispose()


@pytest.fixture
def credentials_of(settings: Settings) -> Callable[[UserRole | str], Credentials]:
    """Raw credentials - **only for tests whose subject is authentication itself** (tests/api/auth,
    tests/contract/test_auth_contract.py). Every other test receives an authenticated client instead.
    """

    def _credentials(role: UserRole | str) -> Credentials:
        parsed = UserRole.parse(role)
        try:
            return credentials_for(settings, parsed)
        except MissingCredentialsError as exc:
            if parsed is UserRole.SECONDARY:
                pytest.skip(str(exc))
            pytest.fail(str(exc), pytrace=False)

    return _credentials


@pytest.fixture
def current_role(request: pytest.FixtureRequest) -> UserRole | None:
    """Identity requested by the test's markers (``None`` means anonymous)."""
    if request.node.get_closest_marker("anonymous"):
        return None
    marker = request.node.get_closest_marker("as_user")
    if marker is None:
        return UserRole.PRIMARY
    if len(marker.args) != 1:
        raise pytest.UsageError(f"{request.node.nodeid}: as_user() takes exactly one role")
    return UserRole.parse(marker.args[0])


def authenticated_client(api_sessions: ApiSessionManager, role: UserRole | None) -> EventHubApi:
    """Resolve a role to an authenticated client, turning configuration problems into clear outcomes.

    * secondary user not configured -> the test is *skipped* (optional persona, reason shown);
    * primary user not configured or login rejected -> the test *fails* with an actionable message
      (never silently skipped: a green run with nothing executed would be worse than a red one).
    """
    # skip/fail are raised *outside* the except blocks so the report shows the reason once,
    # without a chained "During handling of the above exception..." duplicate.
    try:
        if role is not None:
            api_sessions.tokens.token_for(role)
        return api_sessions.client_for(role)
    except MissingCredentialsError as exc:
        problem, optional_persona = str(exc), role is UserRole.SECONDARY
    except AuthenticationError as exc:
        problem, optional_persona = str(exc), False
    if optional_persona:
        pytest.skip(problem)
    pytest.fail(problem, pytrace=False)


def token_for(api_sessions: ApiSessionManager, role: UserRole) -> SecretStr:
    authenticated_client(api_sessions, role)  # same error handling as above
    return api_sessions.tokens.token_for(role)
