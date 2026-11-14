"""Test-data lifecycle.

Everything a test creates is registered with a :class:`ResourceTracker` together with the callable
that deletes it (bound to the identity that owns it). At teardown the tracker deletes in reverse
creation order (bookings before the event they belong to). Deletion problems never fail the test
- they are surfaced as warnings in the pytest summary so leaks are visible without masking results.

This matters doubly on EventHub: the environment is shared and each sandbox is capped (9 bookings,
6 custom events - older entries are silently replaced), so leaked data directly destabilises later runs.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from framework.utils.redaction import get_logger, redact_body, redact_text

if TYPE_CHECKING:  # type-only: framework.api imports framework.utils, so a runtime import would be circular
    from framework.api.http import ApiResponse

log = get_logger("eventhub.cleanup")

# 404 = already gone (e.g. the test itself cancelled the booking, or the event cascade removed it).
_ACCEPTABLE_STATUSES = frozenset({200, 204, 404})


class CleanupWarning(UserWarning):
    """A resource created by a test could not be deleted."""


@dataclass(frozen=True)
class _TrackedResource:
    description: str
    delete: Callable[[], ApiResponse]


class ResourceTracker:
    def __init__(self) -> None:
        self._resources: list[_TrackedResource] = []

    def track(self, description: str, delete: Callable[[], ApiResponse]) -> None:
        self._resources.append(_TrackedResource(description, delete))

    def __len__(self) -> int:
        return len(self._resources)

    def cleanup(self) -> None:
        while self._resources:
            resource = self._resources.pop()
            try:
                response = resource.delete()
            except Exception as exc:  # network errors etc. - report, keep cleaning the rest
                reason = redact_text(f"{type(exc).__name__}: {exc}").splitlines()[0]
                warnings.warn(f"Cleanup of {resource.description} failed: {reason}", CleanupWarning, stacklevel=1)
                continue
            if response.status in _ACCEPTABLE_STATUSES:
                log.info("Cleaned up %s (HTTP %s)", resource.description, response.status)
            else:
                body = redact_body(response.text)[:200]
                warnings.warn(
                    f"Cleanup of {resource.description} returned HTTP {response.status}: {body}",
                    CleanupWarning,
                    stacklevel=1,
                )
