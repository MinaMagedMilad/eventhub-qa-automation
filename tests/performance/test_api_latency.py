"""Response-time budgets for the API calls behind the booking flow.

Opt-in (``pytest -m performance``) and non-blocking in CI (nightly job). This is deliberately **not**
a load test: EventHub is a shared public practice environment, and hammering it with concurrent users
would degrade it for everyone else. Calls are sequential, one worker, a few dozen requests in total -
enough to spot a latency regression, not to stress the system. Real load/stress testing (k6, Locust)
belongs on a dedicated environment, with permission.

Each test publishes p50 / p95 / max to the "API latency" table at the end of the run and fails if p95
exceeds the budget. Budgets are generous, because the numbers include the tester's own network.
"""

from __future__ import annotations

import json

import pytest

from framework.utils.latency import LATENCY_PROPERTY, latency_summary

SAMPLES = 15
READ_P95_BUDGET_MS = 1_500
WRITE_P95_BUDGET_MS = 2_500

READ_CALLS = {
    "GET /events": lambda api, event, booking: api.events.list(search=event.title),
    "GET /events/{id}": lambda api, event, booking: api.events.get(event.id),
    "GET /bookings": lambda api, event, booking: api.bookings.list(event_id=event.id),
    "GET /bookings/{id}": lambda api, event, booking: api.bookings.get(booking.id),
    "GET /bookings/ref/{ref}": lambda api, event, booking: api.bookings.get_by_ref(booking.booking_ref),
}


@pytest.fixture
def record_latency(record_property):
    def _record(endpoint: str, samples: list[float], budget_ms: int) -> dict:
        summary = latency_summary(endpoint, samples, budget_ms)
        record_property(LATENCY_PROPERTY, json.dumps(summary))
        return summary

    return _record


def _assert_within_budget(*summaries: dict) -> None:
    over = [f"{s['endpoint']}: p95 {s['p95']:.0f} ms > {s['budget']} ms" for s in summaries if s["p95"] > s["budget"]]
    assert not over, "p95 latency over budget:\n  " + "\n  ".join(over)


@pytest.mark.parametrize("endpoint", READ_CALLS)
def test_read_latency_is_within_budget(api, event, make_booking, record_latency, endpoint):
    booking = make_booking(event.id)
    call = READ_CALLS[endpoint]
    call(api, event, booking).require_status(200)  # warm-up: connection set-up is not what we measure

    samples = [call(api, event, booking).expect_status(200).elapsed_ms for _ in range(SAMPLES)]

    _assert_within_budget(record_latency(endpoint, samples, READ_P95_BUDGET_MS))


def test_booking_create_and_cancel_latency_is_within_budget(api, make_event, booking_factory, record_latency):
    event = make_event(total_seats=SAMPLES)  # bookings are cancelled straight away; the event cascade cleans up
    create_ms, cancel_ms = [], []

    for _ in range(SAMPLES):
        created = api.bookings.create(booking_factory.build(event.id)).expect_status(201)
        create_ms.append(created.elapsed_ms)
        cancel_ms.append(api.bookings.cancel(created.json()["data"]["id"]).expect_status(200).elapsed_ms)

    _assert_within_budget(
        record_latency("POST /bookings", create_ms, WRITE_P95_BUDGET_MS),
        record_latency("DELETE /bookings/{id}", cancel_ms, WRITE_P95_BUDGET_MS),
    )
