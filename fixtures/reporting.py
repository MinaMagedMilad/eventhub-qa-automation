"""Suite-level conventions enforced at collection time, plus reporting.

* **Test type comes from the folder.** ``tests/<type>/...`` gets the ``<type>`` marker (contract, api,
  ui, e2e, performance). A test outside those folders is a collection error, so the structure can't
  quietly erode.
* **Performance tests are opt-in.** They are deselected unless the ``-m`` expression mentions
  ``performance`` (e.g. ``pytest -m performance``), so the functional gate stays fast and deterministic.
* ``@pytest.mark.acceptance("AC1", ...)`` is validated against US-114, expanded to ``ac1``..``ac5``
  markers and written to the JUnit XML / HTML report. A traceability matrix is printed at the end.
* Performance tests publish their latency statistics, printed as a table at the end of the run.
* **Every test report is redacted** before it leaves the process that ran the test (console, JUnit, HTML,
  xdist): the last line of defence behind the redaction at each source (``framework.utils.redaction``).
* Parallelism is capped: each EventHub sandbox holds max 9 bookings / 6 custom events and silently
  replaces the oldest, so too many concurrent workers on one account would evict each other's data.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from framework.constants import SANDBOX_MAX_BOOKINGS, SANDBOX_MAX_CUSTOM_EVENTS
from framework.utils.latency import LATENCY_PROPERTY
from framework.utils.redaction import redact_text

STORY_ID = "US-114"
ACCEPTANCE_CRITERIA = {
    "AC1": "Booking is created and a confirmation with a booking reference is shown",
    "AC2": "Total price = ticket price x number of tickets",
    "AC3": "The booking appears in My Bookings",
    "AC4": "A booking can be cancelled",
    "AC5": "The same works through the API (POST /api/bookings)",
}
TEST_TYPES = ("contract", "api", "ui", "e2e", "performance")
OPT_IN_TYPES = ("performance",)
MAX_PARALLEL_WORKERS = 4


# ---------------------------------------------------------------------------------------------
# Parallelism guard (pytest-xdist) + plugin registration
# ---------------------------------------------------------------------------------------------
@pytest.hookimpl(optionalhook=True)
def pytest_xdist_auto_num_workers(config: pytest.Config) -> int:
    return min(os.cpu_count() or 1, MAX_PARALLEL_WORKERS)


def pytest_configure(config: pytest.Config) -> None:
    workers = getattr(config.option, "numprocesses", None)
    if isinstance(workers, int) and workers > MAX_PARALLEL_WORKERS:
        raise pytest.UsageError(
            f"-n {workers} is not allowed: the EventHub sandbox caps ({SANDBOX_MAX_BOOKINGS} bookings / "
            f"{SANDBOX_MAX_CUSTOM_EVENTS} events per user, oldest silently replaced) make more than "
            f"{MAX_PARALLEL_WORKERS} concurrent workers per account unsafe."
        )
    if not hasattr(config, "workerinput"):  # controller / single process: owns the summaries
        config.pluginmanager.register(TraceabilityReport(), "eventhub-traceability")
        config.pluginmanager.register(LatencyReport(), "eventhub-latency")


# ---------------------------------------------------------------------------------------------
# Redaction of every test report (failure text and captured output)
# ---------------------------------------------------------------------------------------------
@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Any:
    report = yield
    _redact_report(report)
    return report


def _redact_report(report: pytest.TestReport) -> None:
    # The failure text includes the arguments of every frame in the traceback, so a secret passed down the
    # stack (a header dict, a storage state) would otherwise reach the report verbatim.
    if report.longrepr is not None and not isinstance(report.longrepr, tuple):  # tuple: a skip reason
        text = str(report.longrepr)
        redacted = redact_text(text)
        if redacted != text:  # keep pytest's structured repr unless something had to be masked
            report.longrepr = redacted
    report.sections = [(title, redact_text(content)) for title, content in report.sections]


# ---------------------------------------------------------------------------------------------
# Collection: type markers from folders, opt-in types, acceptance-criteria traceability
# ---------------------------------------------------------------------------------------------
def _test_type(item: pytest.Item) -> str | None:
    parts = Path(str(item.path)).parts
    if "tests" not in parts:
        return None
    below = parts[parts.index("tests") + 1 :]
    return below[0] if len(below) > 1 and below[0] in TEST_TYPES else None


@pytest.hookimpl(tryfirst=True)  # type markers must exist before pytest's own -m filtering runs
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    selected, deselected = [], []
    mark_expression = config.option.markexpr or ""
    for item in items:
        test_type = _test_type(item)
        if test_type is None:
            raise pytest.UsageError(
                f"{item.nodeid}: tests must live in tests/<type>/ where <type> is one of {', '.join(TEST_TYPES)}"
            )
        item.add_marker(test_type)
        if test_type in OPT_IN_TYPES and test_type not in mark_expression:
            deselected.append(item)
            continue
        selected.append(item)
        _apply_acceptance_criteria(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


def _apply_acceptance_criteria(item: pytest.Item) -> None:
    criteria: set[str] = set()
    for mark in item.iter_markers("acceptance"):
        for criterion in mark.args:
            if criterion not in ACCEPTANCE_CRITERIA:
                valid = ", ".join(ACCEPTANCE_CRITERIA)
                raise pytest.UsageError(f"{item.nodeid}: unknown acceptance criterion {criterion!r} (valid: {valid})")
            criteria.add(criterion)
    if criteria:
        for criterion in sorted(criteria):
            item.add_marker(criterion.lower())
        item.user_properties.append(("story", STORY_ID))
        item.user_properties.append(("acceptance", ",".join(sorted(criteria))))


# ---------------------------------------------------------------------------------------------
# End-of-run reports (work with and without pytest-xdist: reports reach the controller)
# ---------------------------------------------------------------------------------------------
class TraceabilityReport:
    def __init__(self) -> None:
        self.results: dict[str, list[str]] = defaultdict(list)

    @staticmethod
    def _outcome(report: pytest.TestReport) -> str | None:
        if report.when == "call":
            if hasattr(report, "wasxfail"):
                return "xpassed" if report.passed else "xfailed"
            return report.outcome
        if report.when == "setup" and not report.passed:
            return "skipped" if report.skipped else "error"
        return None

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        outcome = self._outcome(report)
        criteria = dict(report.user_properties).get("acceptance")
        if outcome and criteria:
            for criterion in str(criteria).split(","):
                self.results[criterion].append(outcome)

    def pytest_terminal_summary(self, terminalreporter: Any) -> None:
        if not self.results:
            return
        tr = terminalreporter
        tr.write_sep("=", f"{STORY_ID} acceptance-criteria traceability")
        tr.write_line(f"{'Criterion':<10}{'Tests':>6}{'Passed':>8}{'Failed':>8}{'XFail':>7}{'Skipped':>9}  Description")
        for criterion, description in ACCEPTANCE_CRITERIA.items():
            outcomes = self.results.get(criterion, [])
            failed = sum(o in ("failed", "error", "xpassed") for o in outcomes)
            tr.write_line(
                f"{criterion:<10}{len(outcomes):>6}{outcomes.count('passed'):>8}{failed:>8}"
                f"{outcomes.count('xfailed'):>7}{outcomes.count('skipped'):>9}  {description}"
            )
        tr.write_line("XFail = known defect reproduced (see README, 'Defects found'); it does not fail the run.")


class LatencyReport:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when == "call":
            for name, value in report.user_properties:
                if name == LATENCY_PROPERTY:
                    self.rows.append(json.loads(str(value)))

    def pytest_terminal_summary(self, terminalreporter: Any) -> None:
        if not self.rows:
            return
        tr = terminalreporter
        tr.write_sep("=", "API latency (ms)")
        tr.write_line(f"{'Endpoint':<26}{'Samples':>8}{'p50':>8}{'p95':>8}{'Max':>8}{'p95 budget':>12}  Result")
        for row in sorted(self.rows, key=lambda r: r["endpoint"]):
            verdict = "within budget" if row["p95"] <= row["budget"] else "OVER BUDGET"
            tr.write_line(
                f"{row['endpoint']:<26}{row['samples']:>8}{row['p50']:>8.0f}{row['p95']:>8.0f}{row['max']:>8.0f}"
                f"{row['budget']:>12}  {verdict}"
            )


# ---------------------------------------------------------------------------------------------
# pytest-html: extra "Acceptance" column (hooks are optional, so pytest-html stays optional too)
# ---------------------------------------------------------------------------------------------
@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_header(cells: list[str]) -> None:
    cells.insert(2, "<th>Acceptance</th>")


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_row(report: pytest.TestReport, cells: list[str]) -> None:
    cells.insert(2, f"<td>{dict(report.user_properties).get('acceptance', '')}</td>")
