"""Builds valid ``POST /events`` request bodies."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from framework.constants import EVENT_CITIES, EventCategory
from framework.factories.overrides import apply_overrides
from framework.factories.sources import EventDataSource
from framework.models.event import CreateEventRequest

TITLE_PHRASE_MAX_LENGTH = 40  # self-imposed (the API documents no limit): keeps titles readable in the UI
DEFAULT_PRICE = Decimal("1250")
DEFAULT_TOTAL_SEATS = 50
DAYS_AHEAD = 45  # comfortably in the future, so the event is always bookable


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventFactory:
    """``build(**overrides)`` -> a valid ``CreateEventRequest``; any field can be overridden.

    Titles start with ``title_prefix`` (the run's label) followed by a unique suffix, so every event
    can be traced to the run that created it. Defaults - price 1250, 50 seats, 45 days ahead - are
    fixed, so tests that depend on them read clearly; only descriptive text is random.
    """

    def __init__(
        self,
        title_prefix: str,
        data: EventDataSource,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.title_prefix = title_prefix
        self._data = data
        self._clock = clock

    def build(self, **overrides: Any) -> CreateEventRequest:
        request = CreateEventRequest(
            title=self._title(),
            category=EventCategory.CONFERENCE.value,
            venue=f"{self._data.last_name()} Convention Centre",
            city=self._data.pick(EVENT_CITIES),
            event_date=(self._clock() + timedelta(days=DAYS_AHEAD)).replace(microsecond=0),
            price=DEFAULT_PRICE,
            total_seats=DEFAULT_TOTAL_SEATS,
            description="Created by the EventHub automation suite. Safe to delete.",
        )
        return apply_overrides(request, overrides)

    def _title(self) -> str:
        """``<prefix> <unique suffix> <phrase>``.

        Only the phrase is shortened, by a fixed amount, so a replay with the same data seed produces the
        same title apart from the run label in the prefix.
        """
        phrase = self._data.catch_phrase()[:TITLE_PHRASE_MAX_LENGTH].rstrip()
        return f"{self.title_prefix} {self._data.suffix()} {phrase}"
