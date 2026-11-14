"""Builds and owns authenticated API clients, one per identity.

This is where "authorization is handled by the framework" happens for the API layer: a request
context is created per role with the role's bearer token baked into its default headers, so every
call made through that client is authenticated without the test doing anything.
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import APIRequestContext, Playwright

from framework.api.auth_api import AuthApi
from framework.api.bookings_api import BookingsApi
from framework.api.events_api import EventsApi
from framework.api.service_api import ServiceApi
from framework.auth.roles import UserRole
from framework.auth.token_provider import TokenProvider
from framework.config import Settings


@dataclass(frozen=True)
class EventHubApi:
    """Facade grouping every resource client for one identity (``None`` = anonymous)."""

    role: UserRole | None
    auth: AuthApi
    events: EventsApi
    bookings: BookingsApi
    service: ServiceApi

    @classmethod
    def over(cls, ctx: APIRequestContext, role: UserRole | None) -> EventHubApi:
        return cls(
            role=role,
            auth=AuthApi(ctx),
            events=EventsApi(ctx),
            bookings=BookingsApi(ctx),
            service=ServiceApi(ctx),
        )


class ApiSessionManager:
    def __init__(self, playwright: Playwright, settings: Settings) -> None:
        self._playwright = playwright
        self._settings = settings
        self._contexts: dict[UserRole | None, APIRequestContext] = {}
        self._extra_contexts: list[APIRequestContext] = []
        self._clients: dict[UserRole | None, EventHubApi] = {}
        self.tokens = TokenProvider(settings, auth_api_factory=lambda: AuthApi(self._context(None)))

    def client_for(self, role: UserRole | None) -> EventHubApi:
        """Authenticated client for ``role``; ``None`` yields a client that sends no credentials."""
        if role not in self._clients:
            self._clients[role] = EventHubApi.over(self._context(role), role)
        return self._clients[role]

    def raw_client(self, *, bearer_token: str) -> EventHubApi:
        """Client with an arbitrary bearer token - for negative auth tests (malformed/forged tokens).

        Not cached: each call gets a fresh context so a bad token can never leak into other tests.
        """
        ctx = self._new_context({"Authorization": f"Bearer {bearer_token}"})
        self._extra_contexts.append(ctx)
        return EventHubApi.over(ctx, role=None)

    def dispose(self) -> None:
        for ctx in [*self._contexts.values(), *self._extra_contexts]:
            ctx.dispose()
        self._contexts.clear()
        self._clients.clear()
        self._extra_contexts.clear()

    # ---- internals -------------------------------------------------------------------------
    def _context(self, role: UserRole | None) -> APIRequestContext:
        if role not in self._contexts:
            token = None if role is None else self.tokens.token_for(role)
            headers = {} if token is None else {"Authorization": f"Bearer {token.get_secret_value()}"}
            self._contexts[role] = self._new_context(headers)
        return self._contexts[role]

    def _new_context(self, extra_headers: dict[str, str]) -> APIRequestContext:
        return self._playwright.request.new_context(
            base_url=self._settings.api_url + "/",
            extra_http_headers={"Accept": "application/json", **extra_headers},
            timeout=self._settings.api_timeout_ms,
        )
