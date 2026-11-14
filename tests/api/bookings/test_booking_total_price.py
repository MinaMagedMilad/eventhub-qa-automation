"""Total price of a booking = ticket price x number of tickets, exactly (AC2, AC5)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from framework.constants import MAX_TICKETS_PER_BOOKING
from framework.utils import expected_total


@pytest.mark.smoke
@pytest.mark.acceptance("AC2", "AC5")
@pytest.mark.parametrize("quantity", [1, 4, MAX_TICKETS_PER_BOOKING], ids=["min-1-ticket", "4-tickets", "max-tickets"])
def test_total_price_is_ticket_price_times_quantity(event, make_booking, quantity):
    booking = make_booking(event.id, quantity=quantity)

    assert booking.total_price == expected_total(event.price, quantity)


@pytest.mark.acceptance("AC2", "AC5")
@pytest.mark.parametrize("unit_price", ["0.10", "19.99", "1499.50"])
def test_total_price_is_exact_for_fractional_ticket_prices(make_event, make_booking, unit_price):
    event = make_event(price=Decimal(unit_price))

    booking = make_booking(event.id, quantity=3)

    assert booking.total_price == expected_total(unit_price, 3), "money must not suffer float rounding"
