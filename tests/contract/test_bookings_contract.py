"""Booking endpoints vs. the published OpenAPI contract: documented status codes and response schemas.

Generic checks tolerate only deviations already filed as defects (framework/contract/deviations.py);
each such deviation is pinned by its own strict known-defect test at the end of this file.
"""

from __future__ import annotations

import pytest

from framework.constants import NONEXISTENT_ID
from framework.defects import known_defect, precondition
from framework.factories import invalid_data as bad
from framework.models import BOOKING_REF_PATTERN


@pytest.mark.smoke
@pytest.mark.acceptance("AC5")
def test_create_booking_response_matches_contract(api, contract, event, booking_factory, track_booking):
    response = api.bookings.create(booking_factory.build(event.id, quantity=2)).expect_status(201)
    track_booking(response.json()["data"]["id"])

    contract.assert_conforms(response, "POST", "/bookings")


@pytest.mark.acceptance("AC3", "AC5")
def test_list_bookings_response_matches_contract(api, contract, event, make_booking):
    make_booking(event.id)

    contract.assert_conforms(api.bookings.list(event_id=event.id).expect_status(200), "GET", "/bookings")


@pytest.mark.acceptance("AC3", "AC5")
def test_get_booking_by_id_response_matches_contract(api, contract, event, make_booking):
    booking = make_booking(event.id)

    contract.assert_conforms(api.bookings.get(booking.id).expect_status(200), "GET", "/bookings/{id}")


@pytest.mark.acceptance("AC3", "AC5")
def test_get_booking_by_reference_response_matches_contract(api, contract, event, make_booking):
    booking = make_booking(event.id)

    response = api.bookings.get_by_ref(booking.booking_ref).expect_status(200)

    contract.assert_conforms(response, "GET", "/bookings/ref/{ref}")


@pytest.mark.acceptance("AC4", "AC5")
def test_cancel_booking_response_matches_contract(api, contract, event, make_booking):
    booking = make_booking(event.id)

    contract.assert_conforms(api.bookings.cancel(booking.id).expect_status(200), "DELETE", "/bookings/{id}")


@pytest.mark.negative
def test_unknown_booking_response_matches_contract(api, contract):
    contract.assert_conforms(api.bookings.get(NONEXISTENT_ID).expect_status(404), "GET", "/bookings/{id}")


@pytest.mark.negative
def test_booking_for_unknown_event_response_matches_contract(api, contract, booking_factory):
    response = api.bookings.create(booking_factory.build(event_id=NONEXISTENT_ID)).expect_status(404)

    contract.assert_conforms(response, "POST", "/bookings")


# ---------------------------------------------------------------------------------------------
# Known contract defects - strict: each turns into a failure the moment it is fixed
# ---------------------------------------------------------------------------------------------
@pytest.mark.negative
@known_defect("EH-05")
@pytest.mark.parametrize("case", ["validation-error", "not-enough-seats"])
def test_rejected_booking_response_matches_contract(api, contract, make_event, booking_factory, case):
    event = make_event(total_seats=1)
    payload = booking_factory.build(event.id, quantity=1 if case == "validation-error" else 2).to_payload()
    if case == "validation-error":
        payload["quantity"] = bad.ZERO

    with precondition("the API rejects the booking with HTTP 400"):
        response = api.bookings.create(payload).expect_status(400)

    contract.assert_conforms(response, "POST", "/bookings", tolerate=())


@pytest.mark.security
@known_defect("EH-04")
@pytest.mark.anonymous
def test_unauthenticated_responses_are_documented(api, contract):
    with precondition("every call without a token is answered with HTTP 401"):
        calls = [
            (api.bookings.list().expect_status(401), "GET", "/bookings"),
            (api.bookings.get(1).expect_status(401), "GET", "/bookings/{id}"),
            (api.bookings.get_by_ref("EVT-AAAAAA").expect_status(401), "GET", "/bookings/ref/{ref}"),
            (api.bookings.cancel(1).expect_status(401), "DELETE", "/bookings/{id}"),
            (api.events.list().expect_status(401), "GET", "/events"),
            (api.events.get(1).expect_status(401), "GET", "/events/{id}"),
        ]

    undocumented = [
        f"{method} {path}"
        for response, method, path in calls
        if response.status not in contract.documented_statuses(method, path)
    ]

    assert not undocumented, f"401 is returned but not documented for: {', '.join(undocumented)}"


@pytest.mark.acceptance("AC1", "AC5")
@known_defect("EH-02")
def test_booking_reference_follows_documented_format(event, make_booking):
    booking = make_booking(event.id)

    assert BOOKING_REF_PATTERN.fullmatch(booking.booking_ref), (
        f"reference {booking.booking_ref!r} does not match the documented EVT-XXXXXX format"
    )


@pytest.mark.acceptance("AC2", "AC5")
@known_defect("EH-03")
def test_booking_total_price_is_a_json_number(api, contract, event, booking_factory, track_booking):
    response = api.bookings.create(booking_factory.build(event.id, quantity=2)).require_status(201)
    track_booking(response.json()["data"]["id"])

    contract.assert_conforms(response, "POST", "/bookings", tolerate=())
