"""OpenAPI contract checks: does a real response match what the published API spec promises?

The spec is a versioned copy of the live Swagger document (``contracts/eventhub-openapi.json``), so
every contract change shows up as a reviewable diff. ``tests/contract/test_openapi_drift.py`` fails as
soon as the live spec stops matching that copy.

Two kinds of violations are reported, each with the JSON path it concerns:
  * the HTTP status is not documented for the operation (``location == "<status>"``);
  * the body does not validate against the documented response schema (``location == "data/totalPrice"``...).

Deviations that are already filed as defects can be *tolerated* by the generic contract tests (see
``deviations.py``), so those tests keep catching every **new** deviation while the known ones are
asserted strictly - and tracked - by their own known-defect tests.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from openapi_schema_validator import OAS30Validator

from framework.api.http import ApiResponse
from framework.config import PROJECT_ROOT
from framework.contract.deviations import KNOWN_DEVIATIONS, KnownDeviation

SPEC_FILE = PROJECT_ROOT / "contracts" / "eventhub-openapi.json"
STATUS_LOCATION = "<status>"


@dataclass(frozen=True)
class Violation:
    operation: str  # e.g. "POST /bookings"
    status: int
    location: str  # "<status>", "" (whole body) or a JSON path such as "data/totalPrice"
    message: str

    def __str__(self) -> str:
        return f"[{self.operation} -> {self.status}] {self.location or '<body>'}: {self.message}"


class OpenApiContract:
    def __init__(self, spec: Mapping[str, Any]) -> None:
        self.spec = spec
        self._validators: dict[tuple[str, str, int], Any] = {}

    @classmethod
    def from_file(cls, path: Path = SPEC_FILE) -> OpenApiContract:
        return cls(json.loads(path.read_text(encoding="utf-8")))

    # ---- spec lookup -------------------------------------------------------------------------
    def operation(self, method: str, path: str) -> Mapping[str, Any]:
        """``path`` is the documented template relative to the server URL, e.g. ``/bookings/{id}``."""
        try:
            return self.spec["paths"][path][method.lower()]
        except KeyError:
            raise KeyError(f"{method.upper()} {path} is not documented in the OpenAPI spec") from None

    def documented_statuses(self, method: str, path: str) -> list[int]:
        return sorted(int(code) for code in self.operation(method, path).get("responses", {}))

    def _validator(self, method: str, path: str, status: int) -> Any | None:
        key = (method.upper(), path, status)
        if key not in self._validators:
            response = self.operation(method, path)["responses"].get(str(status), {})
            schema = response.get("content", {}).get("application/json", {}).get("schema")
            # Root document = schema + components, so "#/components/..." references resolve inside it.
            self._validators[key] = (
                None
                if schema is None
                else OAS30Validator(
                    {**schema, "components": self.spec.get("components", {})},
                    format_checker=OAS30Validator.FORMAT_CHECKER,
                )
            )
        return self._validators[key]

    # ---- checks ------------------------------------------------------------------------------
    def violations(self, response: ApiResponse, method: str, path: str) -> list[Violation]:
        operation = f"{method.upper()} {path}"
        documented = self.documented_statuses(method, path)
        if response.status not in documented:
            listed = ", ".join(map(str, documented))
            return [
                Violation(
                    operation,
                    response.status,
                    STATUS_LOCATION,
                    f"HTTP {response.status} is not documented (documented: {listed})",
                )
            ]
        validator = self._validator(method, path, response.status)
        if validator is None:
            return []
        try:
            body = json.loads(response.text)
        except json.JSONDecodeError:
            return [Violation(operation, response.status, "", "response body is not JSON")]
        return [
            Violation(operation, response.status, "/".join(map(str, error.absolute_path)), error.message)
            for error in sorted(validator.iter_errors(body), key=lambda e: [str(p) for p in e.absolute_path])
        ]

    def assert_conforms(
        self,
        response: ApiResponse,
        method: str,
        path: str,
        *,
        tolerate: Iterable[KnownDeviation] = KNOWN_DEVIATIONS,
    ) -> None:
        """Fail with every violation listed, ignoring those already filed as known defects.

        Pass ``tolerate=()`` to assert strict conformance (used by the known-defect tests).
        """
        tolerated = tuple(tolerate)
        problems = [v for v in self.violations(response, method, path) if not any(d.matches(v) for d in tolerated)]
        if problems:
            listing = "\n".join(f"  - {v}" for v in problems)
            raise AssertionError(
                response.describe(f"Response breaks the OpenAPI contract ({len(problems)} violation(s)):\n{listing}")
            )


@cache
def default_contract() -> OpenApiContract:
    return OpenApiContract.from_file()
