"""Fixtures shared by the API tests."""

from __future__ import annotations

import pytest

from framework.auth import UserRole


@pytest.fixture
def other_user(api_as):
    """A second, unrelated user (skipped with a reason if not configured)."""
    return api_as(UserRole.SECONDARY)
