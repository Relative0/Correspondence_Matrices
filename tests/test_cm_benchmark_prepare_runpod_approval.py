from pathlib import Path

import pytest

from scripts.cm_benchmark_prepare_runpod_approval import build_request


EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "docs/audits/2026-09-13-cm-benchmark-campaign/prelaunch-008/UPLOAD_MANIFEST.json"
)


@pytest.mark.skipif(
    not EVIDENCE.exists(),
    reason="frozen prelaunch bundles are excluded from the source-only integration",
)
def test_approval_request_is_exact_and_non_authorizing():
    result = build_request()
    assert result["authorization_granted"] is False
    assert result["status"] == "exact_approval_pending"
    assert result["upload"]["authorized"] is False
    assert result["upload"]["bundle_count"] == 11
    assert result["resource_request"]["maximum_concurrent_pods"] == 1
    assert result["envelope"]["maximum_total_pod_hours"] == 16
    assert result["envelope"]["maximum_total_runpod_charges_usd"] == 50
    assert sum(result["envelope"]["stages_max_hours"].values()) == 16
    assert result["excluded_effects"]["production_changes"] is False
