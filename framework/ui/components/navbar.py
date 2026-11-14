from __future__ import annotations

from playwright.sync_api import Locator, Page

from framework.ui.components.base import Component


class NavBar(Component):
    def __init__(self, page: Page) -> None:
        super().__init__(page, page.get_by_role("navigation").first)
        self.events_link: Locator = page.get_by_test_id("nav-events")
        self.my_bookings_link: Locator = page.get_by_test_id("nav-bookings")
        self.user_email: Locator = page.get_by_test_id("user-email-display")

    def go_to_events(self) -> None:
        self.events_link.click()

    def go_to_my_bookings(self) -> None:
        self.my_bookings_link.click()
