"""Typed, environment-driven configuration.

Every knob the suite needs is declared here once. Values come from real environment variables
first (CI), then from a git-ignored ``.env`` file at the project root (local runs). Nothing else in
the code base reads ``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EVENTHUB_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Target environment
    base_url: str = "https://eventhub.rahulshettyacademy.com"
    api_url: str = "https://api.eventhub.rahulshettyacademy.com/api"

    # Test identities (see framework.auth.roles)
    primary_email: str | None = None
    primary_password: SecretStr | None = None
    secondary_email: str | None = None
    secondary_password: SecretStr | None = None

    # Where the web app keeps its JWT (verified in the app bundle: localStorage["eventhub_token"])
    token_storage_key: str = "eventhub_token"

    # Timeouts
    api_timeout_ms: int = 20_000
    ui_timeout_ms: int = 15_000

    # Every entity the suite creates is tagged with this prefix so leftovers are easy to spot.
    test_data_prefix: str = "QA-AUTO"

    # Run identity (framework.utils.run_context). Unset: generated per run. CI passes its own run id.
    run_id: str | None = None

    # Seed every generated value derives from (framework.utils.random_data). Unset: a new seed per run.
    # Either way it is printed in the report header; set it to replay a failed run's data.
    data_seed: int | None = None

    @field_validator("base_url", "api_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("primary_email", "secondary_email", "run_id", "data_seed", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings singleton (each pytest-xdist worker builds its own)."""
    return Settings()
