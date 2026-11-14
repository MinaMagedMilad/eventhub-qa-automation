"""Random primitives for generated test data - the suite's only source of randomness, and always seeded.

Test data needs to be *unique* and *replayable*, not unpredictable, so everything here comes from
``random.Random`` (no ``secrets``), and Faker is seeded from the same generator. Every test gets its own
instance, seeded from the run's data seed and the test's id (:meth:`RandomData.for_test`): a test's
names, e-mails, phone numbers and suffixes depend only on those two values - not on the xdist worker,
the test order or which other tests ran. The data seed is printed in the report header, so the data of
any failed test can be generated again: ``EVENTHUB_DATA_SEED=<seed> pytest "<test id>"``.

Uniqueness between runs never relies on these values: event titles also carry the run id
(``framework.utils.run_context``). Every value is obviously synthetic (``example.com`` e-mails,
``+91 9...`` mobile numbers). ``RandomData`` satisfies the data-source interfaces the factories declare
(``framework.factories.sources``).
"""

from __future__ import annotations

import random
import re
from collections.abc import Sequence
from typing import TypeVar

from faker import Faker

T = TypeVar("T")

# RFC 2606 reserved domain: mail to it is never delivered, so no real person is ever contacted.
SYNTHETIC_EMAIL_DOMAIN = "example.com"
_NOT_EMAIL_SAFE = re.compile(r"[^a-z0-9]")


class RandomData:
    def __init__(self, *, seed: int | str, locale: str = "en_IN") -> None:
        self._rng = random.Random(seed)  # str seeds are hashed with SHA-512: stable across processes
        self._faker = Faker(locale)
        self._faker.seed_instance(self._rng.getrandbits(64))  # one seed drives both generators

    @classmethod
    def for_test(cls, data_seed: int, test_id: str) -> RandomData:
        """The generator for one test: same data seed + same test id -> same values, wherever it runs."""
        return cls(seed=f"{data_seed}:{test_id}")

    def suffix(self, length: int = 6) -> str:
        """Lower-case hex token, e.g. ``"3fa9c1"``."""
        return f"{self._rng.getrandbits(4 * length):0{length}x}"

    def first_name(self) -> str:
        return str(self._faker.first_name())

    def last_name(self) -> str:
        return str(self._faker.last_name())

    def catch_phrase(self) -> str:
        return str(self._faker.catch_phrase())

    def pick(self, options: Sequence[T]) -> T:
        return self._rng.choice(options)

    def mobile_number(self) -> str:
        """``+91 9XXXXXXXXX`` - same shape as the UI placeholder ("+91 98765 43210")."""
        return f"+91 9{self._rng.randrange(10**9):09d}"

    def email(self, label: str) -> str:
        """``qa.<label>.<suffix>@example.com`` - recognisable, undeliverable, and tied to no account."""
        local = _NOT_EMAIL_SAFE.sub("", label.lower()) or "user"
        return f"qa.{local}.{self.suffix()}@{SYNTHETIC_EMAIL_DOMAIN}"


def new_data_seed() -> int:
    """A fresh seed for a run that was not given one (``EVENTHUB_DATA_SEED``)."""
    return random.Random().randrange(1, 10**9)
