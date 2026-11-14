"""Booking form: invalid customer details are caught in the browser and never sent (AC1)."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from framework.factories import invalid_data as bad
from framework.ui.components import BookingForm


@pytest.fixture
def booking_requests(page):
    """Records every POST /bookings the page sends, to prove invalid input never leaves the browser."""
    sent: list[str] = []
    page.on("request", lambda r: sent.append(r.url) if r.method == "POST" and r.url.endswith("/bookings") else None)
    return sent


@pytest.mark.negative
@pytest.mark.acceptance("AC1")
def test_empty_form_shows_every_validation_error_and_sends_nothing(app, event, booking_requests):
    form = app.event_details.open(event.id).booking_form

    form.submit()

    for message in (BookingForm.NAME_ERROR, BookingForm.EMAIL_ERROR, BookingForm.PHONE_ERROR):
        expect(form.error(message)).to_be_visible()
    assert booking_requests == []


@pytest.mark.negative
@pytest.mark.acceptance("AC1")
@pytest.mark.parametrize(
    ("name", "email", "phone", "expected_error"),
    [
        pytest.param(bad.ONE_CHAR, "qa@example.com", "+91 9876543210", BookingForm.NAME_ERROR, id="name-1-char"),
        pytest.param("Asha Rao", bad.EMAIL_WITHOUT_TLD, "+91 9876543210", BookingForm.EMAIL_ERROR, id="email-no-tld"),
        pytest.param(
            "Asha Rao", bad.EMAIL_DOT_INSTEAD_OF_AT, "+91 9876543210", BookingForm.EMAIL_ERROR, id="email-no-at"
        ),
        pytest.param("Asha Rao", "qa@example.com", bad.PHONE_NINE_DIGITS, BookingForm.PHONE_ERROR, id="phone-9-digits"),
        pytest.param("Asha Rao", "qa@example.com", bad.PHONE_WITH_LETTERS, BookingForm.PHONE_ERROR, id="phone-letters"),
    ],
)
def test_invalid_customer_details_are_rejected(app, event, booking_requests, name, email, phone, expected_error):
    form = app.event_details.open(event.id).booking_form

    form.fill_customer_details(name=name, email=email, phone=phone)
    form.submit()

    expect(form.error(expected_error)).to_be_visible()
    expect(app.event_details.confirmation.heading).to_have_count(0)
    assert booking_requests == []
