"""Money helpers that mirror how the web app renders prices.

The UI formats every amount with ``Intl.NumberFormat("en-US", {style: "currency", currency: "USD",
maximumFractionDigits: 0})`` - i.e. US dollars rounded half-away-from-zero to whole units
("$3,750"). Expected UI strings are derived with the same rules so UI assertions stay exact.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

_NON_NUMERIC = re.compile(r"[^\d.\-]")


def to_decimal(value: Decimal | int | float | str) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def expected_total(unit_price: Decimal | int | float | str, quantity: int) -> Decimal:
    """AC2: total = ticket price x number of tickets (exact decimal arithmetic, no float drift)."""
    return to_decimal(unit_price) * quantity


def format_usd_whole(amount: Decimal | int | float | str) -> str:
    """Format exactly like the UI: ``$1,234`` (USD, no decimals, half-up rounding)."""
    rounded = to_decimal(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    sign = "-" if rounded.is_signed() else ""
    return f"{sign}${abs(rounded):,}"


def parse_usd(text: str) -> Decimal:
    """Parse a UI amount such as ``"$3,750"`` back into a Decimal."""
    cleaned = _NON_NUMERIC.sub("", text)
    if not cleaned:
        raise ValueError(f"No amount found in {text!r}")
    return Decimal(cleaned)
