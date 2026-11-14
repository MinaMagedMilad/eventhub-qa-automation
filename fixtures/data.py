"""Test-data fixtures: builders plus "make_*" factories that create data through the API and
register it for automatic deletion.

Pattern used by the suite: **arrange through the API, act through the layer under test, assert
through both, clean up through the API.** Each test gets its own freshly created event, so prices
and seat counts are known exactly and tests never interfere with each other (or with other people
using the shared environment).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest

from fixtures.auth import authenticated_client
from framework.api.session import ApiSessionManager, EventHubApi
from framework.auth import UserRole
from framework.config import Settings
from framework.factories import BookingFactory, EventFactory
from framework.models import Booking, DataEnvelope, Event
from framework.utils import ResourceTracker
from framework.utils.random_data import RandomData
from framework.utils.run_context import RunContext


@pytest.fixture
def random_data(request: pytest.FixtureRequest, run_context: RunContext) -> RandomData:
    """This test's source of generated values, seeded from the run's data seed and the test's id.

    A test therefore gets the same names, e-mails, phone numbers and suffixes for the same seed, whatever
    worker it runs on and whatever ran before it - so one failed test can be replayed on its own.
    """
    return RandomData.for_test(run_context.data_seed, request.node.nodeid)


@pytest.fixture
def event_factory(settings: Settings, run_context: RunContext, random_data: RandomData) -> EventFactory:
    return EventFactory(title_prefix=f"{settings.test_data_prefix} {run_context.tag}", data=random_data)


@pytest.fixture
def booking_factory(random_data: RandomData) -> BookingFactory:
    return BookingFactory(data=random_data)


@pytest.fixture
def event_payload(event_factory: EventFactory) -> dict[str, Any]:
    """A valid ``POST /events`` body as a plain dict, for negative tests to break.

    Unlike factory overrides, a dict can lose a field (``event_payload.pop("title")``) or take a value of
    the wrong JSON type (see ``framework.factories.invalid_data``).
    """
    return event_factory.build().to_payload()


@pytest.fixture
def booking_payload(event: Event, booking_factory: BookingFactory) -> dict[str, Any]:
    """A valid ``POST /bookings`` body for the test's ``event``, as a plain dict to break (see ``event_payload``)."""
    return booking_factory.build(event.id).to_payload()


@pytest.fixture
def cleanup() -> Iterator[ResourceTracker]:
    tracker = ResourceTracker()
    yield tracker
    tracker.cleanup()


def _owner(owner: UserRole | str | None, current_role: UserRole | None) -> UserRole:
    if owner is not None:
        return UserRole.parse(owner)
    return current_role or UserRole.PRIMARY  # anonymous tests still need data owned by someone


@pytest.fixture
def track_event(
    api_sessions: ApiSessionManager, current_role: UserRole | None, cleanup: ResourceTracker
) -> Callable[..., None]:
    """Register an event created outside ``make_event`` (e.g. by a raw POST under test) for cleanup."""

    def _track(event_id: int, *, owner: UserRole | str | None = None) -> None:
        role = _owner(owner, current_role)
        client: EventHubApi = authenticated_client(api_sessions, role)
        cleanup.track(f"event #{event_id} owned by {role.value}", lambda: client.events.delete(event_id))

    return _track


@pytest.fixture
def make_event(
    api_sessions: ApiSessionManager,
    current_role: UserRole | None,
    event_factory: EventFactory,
    track_event: Callable[..., None],
) -> Callable[..., Event]:
    """``make_event(price=Decimal("99.5"), total_seats=3, owner="secondary")`` -> created ``Event``."""

    def _make(*, owner: UserRole | str | None = None, **overrides: Any) -> Event:
        role = _owner(owner, current_role)
        client = authenticated_client(api_sessions, role)
        response = client.events.create(event_factory.build(**overrides)).require_status(201)
        created = response.parse(DataEnvelope[Event]).data
        track_event(created.id, owner=role)
        return created

    return _make


@pytest.fixture
def event(make_event: Callable[..., Event]) -> Event:
    """A fresh event (price 1250, 50 seats) owned by the test's identity."""
    return make_event()


@pytest.fixture
def track_booking(
    api_sessions: ApiSessionManager, current_role: UserRole | None, cleanup: ResourceTracker
) -> Callable[..., None]:
    """Register a booking created outside ``make_booking`` (e.g. through the UI) for cleanup."""

    def _track(booking_id: int, *, owner: UserRole | str | None = None) -> None:
        role = _owner(owner, current_role)
        client: EventHubApi = authenticated_client(api_sessions, role)
        cleanup.track(f"booking #{booking_id} owned by {role.value}", lambda: client.bookings.cancel(booking_id))

    return _track


@pytest.fixture
def make_booking(
    api_sessions: ApiSessionManager,
    current_role: UserRole | None,
    booking_factory: BookingFactory,
    track_booking: Callable[..., None],
) -> Callable[..., Booking]:
    """``make_booking(event.id, quantity=3)`` -> confirmed ``Booking`` (registered for cleanup)."""

    def _make(event_id: int, *, owner: UserRole | str | None = None, **overrides: Any) -> Booking:
        role = _owner(owner, current_role)
        client = authenticated_client(api_sessions, role)
        response = client.bookings.create(booking_factory.build(event_id, **overrides)).require_status(201)
        booking = response.parse(DataEnvelope[Booking]).data
        track_booking(booking.id, owner=role)
        return booking

    return _make
