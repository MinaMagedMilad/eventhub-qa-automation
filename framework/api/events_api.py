from __future__ import annotations

from typing import Any

from framework.api.http import ApiResponse, BaseApiClient, HttpMethod
from framework.models.common import DataEnvelope
from framework.models.event import CreateEventRequest, Event


class EventsApi(BaseApiClient):
    """``/events`` resource: creates and removes the events that booking tests book against.

    Methods return raw :class:`ApiResponse` objects so tests can assert any status; ``fetch`` is the
    typed, fail-fast read used when a test only needs the current state of an event.
    """

    def fetch(self, event_id: int) -> Event:
        return self.get(event_id).expect_status(200).parse(DataEnvelope[Event]).data

    def list(
        self,
        *,
        category: str | None = None,
        city: str | None = None,
        search: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> ApiResponse:
        params = {"category": category, "city": city, "search": search, "page": page, "limit": limit}
        return self._send(HttpMethod.GET, "/events", params=params)

    def get(self, event_id: int | str) -> ApiResponse:
        return self._send(HttpMethod.GET, f"/events/{event_id}")

    def create(self, payload: CreateEventRequest | dict[str, Any]) -> ApiResponse:
        body = payload.to_payload() if isinstance(payload, CreateEventRequest) else payload
        return self._send(HttpMethod.POST, "/events", json_body=body)

    def update(self, event_id: int, payload: CreateEventRequest | dict[str, Any]) -> ApiResponse:
        body = payload.to_payload() if isinstance(payload, CreateEventRequest) else payload
        return self._send(HttpMethod.PUT, f"/events/{event_id}", json_body=body)

    def delete(self, event_id: int | str) -> ApiResponse:
        return self._send(HttpMethod.DELETE, f"/events/{event_id}")
