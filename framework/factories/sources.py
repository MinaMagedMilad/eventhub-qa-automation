"""What the factories need from a source of random values - declared by the consumer, kept minimal.

Each factory depends only on the narrow interface below, not on Faker or ``random`` (dependency
inversion; interface segregation: the event builder never sees e-mail or phone generation). Any object
with these methods fits - ``framework.utils.random_data.RandomData`` in the suite, a stub with fixed
values when a factory itself is under test.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar

T = TypeVar("T")


class EventDataSource(Protocol):
    def suffix(self, length: int = ...) -> str: ...

    def catch_phrase(self) -> str: ...

    def last_name(self) -> str: ...

    def pick(self, options: Sequence[T]) -> T: ...


class CustomerDataSource(Protocol):
    def first_name(self) -> str: ...

    def last_name(self) -> str: ...

    def email(self, label: str) -> str: ...

    def mobile_number(self) -> str: ...
