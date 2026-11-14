from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from framework.models.base import ApiModel
from framework.models.event import Event

# Documented format: "EVT-XXXXXX" (e.g. EVT-A1B2C3)
BOOKING_REF_PATTERN = re.compile(r"^EVT-[A-Z0-9]{6}$")


class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Booking(ApiModel):
    id: int
    event_id: int
    customer_name: str
    customer_email: str
    customer_phone: str
    quantity: int
    total_price: Decimal
    status: BookingStatus
    booking_ref: str
    created_at: datetime
    updated_at: datetime | None = None
    event: Event | None = None

    def as_request_payload(self) -> dict[str, Any]:
        """The fields a client supplies, in request shape - for "what I sent is what was stored" checks."""
        return {
            "eventId": self.event_id,
            "customerName": self.customer_name,
            "customerEmail": self.customer_email,
            "customerPhone": self.customer_phone,
            "quantity": self.quantity,
        }


@dataclass(frozen=True)
class CreateBookingRequest:
    """Request body for ``POST /bookings``. Built by ``framework.factories.BookingFactory``."""

    event_id: int
    customer_name: str
    customer_email: str
    customer_phone: str
    quantity: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "eventId": self.event_id,
            "customerName": self.customer_name,
            "customerEmail": self.customer_email,
            "customerPhone": self.customer_phone,
            "quantity": self.quantity,
        }
