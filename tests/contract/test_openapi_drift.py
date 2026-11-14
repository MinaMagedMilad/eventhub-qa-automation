"""The published API spec must still be the one this suite was written against.

If the live spec changes, this test fails with a summary of what changed. Review it, then refresh the
versioned copy with ``pytest tests/contract/test_openapi_drift.py --update-openapi-snapshot`` and commit
the diff together with any test changes it requires.
"""

from __future__ import annotations

import json

import pytest

from framework.contract import SPEC_FILE, describe_differences, extract_spec


@pytest.mark.smoke
def test_live_spec_matches_the_versioned_snapshot(anonymous_api, contract, request):
    live = extract_spec(anonymous_api.service.swagger_init_script().expect_status(200).text)

    differences = describe_differences(contract.spec, live)

    if differences and request.config.getoption("--update-openapi-snapshot"):
        SPEC_FILE.write_text(json.dumps(live, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        pytest.skip(f"Snapshot updated ({len(differences)} change(s)); review the git diff of {SPEC_FILE.name}")
    assert not differences, "The live OpenAPI spec changed:\n  " + "\n  ".join(differences)
