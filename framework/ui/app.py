from __future__ import annotations

from functools import cached_property

from playwright.sync_api import Page

from framework.ui.pages.booking_details_page import BookingDetailsPage
from framework.ui.pages.event_details_page import EventDetailsPage
from framework.ui.pages.events_page import EventsPage
from framework.ui.pages.my_bookings_page import MyBookingsPage


class EventHubApp:
    """Entry point to every page object for one browser tab: ``app.my_bookings.open()``."""

    def __init__(self, page: Page) -> None:
        self.page = page

    @cached_property
    def events(self) -> EventsPage:
        return EventsPage(self.page)

    @cached_property
    def event_details(self) -> EventDetailsPage:
        return EventDetailsPage(self.page)

    @cached_property
    def my_bookings(self) -> MyBookingsPage:
        return MyBookingsPage(self.page)

    @cached_property
    def booking_details(self) -> BookingDetailsPage:
        return BookingDetailsPage(self.page)
