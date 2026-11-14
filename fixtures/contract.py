"""Contract-testing fixtures and options."""

from __future__ import annotations

import pytest

from framework.contract import OpenApiContract, default_contract


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-openapi-snapshot",
        action="store_true",
        default=False,
        help="If the live OpenAPI spec differs from contracts/eventhub-openapi.json, overwrite the snapshot "
        "(review the git diff before committing).",
    )


@pytest.fixture(scope="session")
def contract() -> OpenApiContract:
    """The versioned OpenAPI document responses are validated against."""
    return default_contract()
