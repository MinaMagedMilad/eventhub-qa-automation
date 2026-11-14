from __future__ import annotations

from framework.api.http import ApiResponse, BaseApiClient, HttpMethod
from framework.contract.live_spec import SWAGGER_INIT_PATH


class ServiceApi(BaseApiClient):
    """Public service endpoints: health, feature flags and the published API docs."""

    def health(self) -> ApiResponse:
        return self._send(HttpMethod.GET, "/health")

    def config(self) -> ApiResponse:
        return self._send(HttpMethod.GET, "/config")

    def swagger_init_script(self) -> ApiResponse:
        """The Swagger UI bootstrap script that embeds the live OpenAPI document."""
        return self._send(HttpMethod.GET, SWAGGER_INIT_PATH)
