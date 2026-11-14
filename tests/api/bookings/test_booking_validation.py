"""Input validation of POST /api/bookings: invalid input is rejected and consumes no seats (AC5).

Every case starts from a valid body (``booking_payload``, a plain dict) and breaks one field: a wrong
value, a missing field or a wrong JSON type, from the known-bad catalogue (framework/factories/invalid_data.py).
The rules asserted are the documented ones (CreateBookingInput: types, name >= 2 characters, e-mail format,
phone >= 10 characters, quantity 1-10). If a case were wrongly accepted, the booking would still be
removed with its event at teardown.
"""

from __future__ import annotations

import pytest

from framework.constants import MAX_TICKETS_PER_BOOKING, NONEXISTENT_ID
from framework.defects import known_defect
from framework.factories import invalid_data as bad
from framework.models import Booking, DataEnvelope, ErrorResponse

VALIDATION_FAILED = "Validation failed"

# (case id, field, invalid value)
INVALID_FIELD_VALUES = [
    ("name-empty", "customerName", bad.EMPTY),
    ("name-1-char", "customerName", bad.ONE_CHAR),
    ("email-empty", "customerEmail", bad.EMPTY),
    ("email-no-at", "customerEmail", bad.EMAIL_WITHOUT_AT),
    ("email-no-domain", "customerEmail", bad.EMAIL_WITHOUT_DOMAIN),
    ("phone-empty", "customerPhone", bad.EMPTY),
    ("phone-too-short", "customerPhone", bad.PHONE_TOO_SHORT),
    ("quantity-zero", "quantity", bad.ZERO),
    ("quantity-negative", "quantity", bad.NEGATIVE),
    ("quantity-above-max", "quantity", MAX_TICKETS_PER_BOOKING + 1),
    ("quantity-fraction", "quantity", bad.FRACTION),
]

REQUIRED_FIELDS = ["eventId", "customerName", "customerEmail", "customerPhone", "quantity"]

# (field, case, a value of the wrong JSON type for the field's documented type)
WRONG_TYPES = [
    *(("customerName", case, value) for case, value in bad.NOT_A_STRING.items()),
    *(("customerEmail", case, value) for case, value in bad.NOT_A_STRING.items()),
    *(("customerPhone", case, value) for case, value in bad.NOT_A_STRING.items()),
    ("customerPhone", "valid-digits-as-number", bad.PHONE_AS_NUMBER),
    *(("quantity", case, value) for case, value in bad.NOT_AN_INTEGER.items()),
    ("quantity", "valid-integer-as-text", bad.INTEGER_AS_TEXT),
    *(("eventId", case, value) for case, value in bad.NOT_AN_INTEGER.items()),
]
KNOWN_DEFECTS = {
    "customerName-number": "EH-07",
    "customerName-boolean": "EH-07",
    "customerPhone-valid-digits-as-number": "EH-07",
    "quantity-valid-integer-as-text": "EH-07",
    "too-long": "EH-08",
}


def _case(case_id: str, *values: object):
    defect = KNOWN_DEFECTS.get(case_id)
    return pytest.param(*values, id=case_id, marks=[known_defect(defect)] if defect else [])


def _assert_rejected_without_side_effects(api, event, response, field, track_booking):
    if response.status == 201:  # defect path: the booking may even be on another event - always clean it up
        track_booking(response.json()["data"]["id"])
    response.expect_status(400)
    error = response.parse(ErrorResponse)
    assert error.error == VALIDATION_FAILED
    assert error.messages_for(field), f"no validation message for '{field}': {error.details}"
    assert api.events.fetch(event.id).available_seats == event.total_seats, "a rejected booking consumed seats"


@pytest.mark.negative
@pytest.mark.acceptance("AC5")
@pytest.mark.parametrize(("field", "value"), [pytest.param(f, v, id=i) for i, f, v in INVALID_FIELD_VALUES])
def test_invalid_field_value_is_rejected(api, event, booking_payload, track_booking, field, value):
    booking_payload[field] = value

    response = api.bookings.create(booking_payload)

    _assert_rejected_without_side_effects(api, event, response, field, track_booking)


@pytest.mark.negative
@pytest.mark.acceptance("AC5")
@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_missing_required_field_is_rejected(api, event, booking_payload, track_booking, field):
    booking_payload.pop(field)

    response = api.bookings.create(booking_payload)

    _assert_rejected_without_side_effects(api, event, response, field, track_booking)


@pytest.mark.negative
@pytest.mark.acceptance("AC5")
@pytest.mark.parametrize(("field", "value"), [_case(f"{f}-{c}", f, v) for f, c, v in WRONG_TYPES])
def test_field_of_the_wrong_type_is_rejected(api, event, booking_payload, track_booking, field, value):
    booking_payload[field] = value

    response = api.bookings.create(booking_payload)

    _assert_rejected_without_side_effects(api, event, response, field, track_booking)


@pytest.mark.negative
@pytest.mark.acceptance("AC5")
@pytest.mark.parametrize("name", [_case(case, value) for case, value in bad.TRICKY_TEXT.items()])
def test_unusual_customer_name_is_stored_exactly_or_rejected_cleanly(api, event, booking_payload, track_booking, name):
    """No length limit or character set is documented, so either outcome is acceptable - but never a
    server error, never a silently altered name (mangled encoding, stripped quotes, escaped markup), and a
    rejected booking must not consume seats.
    """
    booking_payload["customerName"] = name

    response = api.bookings.create(booking_payload)

    if response.status == 201:
        booking = response.parse(DataEnvelope[Booking]).data
        track_booking(booking.id)
        assert api.bookings.fetch(booking.id).customer_name == name, "the stored name differs from what was sent"
        return
    seats_left = api.events.fetch(event.id).available_seats
    side_effects = f"seats left afterwards: {seats_left} of {event.total_seats}"
    assert response.status == 400, response.describe(f"Expected 201 (stored) or 400 (rejected); {side_effects}")
    error = response.parse(ErrorResponse)
    assert error.messages_for("customerName"), f"rejected without saying why: {error.details}"
    assert seats_left == event.total_seats, f"a rejected booking consumed seats ({side_effects})"


@pytest.mark.negative
@pytest.mark.acceptance("AC5")
def test_booking_for_unknown_event_returns_404(api, booking_factory):
    response = api.bookings.create(booking_factory.build(event_id=NONEXISTENT_ID)).expect_status(404)

    assert response.parse(ErrorResponse).error
