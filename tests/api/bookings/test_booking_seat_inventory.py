"""Seat inventory: booking consumes seats, never more than are available (AC5)."""

from __future__ import annotations

import pytest

from framework.defects import known_defect
from framework.models import Booking, BookingStatus, DataEnvelope, ErrorResponse, ListEnvelope


def _sold_seats(api, event_id: int) -> int:
    listing = api.bookings.list(event_id=event_id, limit=100).expect_status(200).parse(ListEnvelope[Booking])
    return sum(b.quantity for b in listing.data)


@pytest.mark.acceptance("AC5")
def test_booking_decrements_available_seats(api, make_event, make_booking):
    event = make_event(total_seats=20)

    make_booking(event.id, quantity=3)

    refreshed = api.events.fetch(event.id)
    assert refreshed.available_seats == 17
    assert refreshed.total_seats == 20


@pytest.mark.acceptance("AC5")
def test_last_available_seats_can_be_booked(api, make_event, make_booking):
    event = make_event(total_seats=3)

    booking = make_booking(event.id, quantity=3)

    assert booking.status is BookingStatus.CONFIRMED
    assert api.events.fetch(event.id).available_seats == 0


@pytest.mark.negative
@pytest.mark.acceptance("AC5")
def test_booking_more_tickets_than_available_is_rejected(api, make_event, booking_factory):
    event = make_event(total_seats=3)

    response = api.bookings.create(booking_factory.build(event.id, quantity=4)).expect_status(400)

    assert response.parse(ErrorResponse).error == "Only 3 seat(s) available, but 4 requested"
    assert api.events.fetch(event.id).available_seats == 3, "a rejected booking must not consume seats"


@pytest.mark.negative
@pytest.mark.acceptance("AC5")
@known_defect("EH-06")
def test_tickets_sold_never_exceed_capacity_after_the_event_is_resized(
    api, make_event, make_booking, event_factory, booking_factory, track_booking
):
    """However the API treats a capacity change, it must never sell more tickets than the event has seats.

    Live (EH-06): lowering capacity from 10 to 3 with 4 seats sold is accepted, available seats stay at 6,
    and a further booking succeeds - 5 tickets sold for a 3-seat event.
    """
    event = make_event(total_seats=10)
    make_booking(event.id, quantity=4)
    api.events.update(event.id, event_factory.build(total_seats=3))  # accepted or rejected - both are fine here

    attempt = api.bookings.create(booking_factory.build(event.id, quantity=1))
    if attempt.status == 201:
        track_booking(attempt.parse(DataEnvelope[Booking]).data.id)

    capacity = api.events.fetch(event.id).total_seats
    sold = _sold_seats(api, event.id)
    assert sold <= capacity, (
        f"Overbooked: {sold} tickets sold for an event with {capacity} seats (extra booking -> HTTP {attempt.status})"
    )
