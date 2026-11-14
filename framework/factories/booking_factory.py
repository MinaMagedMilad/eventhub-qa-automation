"""Builds valid ``POST /bookings`` request bodies."""

from __future__ import annotations

from typing import Any

from framework.factories.overrides import apply_overrides
from framework.factories.sources import CustomerDataSource
from framework.models.booking import CreateBookingRequest


class BookingFactory:
    """``build(event_id, **overrides)`` -> a valid one-ticket ``CreateBookingRequest`` for that event.

    The customer is synthetic: a generated name, an undeliverable ``@example.com`` address and a
    ``+91 9...`` mobile number.
    """

    def __init__(self, data: CustomerDataSource) -> None:
        self._data = data

    def build(self, event_id: int, **overrides: Any) -> CreateBookingRequest:
        first, last = self._data.first_name(), self._data.last_name()
        request = CreateBookingRequest(
            event_id=event_id,
            customer_name=f"{first} {last}",
            customer_email=self._data.email(first),
            customer_phone=self._data.mobile_number(),
            quantity=1,
        )
        return apply_overrides(request, overrides)
