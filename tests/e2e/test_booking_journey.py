"""End-to-end: a visitor books tickets in the browser, and the result is verified in the system (AC1-AC3).

E2E tests follow a whole user journey across pages, then confirm the outcome through the API: a
confirmation screen alone does not prove a booking was persisted correctly.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from framework.models import BookingStatus
from framework.utils import expected_total, format_usd_whole


@pytest.mark.smoke
@pytest.mark.acceptance("AC1", "AC2", "AC3")
def test_visitor_books_tickets_from_the_events_list(app, api, event, booking_factory, track_booking):
    customer = booking_factory.build(event.id, quantity=3)
    total = expected_total(event.price, customer.quantity)

    # Find the event like a visitor would and open it
    app.events.open().search(event.title)
    app.events.card_titled(event.title).book_now()
    details = app.event_details
    details.wait_until_ready()
    expect(details.title).to_have_text(event.title)

    # AC1 - choose tickets, enter name / e-mail / phone, confirm
    details.booking_form.book(
        quantity=customer.quantity,
        name=customer.customer_name,
        email=customer.customer_email,
        phone=customer.customer_phone,
    )

    # AC1 - confirmation with a booking reference; AC2 - correct total
    # (The reference *format* is a contract check - see tests/contract, defect EH-02.)
    confirmation = details.confirmation
    expect(confirmation.heading).to_be_visible()
    expect(confirmation.booking_ref).not_to_be_empty()
    booking_ref = confirmation.read_booking_ref()
    expect(confirmation.customer).to_have_text(customer.customer_name)
    expect(confirmation.tickets).to_have_text(str(customer.quantity))
    expect(confirmation.total).to_have_text(format_usd_whole(total))

    # The booking really exists, with exactly what the visitor entered
    stored = api.bookings.fetch_by_ref(booking_ref)
    track_booking(stored.id)
    assert stored.as_request_payload() == customer.to_payload()
    assert stored.total_price == total
    assert stored.status is BookingStatus.CONFIRMED

    # AC3 - it is listed in My Bookings
    confirmation.go_to_my_bookings()
    my_bookings = app.my_bookings
    my_bookings.wait_until_ready()
    card = my_bookings.card_for(booking_ref)
    expect(card.root).to_be_visible()
    expect(card.event_title).to_have_text(event.title)
    expect(card.total).to_have_text(format_usd_whole(total))


@pytest.mark.acceptance("AC1", "AC5")
def test_booking_in_the_browser_reduces_available_seats(app, api, make_event, booking_factory, track_booking):
    event = make_event(total_seats=12)
    customer = booking_factory.build(event.id, quantity=5)
    details = app.event_details.open(event.id)

    details.booking_form.book(
        quantity=customer.quantity,
        name=customer.customer_name,
        email=customer.customer_email,
        phone=customer.customer_phone,
    )
    expect(details.confirmation.heading).to_be_visible()
    track_booking(api.bookings.fetch_by_ref(details.confirmation.read_booking_ref()).id)

    assert api.events.fetch(event.id).available_seats == 7
