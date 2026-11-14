"""Per-field overrides shared by every factory (composition, not a base class to inherit from)."""

from __future__ import annotations

from dataclasses import fields, replace
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

R = TypeVar("R", bound="DataclassInstance")


def apply_overrides(request: R, overrides: dict[str, Any]) -> R:
    """Return a copy of the frozen request dataclass with ``overrides`` applied.

    Unknown names fail loudly with the list of valid ones, so a typo such as ``total_seat=3`` can never
    silently produce a default-valued request.
    """
    valid = {f.name for f in fields(request)}
    unknown = sorted(set(overrides) - valid)
    if unknown:
        raise TypeError(
            f"{type(request).__name__} has no field(s) {', '.join(unknown)}; valid fields: {', '.join(sorted(valid))}"
        )
    return replace(request, **overrides)
