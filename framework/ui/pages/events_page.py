from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from framework.ui.components.base import Component
from framework.ui.pages.base_page import BasePage


class EventCard(Component):
    def __init__(self, page: Page, root: Locator) -> None:
        super().__init__(page, root)
        self.title: Locator = root.get_by_role("heading", level=3)
        self.book_now_link: Locator = root.get_by_test_id("book-now-btn")

    def book_now(self) -> None:
        self.book_now_link.click()


class EventsPage(BasePage):
    path = "/events"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.heading: Locator = page.get_by_role("heading", level=1)
        self.search_box: Locator = page.get_by_placeholder("Search events, venues")
        self.event_cards: Locator = page.get_by_test_id("event-card")
        self.no_results: Locator = page.get_by_role("heading", name="No events found")
        # The filter <select>s have no id, label or test id: each is identified by its "All ..." option.
        self.category_filter: Locator = self._filter_with_option("All Categories")
        self.city_filter: Locator = self._filter_with_option("All Cities")

    def open(self) -> EventsPage:
        self._visit(self.path)
        return self

    def wait_until_ready(self) -> None:
        expect(self.event_cards.first.or_(self.no_results)).to_be_visible()

    def search(self, text: str) -> None:
        self.search_box.fill(text)
        # The box is debounced (300 ms) and then reflected in the URL; wait for that, then the results.
        expect(self.page).to_have_url(re.compile(r"[?&]search="))
        self.wait_until_ready()

    def filter_values(self, select: Locator) -> list[str]:
        """The values a filter offers, without its "All ..." (empty) option."""
        expect(select).to_be_visible()
        values: list[str] = select.locator("option").evaluate_all("options => options.map(o => o.value)")
        return [value for value in values if value]

    def _filter_with_option(self, label: str) -> Locator:
        return self.page.get_by_role("combobox").filter(has=self.page.locator("option", has_text=label))

    def card_titled(self, title: str) -> EventCard:
        return EventCard(self.page, self.event_cards.filter(has=self.page.get_by_role("heading", name=title)))
