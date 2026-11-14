from __future__ import annotations

from playwright.sync_api import Locator, Page

from framework.ui.components.base import Component


class Toasts(Component):
    """Notification stack (top-right). Toasts have no test ids; the container is an aria-live region."""

    def __init__(self, page: Page) -> None:
        super().__init__(page, page.locator("[aria-live='polite']"))

    def with_text(self, message: str) -> Locator:
        return self.root.get_by_text(message)
