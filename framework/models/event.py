from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from framework.models.base import ApiModel


class Event(ApiModel):
    id: int
    title: str
    description: str | None = None
    category: str
    venue: str
    city: str
    event_date: datetime
    price: Decimal
    total_seats: int
    available_seats: int
    image_url: str | None = None
    is_static: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class CreateEventRequest:
    """Request body for ``POST /events``. Built by ``framework.factories.EventFactory``."""

    title: str
    category: str
    venue: str
    city: str
    event_date: datetime
    price: Decimal
    total_seats: int
    description: str | None = None
    image_url: str | None = None

    def to_payload(self) -> dict[str, Any]:
        data = asdict(self)
        payload: dict[str, Any] = {
            "title": data["title"],
            "category": data["category"],
            "venue": data["venue"],
            "city": data["city"],
            "eventDate": self.event_date.astimezone(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            # JSON number (not string) - the API documents ``price`` as a number.
            "price": int(self.price) if self.price == self.price.to_integral_value() else float(self.price),
            "totalSeats": data["total_seats"],
        }
        if self.description is not None:
            payload["description"] = self.description
        if self.image_url is not None:
            payload["imageUrl"] = self.image_url
        return payload
