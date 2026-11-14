"""My Bookings page: what a booking card shows, and the cancel dialog's escape hatch (AC3, AC4)."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from framework.utils import format_usd_whole


@pytest.mark.smoke
@pytest.mark.acceptance("AC3")
def test_booking_card_shows_the_booking_details(app, event, make_booking):
    booking = make_booking(event.id, quantity=2)

    card = app.my_bookings.open().card_for(booking.booking_ref)

    expect(card.root).to_be_visible()
    expect(card.event_title).to_have_text(event.title)
    expect(card.tickets).to_have_text(re.compile(r"2 tickets$"))
    expect(card.total).to_have_text(format_usd_whole(booking.total_price))
    expect(card.status_badge("confirmed")).to_be_visible()
    expect(card.booking_id).to_have_text(f"#{booking.id}")


@pytest.mark.acceptance("AC4")
def test_dismissing_the_cancel_dialog_keeps_the_booking(app, api, event, make_booking):
    booking = make_booking(event.id)
    my_bookings = app.my_bookings.open()

    dialog = my_bookings.card_for(booking.booking_ref).start_cancellation()
    dialog.dismiss()

    expect(dialog.root).to_be_hidden()
    expect(my_bookings.card_for(booking.booking_ref).status_badge("confirmed")).to_be_visible()
    api.bookings.get(booking.id).expect_status(200)
