from __future__ import annotations

from typing import Any

from framework.api.http import ApiResponse, BaseApiClient, HttpMethod
from framework.models.booking import Booking, CreateBookingRequest
from framework.models.common import DataEnvelope


class BookingsApi(BaseApiClient):
    """``/bookings`` resource - the subject of US-114.

    Methods return the raw :class:`ApiResponse` so tests can assert on any status code (positive and
    negative paths). ``fetch`` / ``fetch_by_ref`` are typed, fail-fast reads for checking state.

    Note: the app also exposes an undocumented ``DELETE /bookings`` ("Clear all bookings" button).
    It is intentionally not wrapped here: wiping a whole sandbox would break tests running in parallel.
    """

    def fetch(self, booking_id: int) -> Booking:
        return self.get(booking_id).expect_status(200).parse(DataEnvelope[Booking]).data

    def fetch_by_ref(self, booking_ref: str) -> Booking:
        return self.get_by_ref(booking_ref).expect_status(200).parse(DataEnvelope[Booking]).data

    def create(self, payload: CreateBookingRequest | dict[str, Any] | str) -> ApiResponse:
        body = payload.to_payload() if isinstance(payload, CreateBookingRequest) else payload
        return self._send(HttpMethod.POST, "/bookings", json_body=body)

    def list(
        self,
        *,
        event_id: int | None = None,
        status: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> ApiResponse:
        params = {"eventId": event_id, "status": status, "page": page, "limit": limit}
        return self._send(HttpMethod.GET, "/bookings", params=params)

    def get(self, booking_id: int | str) -> ApiResponse:
        return self._send(HttpMethod.GET, f"/bookings/{booking_id}")

    def get_by_ref(self, booking_ref: str) -> ApiResponse:
        return self._send(HttpMethod.GET, f"/bookings/ref/{booking_ref}")

    def cancel(self, booking_id: int | str) -> ApiResponse:
        return self._send(HttpMethod.DELETE, f"/bookings/{booking_id}")
