"""End-to-end: a user cancels a booking from My Bookings, and the system releases the seats (AC4)."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect


@pytest.mark.smoke
@pytest.mark.acceptance("AC4")
def test_user_cancels_a_booking_from_my_bookings(app, api, make_event, make_booking):
    event = make_event(total_seats=10)
    booking = make_booking(event.id, quantity=3)
    my_bookings = app.my_bookings.open()

    dialog = my_bookings.card_for(booking.booking_ref).start_cancellation()
    expect(dialog.description).to_contain_text(booking.booking_ref)
    expect(dialog.description).to_contain_text("3 seat(s)")
    dialog.confirm()

    expect(my_bookings.toasts.with_text(my_bookings.CANCELLED_TOAST)).to_be_visible()
    expect(my_bookings.card_for(booking.booking_ref).root).to_have_count(0)
    api.bookings.get(booking.id).expect_status(404)
    assert api.events.fetch(event.id).available_seats == 10
