"""Booking details page: a signed-in user must not be able to open another user's booking."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect


@pytest.mark.security
@pytest.mark.as_user("secondary")
def test_user_cannot_open_another_users_booking(app, make_event, make_booking):
    event = make_event(owner="primary")
    booking = make_booking(event.id, owner="primary")

    details = app.booking_details.open(booking.id)

    expect(details.access_denied.or_(details.not_found)).to_be_visible()
    expect(details.page.get_by_text(booking.booking_ref)).to_have_count(0)
    expect(details.page.get_by_text(booking.customer_email)).to_have_count(0)
