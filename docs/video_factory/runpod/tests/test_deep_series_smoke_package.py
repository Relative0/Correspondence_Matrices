from __future__ import annotations

import json
from pathlib import Path
import sys
import zipfile


RUNPOD_ROOT = Path(__file__).resolve().parents[1]
if str(RUNPOD_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNPOD_ROOT))

import deep_series_smoke_package as package


def load(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def test_deep_series_smoke_bundle_is_current_safe_and_complete():
    package.validate()
    record = load(package.OUTPUT_ROOT / "bundle_record.json")
    batch = load(package.OUTPUT_ROOT / "batch_manifest.json")
    audit = load(package.OUTPUT_ROOT / "exclusion_audit.json")
    proposal = load(package.OUTPUT_ROOT / "proposal.json")
    assert record["status"] == "ready_local_only_remote_not_authorized"
    assert record["cloud_uploaded"] is False
    assert record["runpod_resource_created"] is False
    assert record["total_frames"] == 4492
    assert batch["remote_or_paid_work_authorized"] is False
    assert batch["ordered_job_ids"] == [
        "conceptual-vs-measured-c01-smoke",
        "what-is-explicit-cm-c01-smoke",
    ]
    assert set(batch["expected_primitive_coverage"]) == {
        "boundary", "expression_matrix", "representation_compare", "result", "transform_compare"
    }
    assert audit["credential_values_included"] is False
    assert proposal["remote_or_paid_work_authorized"] is False
    assert proposal["authorization_ceiling"]["maximum_total_runpod_spend_usd"] == 2.0
    assert proposal["immutable_inputs"]["bundle_sha256"] == record["bundle_sha256"]


def test_bundle_contains_only_two_contracts_and_two_jobs():
    record = load(package.OUTPUT_ROOT / "bundle_record.json")
    with zipfile.ZipFile(package.OUTPUT_ROOT / record["bundle"]) as archive:
        names = archive.namelist()
    assert len([name for name in names if name.startswith("cm/contracts/")]) == 2
    assert len([name for name in names if name.startswith("cm/jobs/")]) == 2
    assert "runpod/deep_series_smoke_worker.py" in names
    assert "runpod/deep_series_smoke_batch.py" in names
    assert "runpod/deep_series_smoke_bootstrap.sh" in names
