from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from framework.ui.components.base import Component, value_next_to

MINUS_SIGN = "−"  # the decrement button renders a real minus sign, not a hyphen


class BookingForm(Component):
    """The "Book Tickets" panel on the event details page (US-114 AC1 inputs)."""

    # Client-side validation messages rendered by the form.
    NAME_ERROR = "Name must be at least 2 chars"
    EMAIL_ERROR = "Enter a valid email"
    PHONE_ERROR = "Enter a valid 10-digit phone"

    def __init__(self, page: Page) -> None:
        # The submit button only has an id (no test id) - used to scope the whole form.
        super().__init__(page, page.locator("form").filter(has=page.locator("#confirm-booking")))
        self.ticket_count: Locator = self.root.locator("#ticket-count")  # id only, no test id
        self.increase_button: Locator = self.root.get_by_role("button", name="+", exact=True)
        self.decrease_button: Locator = self.root.get_by_role("button", name=MINUS_SIGN, exact=True)
        self.max_hint: Locator = self.root.get_by_text(re.compile(r"^\(max \d+\)$"))
        self.full_name: Locator = self.root.get_by_label("Full Name")
        self.email: Locator = self.root.get_by_test_id("customer-email")
        self.phone: Locator = self.root.get_by_label("Phone Number")
        self.price_breakdown: Locator = self.root.get_by_text(re.compile(r"× \d+ tickets?$"))
        self.total: Locator = value_next_to(self.root, "Total")
        self.submit_button: Locator = self.root.locator("#confirm-booking")

    # ---- actions ----------------------------------------------------------------------------
    def select_quantity(self, quantity: int) -> None:
        """Use the +/- steppers like a user would, verifying each step landed."""
        current = self.current_quantity()
        button = self.increase_button if quantity > current else self.decrease_button
        step = 1 if quantity > current else -1
        while current != quantity:
            button.click()
            current += step
            expect(self.ticket_count).to_have_text(str(current))

    def fill_customer_details(self, *, name: str, email: str, phone: str) -> None:
        self.full_name.fill(name)
        self.email.fill(email)
        self.phone.fill(phone)

    def submit(self) -> None:
        self.submit_button.click()

    def book(self, *, quantity: int, name: str, email: str, phone: str) -> None:
        self.select_quantity(quantity)
        self.fill_customer_details(name=name, email=email, phone=phone)
        self.submit()

    # ---- state ------------------------------------------------------------------------------
    def current_quantity(self) -> int:
        return int(self.ticket_count.inner_text().strip())

    def error(self, message: str) -> Locator:
        return self.root.get_by_text(message, exact=True)
