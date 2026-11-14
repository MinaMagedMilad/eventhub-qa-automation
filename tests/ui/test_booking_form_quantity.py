"""Booking form: the ticket quantity is limited by the seats left and by the 10-ticket cap (AC1)."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from framework.constants import MAX_TICKETS_PER_BOOKING


@pytest.mark.acceptance("AC1")
def test_quantity_is_limited_to_the_seats_available(app, make_event):
    event = make_event(total_seats=3)
    form = app.event_details.open(event.id).booking_form

    expect(form.ticket_count).to_have_text("1")
    expect(form.decrease_button).to_be_disabled()
    expect(form.max_hint).to_have_text("(max 3)")

    form.select_quantity(3)

    expect(form.increase_button).to_be_disabled()


@pytest.mark.acceptance("AC1")
def test_quantity_is_capped_at_ten_tickets_per_booking(app, event):
    form = app.event_details.open(event.id).booking_form  # 50 seats available

    expect(form.max_hint).to_have_text(f"(max {MAX_TICKETS_PER_BOOKING})")
    form.select_quantity(MAX_TICKETS_PER_BOOKING)

    expect(form.increase_button).to_be_disabled()


@pytest.mark.acceptance("AC1")
def test_sold_out_event_cannot_be_booked(app, make_event, make_booking):
    event = make_event(total_seats=2)
    make_booking(event.id, quantity=2)

    form = app.event_details.open(event.id).booking_form

    expect(form.submit_button).to_be_disabled()
    expect(form.submit_button).to_have_text("Sold Out")
