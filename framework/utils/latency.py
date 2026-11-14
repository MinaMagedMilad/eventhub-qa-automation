"""Latency statistics for the performance suite (tests/performance)."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from typing import Any

# user_properties key the reporting plugin aggregates into the "API latency" table.
LATENCY_PROPERTY = "latency"


def latency_summary(endpoint: str, samples_ms: Sequence[float], p95_budget_ms: int) -> dict[str, Any]:
    if len(samples_ms) < 2:
        raise ValueError("at least two samples are needed for percentiles")
    p95 = statistics.quantiles(samples_ms, n=20, method="inclusive")[18]
    return {
        "endpoint": endpoint,
        "samples": len(samples_ms),
        "p50": round(statistics.median(samples_ms), 1),
        "p95": round(p95, 1),
        "max": round(max(samples_ms), 1),
        "budget": p95_budget_ms,
    }
