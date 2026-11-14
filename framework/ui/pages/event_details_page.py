from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from framework.ui.components.base import value_next_to
from framework.ui.components.booking_confirmation import BookingConfirmation
from framework.ui.components.booking_form import BookingForm
from framework.ui.pages.base_page import BasePage


class EventDetailsPage(BasePage):
    """``/events/{id}`` - event information plus the "Book Tickets" panel."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.title: Locator = page.get_by_role("heading", level=1)
        self.book_tickets_heading: Locator = page.get_by_role("heading", name="Book Tickets")
        self.not_found: Locator = page.get_by_role("heading", name="Event not found")
        self.booking_form = BookingForm(page)
        self.confirmation = BookingConfirmation(page)

    def open(self, event_id: int) -> EventDetailsPage:
        self._visit(f"/events/{event_id}")
        return self

    def wait_until_ready(self) -> None:
        expect(self.book_tickets_heading.or_(self.not_found)).to_be_visible()

    def info(self, label: str) -> Locator:
        """Event fact tile value, e.g. ``info("Available")`` -> ``"50 / 50 seats"``.

        (The label is upper-cased with CSS only, so its DOM text is still "Available".)
        """
        return value_next_to(self.page.locator("body"), label)
