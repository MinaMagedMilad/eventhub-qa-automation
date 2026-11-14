from __future__ import annotations

from playwright.sync_api import Locator, Page

from framework.ui.components.base import Component, value_next_to


class BookingConfirmation(Component):
    """Success panel that replaces the booking form after "Confirm Booking" (US-114 AC1 output)."""

    def __init__(self, page: Page) -> None:
        heading = page.get_by_role("heading", name="Booking Confirmed!")
        super().__init__(page, page.locator("div").filter(has=heading).last)
        self.heading: Locator = heading
        self.booking_ref: Locator = self.root.locator(".booking-ref")  # CSS class only, no test id
        self.customer: Locator = value_next_to(self.root, "Customer")
        self.tickets: Locator = value_next_to(self.root, "Tickets")
        self.total: Locator = value_next_to(self.root, "Total")
        self.view_my_bookings_button: Locator = self.root.get_by_role("button", name="View My Bookings")

    def read_booking_ref(self) -> str:
        return self.booking_ref.inner_text().strip()

    def go_to_my_bookings(self) -> None:
        self.view_my_bookings_button.click()
