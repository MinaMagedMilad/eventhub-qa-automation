"""Cancelling a booking releases its seats and removes it (AC4, AC5)."""

from __future__ import annotations

import pytest

from framework.constants import NONEXISTENT_ID
from framework.models import Booking, ListEnvelope, MessageEnvelope


@pytest.mark.smoke
@pytest.mark.acceptance("AC4", "AC5")
def test_cancelling_a_booking_releases_its_seats(api, make_event, make_booking):
    event = make_event(total_seats=10)
    booking = make_booking(event.id, quantity=4)

    response = api.bookings.cancel(booking.id).expect_status(200)

    assert response.parse(MessageEnvelope).message == "Booking cancelled"
    assert api.events.fetch(event.id).available_seats == 10, "cancelled seats must go back to the event"


@pytest.mark.acceptance("AC4", "AC5")
def test_cancelled_booking_no_longer_appears_in_my_bookings(api, event, make_booking):
    kept = make_booking(event.id)
    cancelled = make_booking(event.id)

    api.bookings.cancel(cancelled.id).expect_status(200)

    listing = api.bookings.list(event_id=event.id).expect_status(200).parse(ListEnvelope[Booking])
    assert [b.id for b in listing.data] == [kept.id]
    api.bookings.get(cancelled.id).expect_status(404)


@pytest.mark.negative
@pytest.mark.acceptance("AC4")
def test_cancelling_the_same_booking_twice_returns_404(api, event, make_booking):
    booking = make_booking(event.id)
    api.bookings.cancel(booking.id).expect_status(200)

    api.bookings.cancel(booking.id).expect_status(404)


@pytest.mark.negative
@pytest.mark.acceptance("AC4")
def test_cancelling_a_non_existent_booking_returns_404(api):
    api.bookings.cancel(NONEXISTENT_ID).expect_status(404)
