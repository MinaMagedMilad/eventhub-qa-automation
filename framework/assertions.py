"""Domain assertions shared across test files."""

from __future__ import annotations

from framework.api.http import ApiResponse

# A resource owned by someone else may be reported as "forbidden" or as "not found" (hiding that it
# exists at all). Both are acceptable; any success or other error is not.
ACCESS_DENIED_STATUSES = (403, 404)


def assert_access_denied(response: ApiResponse, action: str) -> None:
    if response.status not in ACCESS_DENIED_STATUSES:
        raise AssertionError(response.describe(f"Expected 403 or 404: another user must not be able to {action}"))
