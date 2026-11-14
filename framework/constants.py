"""Fixed values the suite relies on - each one defined here, once, and imported everywhere else.

Unlike ``framework.config.Settings`` (values that differ per environment), these describe EventHub
itself. The product owns the real lists, so each mirrored value is guarded by a test that fails the
day the two drift apart:

* ``EventCategory`` - documented in the OpenAPI spec (``GET /events?category``) and offered by the
  events-page category filter (tests/contract/test_events_contract.py, tests/ui/test_event_filter_options.py).
* ``EVENT_CITIES`` - not in the spec; offered by the events-page city filter
  (tests/ui/test_event_filter_options.py).
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class EventCategory(str, Enum):
    CONFERENCE = "Conference"
    CONCERT = "Concert"
    SPORTS = "Sports"
    WORKSHOP = "Workshop"
    FESTIVAL = "Festival"


# In the order the events-page city filter lists them.
EVENT_CITIES: Final[tuple[str, ...]] = ("Mumbai", "Bangalore", "Delhi", "Hyderabad", "Chennai", "Pune")

# Documented maximum (CreateBookingInput.quantity); the booking form enforces the same cap.
MAX_TICKETS_PER_BOOKING: Final = 10

# Per-user caps of the shared sandbox; when one is reached, the oldest entry is silently replaced.
SANDBOX_MAX_BOOKINGS: Final = 9
SANDBOX_MAX_CUSTOM_EVENTS: Final = 6

# Values negative tests use to mean "matches nothing".
NONEXISTENT_ID: Final = 999_999_999  # no event or booking has this id
WRONG_PASSWORD: Final = "Wrong-Passw0rd!"  # well-formed, but not the password of the test accounts
