from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from framework.ui.components.base import value_next_to
from framework.ui.pages.base_page import BasePage


class BookingDetailsPage(BasePage):
    """``/bookings/{id}`` - one booking, or an "Access Denied" / "Booking not found" state."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.event_title: Locator = page.get_by_role("heading", level=1)
        self.access_denied: Locator = page.get_by_role("heading", name="Access Denied")
        self.not_found: Locator = page.get_by_role("heading", name="Booking not found")
        self.total_paid: Locator = value_next_to(page.locator("body"), "Total Paid")

    def open(self, booking_id: int) -> BookingDetailsPage:
        self._visit(f"/bookings/{booking_id}")
        return self

    def wait_until_ready(self) -> None:
        expect(self.event_title.or_(self.access_denied).or_(self.not_found).first).to_be_visible()

    def detail(self, label: str) -> Locator:
        return value_next_to(self.page.locator("body"), label)
