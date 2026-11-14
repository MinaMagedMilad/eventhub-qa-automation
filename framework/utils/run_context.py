"""Identity of one test run: its run id and its data seed.

A *run* is one pytest invocation, however many pytest-xdist workers it uses. Both values are created once
(by the controller process, in ``conftest.py``), handed to every worker and printed in the report header.

* **Run id** - labels everything the run creates: event titles start with ``QA-AUTO <run id>-<worker>``,
  so leftover data can be traced to the exact run (CI passes its pipeline id via ``EVENTHUB_RUN_ID``).
  It is new for every run, even a replay, so titles never collide with an earlier run's leftovers.
* **Data seed** - every generated value derives from it (``framework.utils.random_data``), so a failed
  run's data can be generated again with ``EVENTHUB_DATA_SEED``.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone

MAIN_PROCESS = "main"
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,40}$")


@dataclass(frozen=True)
class RunContext:
    run_id: str
    data_seed: int
    worker: str = MAIN_PROCESS  # "main" without xdist, else the xdist worker id ("gw0", "gw1", ...)

    def __post_init__(self) -> None:
        for name, value in (("run id", self.run_id), ("worker", self.worker)):
            if not _SAFE_ID.match(value):
                raise ValueError(f"Invalid {name} {value!r}: use 1-40 characters from A-Z a-z 0-9 . _ -")
        if self.data_seed < 0:
            raise ValueError(f"Invalid data seed {self.data_seed}: use a whole number >= 0")

    @property
    def tag(self) -> str:
        """What generated data is labelled with, e.g. ``20261113-205800-ab12-gw1``."""
        return f"{self.run_id}-{self.worker}"

    def replay_hint(self) -> str:
        return f'EVENTHUB_DATA_SEED={self.data_seed} pytest "<test id>"'


def new_run_id(now: datetime | None = None) -> str:
    """Sortable, unique-enough run id: UTC timestamp + 4 random hex characters (uniqueness, not secrecy)."""
    moment = now or datetime.now(timezone.utc)
    return f"{moment:%Y%m%d-%H%M%S}-{random.Random().getrandbits(16):04x}"
