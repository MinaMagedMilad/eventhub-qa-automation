"""A booking can be found again: in the list ("My Bookings"), by id and by reference (AC3, AC5)."""

from __future__ import annotations

import pytest

from framework.models import Booking, ErrorResponse, ListEnvelope


@pytest.mark.smoke
@pytest.mark.acceptance("AC3", "AC5")
def test_new_booking_is_listed_in_my_bookings(api, event, make_booking):
    booking = make_booking(event.id, quantity=2)

    listing = api.bookings.list(event_id=event.id).expect_status(200).parse(ListEnvelope[Booking])

    assert [b.id for b in listing.data] == [booking.id]
    listed = listing.data[0]
    assert listed.booking_ref == booking.booking_ref
    assert listed.event is not None, "list items embed their event"
    assert listed.event.id == event.id


@pytest.mark.acceptance("AC3", "AC5")
def test_booking_can_be_fetched_by_id_and_by_reference(api, event, make_booking):
    booking = make_booking(event.id)

    by_id = api.bookings.fetch(booking.id)
    by_ref = api.bookings.fetch_by_ref(booking.booking_ref)

    assert by_id.as_request_payload() == booking.as_request_payload()
    assert by_ref.id == booking.id


@pytest.mark.negative
@pytest.mark.acceptance("AC3")
def test_unknown_booking_reference_returns_404(api):
    response = api.bookings.get_by_ref("EVT-000000").expect_status(404)

    assert response.parse(ErrorResponse).error
