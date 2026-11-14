from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from framework.ui.components.booking_card import BookingCard
from framework.ui.pages.base_page import BasePage


class MyBookingsPage(BasePage):
    """``/bookings`` - the signed-in user's bookings (US-114 AC3 / AC4)."""

    path = "/bookings"
    CANCELLED_TOAST = "Booking cancelled successfully"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.heading: Locator = page.get_by_role("heading", name="My Bookings", level=1)
        self.booking_cards: Locator = page.get_by_test_id("booking-card")
        self.empty_state: Locator = page.get_by_role("heading", name="No bookings yet")

    def open(self) -> MyBookingsPage:
        self._visit(self.path)
        return self

    def wait_until_ready(self) -> None:
        expect(self.heading).to_be_visible()
        expect(self.booking_cards.first.or_(self.empty_state)).to_be_visible()

    def card_for(self, booking_ref: str) -> BookingCard:
        return BookingCard(self.page, self.booking_cards.filter(has_text=booking_ref))
