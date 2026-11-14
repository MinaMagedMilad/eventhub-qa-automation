"""Read the OpenAPI document the API is publishing *right now*, and compare it with the versioned copy.

EventHub serves its docs with swagger-ui-express, which embeds the spec in ``/api/docs/swagger-ui-init.js``
as ``var options = {"swaggerDoc": {...}, ...};`` (there is no plain JSON endpoint). ``raw_decode`` parses
exactly that one JSON object, so surrounding JavaScript can change without breaking the extraction.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

SWAGGER_INIT_PATH = "/docs/swagger-ui-init.js"
_OPTIONS_MARKER = "var options = "
_HTTP_METHODS = ("get", "put", "post", "delete", "patch", "head", "options")


def extract_spec(swagger_init_js: str) -> dict[str, Any]:
    start = swagger_init_js.find(_OPTIONS_MARKER)
    if start == -1:
        raise ValueError(f"'{_OPTIONS_MARKER.strip()}' not found in swagger-ui-init.js - has the docs setup changed?")
    options, _ = json.JSONDecoder().raw_decode(swagger_init_js, start + len(_OPTIONS_MARKER))
    spec = options.get("swaggerDoc")
    if not isinstance(spec, dict):
        raise ValueError("swagger-ui-init.js contains no 'swaggerDoc' object")
    return spec


def _operations(spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        f"{method.upper()} {path}": operation
        for path, item in spec.get("paths", {}).items()
        for method, operation in item.items()
        if method in _HTTP_METHODS
    }


def describe_differences(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> list[str]:
    """Human-readable summary of how ``actual`` differs from ``expected`` (empty list = identical)."""
    if expected == actual:
        return []
    changes: list[str] = []
    old_ops, new_ops = _operations(expected), _operations(actual)
    changes += [f"operation removed: {op}" for op in sorted(old_ops.keys() - new_ops.keys())]
    changes += [f"operation added:   {op}" for op in sorted(new_ops.keys() - old_ops.keys())]
    changes += [
        f"operation changed: {op}" for op in sorted(old_ops.keys() & new_ops.keys()) if old_ops[op] != new_ops[op]
    ]
    old_schemas = expected.get("components", {}).get("schemas", {})
    new_schemas = actual.get("components", {}).get("schemas", {})
    changes += [f"schema removed: {name}" for name in sorted(old_schemas.keys() - new_schemas.keys())]
    changes += [f"schema added:   {name}" for name in sorted(new_schemas.keys() - old_schemas.keys())]
    changes += [
        f"schema changed: {name}"
        for name in sorted(old_schemas.keys() & new_schemas.keys())
        if old_schemas[name] != new_schemas[name]
    ]
    for section in ("openapi", "info", "servers", "tags"):
        if expected.get(section) != actual.get(section):
            changes.append(f"'{section}' changed")
    return changes or ["documents differ outside paths/schemas/info"]
