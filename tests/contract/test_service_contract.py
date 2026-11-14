"""Public service endpoints vs. the published OpenAPI contract."""

from __future__ import annotations

import pytest


@pytest.mark.smoke
def test_health_response_matches_contract(anonymous_api, contract):
    response = anonymous_api.service.health().expect_status(200)

    contract.assert_conforms(response, "GET", "/health")
    assert response.json()["status"] == "ok"


def test_config_response_matches_contract(anonymous_api, contract):
    contract.assert_conforms(anonymous_api.service.config().expect_status(200), "GET", "/config")
