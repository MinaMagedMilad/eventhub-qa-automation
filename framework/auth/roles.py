"""Test identities.

Tests never handle credentials. They declare *who* they act as (a :class:`UserRole`) and the
framework resolves that role to credentials, a JWT, an authenticated API client and an
authenticated browser context.

Adding a new persona (e.g. an admin) is a matter of adding an enum member and two settings fields.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from pydantic import SecretStr

from framework.config import Settings
from framework.utils.redaction import register_secret

_EMAIL_SHAPE = re.compile(r"^[^\s@]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


class UserRole(str, Enum):
    PRIMARY = "primary"
    """Main test user; owns the data for almost every test."""

    SECONDARY = "secondary"
    """A different, unrelated user; used to prove tenant isolation."""

    @classmethod
    def parse(cls, value: str | UserRole) -> UserRole:
        try:
            return value if isinstance(value, UserRole) else cls(value.lower())
        except ValueError:
            valid = ", ".join(r.value for r in cls)
            raise ValueError(f"Unknown user role {value!r}; expected one of: {valid}") from None


class MissingCredentialsError(RuntimeError):
    """Raised when a role is requested but its credentials are not configured."""


@dataclass(frozen=True)
class Credentials:
    email: str
    password: SecretStr

    def __repr__(self) -> str:  # never leak the password into logs or assertion messages
        return f"Credentials(email={self.email!r}, password='**********')"


def credentials_for(settings: Settings, role: UserRole) -> Credentials:
    email: str | None = getattr(settings, f"{role.value}_email")
    password: SecretStr | None = getattr(settings, f"{role.value}_password")
    if not email or password is None or not password.get_secret_value():
        prefix = f"EVENTHUB_{role.value.upper()}"
        raise MissingCredentialsError(
            f"No credentials configured for the '{role.value}' test user. "
            f"Set {prefix}_EMAIL and {prefix}_PASSWORD in .env (see .env.example) or as environment variables."
        )
    if not _EMAIL_SHAPE.match(email):
        prefix = f"EVENTHUB_{role.value.upper()}"
        raise MissingCredentialsError(
            f"{prefix}_EMAIL={email!r} is not an e-mail address. "
            "Use the real address of a registered EventHub account (a placeholder was left in .env?)."
        )
    register_secret(password)  # masked in every message, log and report from now on
    return Credentials(email=email, password=password)
