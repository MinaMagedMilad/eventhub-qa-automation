"""Browser-side authentication.

The web app keeps its JWT in ``localStorage["eventhub_token"]`` and validates it with ``GET /auth/me``
on load (verified in the app bundle). Instead of driving the login form before every UI test, the
framework seeds that key through Playwright ``storage_state`` when the browser context is created,
using the same token the API layer obtained. Result: every UI test starts already signed in as the
requested role, with zero login steps and zero credentials in test code.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from pydantic import SecretStr


def authenticated_storage_state(base_url: str, storage_key: str, token: SecretStr) -> dict[str, Any]:
    parts = urlsplit(base_url)
    origin = f"{parts.scheme}://{parts.netloc}"
    return {
        "cookies": [],
        "origins": [{"origin": origin, "localStorage": [{"name": storage_key, "value": token.get_secret_value()}]}],
    }
