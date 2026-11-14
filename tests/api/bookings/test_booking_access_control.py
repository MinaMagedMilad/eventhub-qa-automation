"""Authentication and tenant isolation for the booking endpoints.

The story never says "only the owner can see or cancel a booking", but a booking holds personal data
(name, e-mail, phone) and the API docs promise each account "a fully isolated sandbox", so these are
treated as implicit acceptance criteria (README, story review, assumption A3).
"""

from __future__ import annotations

import pytest

from framework.assertions import assert_access_denied
from framework.models import Booking, BookingStatus, ErrorResponse, ListEnvelope

# Each entry exercises one booking endpoint.
BOOKING_CALLS = {
    "create": lambda api: api.bookings.create(
        {
            "eventId": 1,
            "customerName": "Anon",
            "customerEmail": "a@example.com",
            "customerPhone": "+919000000000",
            "quantity": 1,
        }
    ),
    "list": lambda api: api.bookings.list(),
    "get-by-id": lambda api: api.bookings.get(1),
    "get-by-ref": lambda api: api.bookings.get_by_ref("EVT-AAAAAA"),
    "cancel": lambda api: api.bookings.cancel(1),
}


@pytest.mark.security
@pytest.mark.negative
@pytest.mark.anonymous
@pytest.mark.parametrize("call", BOOKING_CALLS.values(), ids=BOOKING_CALLS.keys())
def test_booking_endpoints_require_authentication(api, call):
    response = call(api).expect_status(401)

    assert response.parse(ErrorResponse).error == "Unauthorized"


@pytest.mark.security
@pytest.mark.negative
@pytest.mark.parametrize(
    "token",
    ["not-a-jwt", "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VySWQiOjF9.forged-signature"],
    ids=["garbage", "forged-signature"],
)
def test_booking_endpoints_reject_invalid_tokens(api_with_token, token):
    response = api_with_token(token).bookings.list().expect_status(401)

    assert response.parse(ErrorResponse).error == "Invalid or expired token"


# ---------------------------------------------------------------------------------------------
# Tenant isolation: user B must never read or change user A's booking
# ---------------------------------------------------------------------------------------------
@pytest.fixture
def victim_booking(event, make_booking) -> Booking:
    """A booking owned by the primary user."""
    return make_booking(event.id)


@pytest.mark.security
def test_other_user_cannot_read_booking_by_id(other_user, victim_booking):
    assert_access_denied(other_user.bookings.get(victim_booking.id), "read this booking by id")


@pytest.mark.security
def test_other_user_cannot_read_booking_by_reference(other_user, victim_booking):
    assert_access_denied(other_user.bookings.get_by_ref(victim_booking.booking_ref), "read this booking by reference")


@pytest.mark.security
def test_other_user_does_not_see_booking_in_their_list(other_user, victim_booking):
    listing = other_user.bookings.list(limit=100).expect_status(200).parse(ListEnvelope[Booking])

    assert victim_booking.id not in {b.id for b in listing.data}


@pytest.mark.security
def test_other_user_cannot_cancel_booking(api, other_user, victim_booking):
    assert_access_denied(other_user.bookings.cancel(victim_booking.id), "cancel this booking")

    assert api.bookings.fetch(victim_booking.id).status is BookingStatus.CONFIRMED


@pytest.mark.security
def test_other_user_cannot_book_a_private_event(other_user, event, booking_factory):
    assert_access_denied(other_user.bookings.create(booking_factory.build(event.id)), "book this private event")
