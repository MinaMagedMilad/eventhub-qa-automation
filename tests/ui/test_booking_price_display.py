"""Booking form: the amounts on screen follow the quantity and must add up (AC2 as the user sees it)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from framework.defects import known_defect, precondition
from framework.utils import expected_total, format_usd_whole


@pytest.mark.acceptance("AC2")
def test_order_total_follows_the_ticket_quantity(app, make_event):
    event = make_event(total_seats=20)
    form = app.event_details.open(event.id).booking_form

    for quantity in (1, 2, 3, 4, 3):  # up and back down again
        form.select_quantity(quantity)
        expect(form.total).to_have_text(format_usd_whole(expected_total(event.price, quantity)))


@pytest.mark.acceptance("AC2")
@known_defect("EH-01")
def test_fractional_ticket_price_is_displayed_exactly(app, make_event):
    # 3 x $1,499.50 = $4,498.50. The UI formats with maximumFractionDigits=0, so it shows
    # "$1,500 x 3 tickets" next to a total of "$4,499" - neither figure is the real amount,
    # and they contradict each other on the same screen.
    event = make_event(price=Decimal("1499.50"))
    with precondition("the price summary is rendered for 3 tickets"):
        form = app.event_details.open(event.id).booking_form
        form.select_quantity(3)
        expect(form.price_breakdown).to_contain_text("× 3 tickets")

    # The page is settled, so a short timeout keeps the known-defect run fast.
    expect(form.price_breakdown).to_have_text("$1,499.50 × 3 tickets", timeout=3_000)
    expect(form.total).to_have_text("$4,498.50", timeout=3_000)
