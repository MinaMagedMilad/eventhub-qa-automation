"""Root conftest: wires the fixture plugins together and gives the run its identity.

All other logic lives in ``framework`` / ``fixtures``. The run identity (run id + data seed, see
``framework.utils.run_context``) is created here because only the root conftest sees both sides of a
parallel run: the pytest-xdist controller creates it once and hands it to every worker. It is printed in
the report header and in the HTML report's Environment table, so every failure can be traced to its run
and its generated data replayed.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from framework.config import get_settings
from framework.utils.random_data import new_data_seed
from framework.utils.run_context import RunContext, new_run_id

pytest_plugins = [
    "fixtures.auth",
    "fixtures.api",
    "fixtures.data",
    "fixtures.contract",
    "fixtures.ui",
    "fixtures.reporting",
]

_RUN_CONTEXT = pytest.StashKey[RunContext]()
_RUN_ID_INPUT = "eventhub_run_id"
_DATA_SEED_INPUT = "eventhub_data_seed"


def _run_context(config: pytest.Config) -> RunContext:
    """Create the run identity once per process (idempotent: several hooks may ask first)."""
    if _RUN_CONTEXT not in config.stash:
        workerinput: dict[str, Any] | None = getattr(config, "workerinput", None)
        if workerinput is not None:  # xdist worker: reuse the controller's identity
            context = RunContext(
                run_id=workerinput[_RUN_ID_INPUT],
                data_seed=workerinput[_DATA_SEED_INPUT],
                worker=workerinput["workerid"],
            )
        else:
            try:
                settings = get_settings()
                context = RunContext(
                    run_id=settings.run_id or new_run_id(),  # CI passes its own id (EVENTHUB_RUN_ID)
                    data_seed=new_data_seed() if settings.data_seed is None else settings.data_seed,
                )
            except (ValidationError, ValueError) as exc:
                raise pytest.UsageError(f"Invalid EventHub configuration:\n{exc}") from None
        config.stash[_RUN_CONTEXT] = context
    return config.stash[_RUN_CONTEXT]


def pytest_configure(config: pytest.Config) -> None:
    _run_context(config)  # fail fast on an invalid EVENTHUB_RUN_ID / EVENTHUB_DATA_SEED


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node: Any) -> None:
    """pytest-xdist: pass the run identity to each worker as it starts."""
    context = _run_context(node.config)
    node.workerinput[_RUN_ID_INPUT] = context.run_id
    node.workerinput[_DATA_SEED_INPUT] = context.data_seed


def pytest_report_header(config: pytest.Config) -> list[str]:
    context = _run_context(config)
    return [
        f"eventhub run id: {context.run_id}",
        f"eventhub data seed: {context.data_seed} (replay a test's data: {context.replay_hint()})",
    ]


@pytest.hookimpl(optionalhook=True)
def pytest_metadata(metadata: dict[str, Any], config: pytest.Config) -> None:
    """pytest-html: show the run identity in the report's Environment table."""
    context = _run_context(config)
    metadata["EventHub run id"] = context.run_id
    metadata["EventHub data seed"] = context.data_seed
    metadata["Replay a test's data"] = context.replay_hint()


@pytest.fixture(scope="session")
def run_context(pytestconfig: pytest.Config) -> RunContext:
    return _run_context(pytestconfig)
