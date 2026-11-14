from __future__ import annotations

from playwright.sync_api import Page

from framework.ui.components.navbar import NavBar
from framework.ui.components.toast import Toasts


class BasePage:
    """Common page behaviour. Paths are relative to the browser context ``base_url``."""

    path: str = "/"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.navbar = NavBar(page)
        self.toasts = Toasts(page)

    def _visit(self, path: str) -> None:
        self.page.goto(path)
        self.wait_until_ready()

    def wait_until_ready(self) -> None:
        """Block until the page's primary content is rendered. Pages override this."""
