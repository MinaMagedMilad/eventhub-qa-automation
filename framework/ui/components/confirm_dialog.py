from __future__ import annotations

from playwright.sync_api import Locator, Page

from framework.ui.components.base import Component


class ConfirmDialog(Component):
    """Generic confirmation modal (``role="dialog"``, labelled by its title)."""

    def __init__(self, page: Page, title: str) -> None:
        super().__init__(page, page.get_by_role("dialog", name=title))
        self.description: Locator = self.root.locator("p").first
        self.confirm_button: Locator = self.root.get_by_test_id("confirm-dialog-yes")
        self.dismiss_button: Locator = self.root.get_by_role("button", name="Cancel", exact=True)

    def confirm(self) -> None:
        self.confirm_button.click()

    def dismiss(self) -> None:
        self.dismiss_button.click()


class CancelBookingDialog(ConfirmDialog):
    TITLE = "Cancel this booking?"

    def __init__(self, page: Page) -> None:
        super().__init__(page, self.TITLE)
