"""Creating a booking: POST /api/bookings returns a confirmed booking with a reference (AC1, AC5).

Response *shape and types* are covered by tests/contract; this file checks the business outcome.
"""

from __future__ import annotations

import pytest

from framework.models import Booking, BookingStatus, DataEnvelope


@pytest.mark.smoke
@pytest.mark.acceptance("AC1", "AC5")
def test_create_booking_returns_confirmed_booking_with_reference(api, event, booking_factory, track_booking):
    request = booking_factory.build(event.id, quantity=2)

    response = api.bookings.create(request).expect_status(201)

    envelope = response.parse(DataEnvelope[Booking])
    booking = envelope.data
    track_booking(booking.id)
    assert envelope.message == "Booking confirmed!"
    assert booking.status is BookingStatus.CONFIRMED
    assert booking.as_request_payload() == request.to_payload(), "stored booking differs from what was sent"
    # AC1 asks for "a booking reference": it must exist and identify exactly this booking.
    # (Its documented EVT-XXXXXX *format* is a contract check - see tests/contract, defect EH-02.)
    assert booking.booking_ref.strip(), "booking reference is empty"
    assert api.bookings.fetch_by_ref(booking.booking_ref).id == booking.id


@pytest.mark.acceptance("AC1", "AC5")
def test_each_booking_gets_a_unique_reference(event, make_booking):
    first, second = make_booking(event.id), make_booking(event.id)

    assert first.booking_ref != second.booking_ref
    assert first.id != second.id
