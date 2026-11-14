"""Known-bad and edge-case input values for negative tests - one catalogue instead of literals in tests.

Factories build *valid* requests, and their overrides can only make a value wrong (``quantity=0``).
Validation tests therefore start from a valid body as a plain dict (the ``booking_payload`` /
``event_payload`` fixtures) and break it: remove a field with ``payload.pop("customerEmail")``, or set a
value from here, including values of the wrong JSON type.

The catalogue says what a value *is*, never whether it must be rejected: that depends on the field's
rules, so each test picks the values its field's rules forbid and states the expected outcome itself.
Groups are ``{case id: value}`` mappings, ready for ``pytest.mark.parametrize``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

# --- Text -------------------------------------------------------------------------------------
EMPTY: Final = ""
ONE_CHAR: Final = "A"
TOO_LONG: Final = "x" * 1_000  # no maximum is documented; far beyond any sensible length

# --- E-mail addresses -------------------------------------------------------------------------
EMAIL_WITHOUT_AT: Final = "not-an-email"
EMAIL_WITHOUT_DOMAIN: Final = "qa@"
EMAIL_WITHOUT_TLD: Final = "qa@example"
EMAIL_DOT_INSTEAD_OF_AT: Final = "qa.example.com"

# --- Phone numbers ----------------------------------------------------------------------------
PHONE_TOO_SHORT: Final = "12345"
PHONE_NINE_DIGITS: Final = "98765 4321"
PHONE_WITH_LETTERS: Final = "phone-number"

# --- Passwords --------------------------------------------------------------------------------
PASSWORD_TOO_SHORT: Final = "12345"  # documented minimum: 6 characters

# --- Numbers ----------------------------------------------------------------------------------
ZERO: Final = 0
NEGATIVE: Final = -1
FRACTION: Final = 1.5

# --- Wrong JSON types for a field -------------------------------------------------------------
NOT_A_STRING: Final[Mapping[str, Any]] = {"number": 12345, "boolean": True, "null": None}
NOT_AN_INTEGER: Final[Mapping[str, Any]] = {"text": "two", "boolean": True, "null": None}
# Valid values sent as the wrong JSON type: only the type rule can reject them, so they expose an API that
# silently converts types.
PHONE_AS_NUMBER: Final = 9876543210  # 10 digits, but a JSON number instead of a string
INTEGER_AS_TEXT: Final = "2"  # a valid quantity, but a JSON string instead of an integer

# --- Free text that is unusual but legitimate -------------------------------------------------
# An API may store these or reject them, but must never fail on them or store them altered.
TRICKY_TEXT: Final[Mapping[str, str]] = {
    "apostrophe": "Siobhán O'Brien",
    "sql-injection": "Robert'); DROP TABLE bookings;--",
    "html-script": "<script>alert(1)</script>",
    "accents": "Zoë Ñúñez",
    "chinese": "李雷",
    "arabic-rtl": "محمد علي",
    "emoji": "Asha 🎟️ Rao",
    "too-long": TOO_LONG,
}
