from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from framework.ui.components.base import Component
from framework.ui.components.confirm_dialog import CancelBookingDialog


class BookingCard(Component):
    """One booking in the "My Bookings" list."""

    def __init__(self, page: Page, root: Locator) -> None:
        super().__init__(page, root)
        self.booking_ref: Locator = root.locator(".booking-ref")  # CSS class only, no test id
        self.booking_id: Locator = root.get_by_test_id("booking-id")
        self.event_title: Locator = root.get_by_role("heading", level=3)
        self.tickets: Locator = root.get_by_text(re.compile(r"^\S+ \d+ tickets?$"))
        self.total: Locator = root.get_by_text("total", exact=True).locator("xpath=preceding-sibling::*[1]")
        self.cancel_button: Locator = root.get_by_test_id("cancel-booking-btn")
        self.view_details_button: Locator = root.get_by_role("button", name="View Details")

    def status_badge(self, status: str) -> Locator:
        return self.root.get_by_text(status, exact=True)

    def start_cancellation(self) -> CancelBookingDialog:
        self.cancel_button.click()
        return CancelBookingDialog(self.page)
