"""Browser fixtures layered on top of pytest-playwright.

Only ``context`` is overridden: it is created through pytest-playwright's ``new_context`` (so
tracing / screenshots / video on failure keep working) with the requested identity's JWT seeded into
localStorage. Tests simply ask for ``page`` (or ``app``) and land in the app already signed in.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from playwright.sync_api import BrowserContext, Page, expect

from fixtures.auth import token_for
from framework.api.session import ApiSessionManager
from framework.auth import UserRole
from framework.config import Settings
from framework.ui import EventHubApp, authenticated_storage_state


@pytest.fixture(scope="session")
def base_url(pytestconfig: pytest.Config, settings: Settings) -> str:
    """Web-app URL: ``--base-url`` wins, otherwise ``EVENTHUB_BASE_URL`` / default."""
    cli_value = pytestconfig.getoption("base_url", default=None)
    return str(cli_value).rstrip("/") if cli_value else settings.base_url


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    # Desktop viewport (the nav links are hidden below the md breakpoint) and a fixed locale.
    return {**browser_context_args, "viewport": {"width": 1440, "height": 900}, "locale": "en-US"}


@pytest.fixture(scope="session", autouse=True)
def _ui_timeouts(settings: Settings) -> None:
    expect.set_options(timeout=settings.ui_timeout_ms)


@pytest.fixture
def context(
    new_context: Callable[..., BrowserContext],
    api_sessions: ApiSessionManager,
    current_role: UserRole | None,
    settings: Settings,
    base_url: str,
) -> BrowserContext:
    storage_state = None
    if current_role is not None:
        token = token_for(api_sessions, current_role)
        storage_state = authenticated_storage_state(base_url, settings.token_storage_key, token)
    browser_context = new_context(storage_state=storage_state)
    browser_context.set_default_timeout(settings.ui_timeout_ms)
    return browser_context


@pytest.fixture
def app(page: Page) -> EventHubApp:
    return EventHubApp(page)
