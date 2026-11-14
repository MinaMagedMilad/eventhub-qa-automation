"""Contract deviations that are already filed as defects.

Generic contract tests tolerate exactly these (and nothing else), so they stay green on the known
problems while still failing on any new one. Each entry has its own strict known-defect test that
asserts the real contract, so a fix is detected automatically. Keep in sync with framework/defects.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from framework.contract.openapi import Violation


@dataclass(frozen=True)
class KnownDeviation:
    defect_id: str
    operation: str  # "POST /bookings", or "*" for every operation
    location: re.Pattern[str]
    message: re.Pattern[str]

    def matches(self, violation: Violation) -> bool:
        return (
            self.operation in ("*", violation.operation)
            and bool(self.location.search(violation.location))
            and bool(self.message.search(violation.message))
        )


KNOWN_DEVIATIONS: tuple[KnownDeviation, ...] = (
    # EH-03: money amounts are serialised as JSON strings ("2500") instead of numbers.
    KnownDeviation(
        defect_id="EH-03",
        operation="*",
        location=re.compile(r"(^|/)(totalPrice|price)$"),
        message=re.compile(r"is not of type 'number'"),
    ),
)
