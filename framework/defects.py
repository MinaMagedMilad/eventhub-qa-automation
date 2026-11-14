"""Registry of known product defects reproduced by the suite.

A test that reproduces a defect is decorated with ``@known_defect("EH-01")``. It then runs as a
*strict* xfail:

* while the defect exists the test "xfails" - the run stays green and the report says why;
* once the defect is fixed the test unexpectedly passes and **fails the run** (strict), prompting
  the team to remove the marker - so a fix can never go unnoticed;
* only ``AssertionError`` counts as the expected failure; a timeout or crash still fails the run,
  so the marker can't hide unrelated breakage;
* steps that merely *set the scene* run inside ``with precondition(...)``: if one of them fails, its
  ``AssertionError`` is converted into a ``PreconditionError`` and the test fails for real instead of
  being miscounted as the known defect. Data factories (make_event/make_booking) already raise a
  non-assertion error when arranging fails.

Each entry mirrors the "Defects found" table in the README.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import pytest


class PreconditionError(RuntimeError):
    """A known-defect test could not even reach the step that reproduces the defect."""


@contextmanager
def precondition(description: str) -> Iterator[None]:
    try:
        yield
    except AssertionError as exc:
        raise PreconditionError(f"Precondition failed - {description}:\n{exc}") from exc


@dataclass(frozen=True)
class Defect:
    id: str
    title: str


KNOWN_DEFECTS: dict[str, Defect] = {
    d.id: d
    for d in (
        Defect(
            "EH-01",
            "UI rounds every amount to whole dollars: fractional prices show wrong / inconsistent totals",
        ),
        Defect(
            "EH-02",
            "Booking reference does not follow the documented 'EVT-XXXXXX' format (live: e.g. 'Q-MWTERP')",
        ),
        Defect(
            "EH-03",
            'Money amounts are serialised as JSON strings (e.g. totalPrice "2500"); the API docs specify numbers',
        ),
        Defect(
            "EH-04",
            "OpenAPI spec documents no authentication (no security, no 401) for /bookings and /events",
        ),
        Defect(
            "EH-05",
            "OpenAPI spec: POST /bookings 400 is oneOf two overlapping schemas, so no error body can validate",
        ),
        Defect(
            "EH-06",
            "Updating an event's capacity never adjusts availableSeats: capacity below sold seats is accepted "
            "and the event can be oversold; raised capacity adds seats that can never be sold",
        ),
        Defect(
            "EH-07",
            "POST /bookings converts values of the wrong JSON type instead of rejecting them (customerName 12345 / "
            "true -> '12345' / 'true', customerPhone 9876543210 -> '9876543210', quantity '2' -> 2)",
        ),
        Defect(
            "EH-08",
            "POST /bookings answers a 1,000-character customerName with HTTP 500 instead of a validation error",
        ),
    )
}


def known_defect(defect_id: str) -> pytest.MarkDecorator:
    defect = KNOWN_DEFECTS.get(defect_id)
    if defect is None:
        raise KeyError(f"Unknown defect id {defect_id!r}; register it in framework/defects.py")
    return pytest.mark.xfail(reason=f"[{defect.id}] {defect.title}", strict=True, raises=AssertionError)
