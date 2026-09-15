"""Offline-only checks for the proposed corpus Runpod transport."""
import base64
import hashlib
import json
from pathlib import Path

import pytest

from test_cm_runpod_http_transport_independent import load_module


controller = load_module("offline_corpus_controller", "runpod_corpus_controller_v5.py")
preflight = controller.preflight
server = load_module("offline_corpus_bootstrap", "http_transport_bootstrap.py")


def _manifest():
    return json.loads(controller.MANIFEST_PATH.read_text(encoding="utf-8"))


def test_frozen_remote_program_has_only_the_corpus_command():
    code = controller.base.REMOTE_CODE
    compile(code, "<frozen-corpus-remote>", "exec")
    assert "scripts/cm_corpus_memory_validation.py" in code
    assert "study/CORPUS-MEMORY-SELECTION.json" in code
    assert "tests/test_cm_corpus_memory_validation.py" in code
    assert "scripts/cm_memory_estimator_study.py" not in code
    assert code.count("corpus_summary") == 1
    assert code.count("'corpus-study'") == 2


def test_historical_upload_manifest_is_immutable_and_live_source_drift_is_explicit():
    manifest = _manifest()
    assert manifest["authorization_status"] == "pending"
    assert len(manifest["files"]) == 71
    assert manifest["bytes"] == 1_680_864
    assert len({row["target"] for row in manifest["files"]}) == 71
    assert not any(".env" in row["source"].lower() for row in manifest["files"])
    assert hashlib.sha256(controller.MANIFEST_PATH.read_bytes()).hexdigest() == (
        "9149a41912e8b909fb8ae8871a9b72356a5f35a5cb3938a8034e2cbe51aa1e11"
    )
    mismatches = []
    for row in manifest["files"]:
        source = controller.base.ROOT / row["source"]
        data = source.read_bytes()
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            mismatches.append(row["source"])
    assert mismatches == [
        "bitset_backend.py",
        "cm_bench.py",
        "cm_exprlib.py",
        "cmbench/backends/robdd_dd.py",
        "cmbench/config.py",
        "cmbench/enums.py",
    ]


def test_historical_bundle_rebuild_refuses_live_source_drift():
    with pytest.raises(RuntimeError, match="approved upload hash mismatch: bitset_backend.py"):
        controller.base.make_bundle(_manifest())


def test_payload_fits_transport_cap_and_bootstrap_accepts_exact_schema(monkeypatch):
    manifest = _manifest()
    bundle = b"frozen-corpus-bundle-fixture\n" * 1_000
    raw = controller.prepare_payload(bundle, manifest, 1_000)
    assert len(raw) <= 1 << 20
    monkeypatch.setattr(server, "EXPECTED_SIZE", len(raw))
    monkeypatch.setattr(server, "EXPECTED_HASH", hashlib.sha256(raw).hexdigest())
    decoded = server.validate_payload(raw)
    assert hashlib.sha256(base64.b64decode(decoded["bundle"])).hexdigest() == hashlib.sha256(bundle).hexdigest()
    assert json.loads(base64.b64decode(decoded["manifest"]))["package_id"] == manifest["package_id"]


def test_create_request_retains_zero_volume_and_resource_caps():
    body = controller.create_payload("cm-corpus-study-0123456789ab", {"id": "cpu3c"}, "offline-token", b"payload", 1_000)
    assert body["vcpuCount"] == 2
    assert "memoryInGb" not in body  # 4 GiB is validated from the selected flavor response.
    assert body["containerDiskInGb"] == 12
    assert type(body["volumeInGb"]) is int and body["volumeInGb"] == 0
    assert "networkVolumeId" not in body
    assert body["ports"] == ["8080/http", "8081/http"]


def test_prior_three_allocations_are_locally_reconciled():
    prior = preflight.prior_attempts()
    assert prior == {
        "pod_ids": ["8voqzr4b1a4qti", "eidn8uu97y3b6q", "s2dpiij1msutml"],
        "cleanup_verified": True,
        "minimum_delayed_billing_reserve_usd": 0.03,
    }


@pytest.mark.parametrize("rate,prior,ready", [
    (0.06, 0.03, True),
    (0.25, 0.03, True),
    (0.250001, 0.03, False),
    (0.06, 0.029999, False),
    (0.25, 0.11, True),
    (0.25, 0.12, False),
    (0.25, 0.13, False),
])
def test_budget_includes_prior_reserve_and_storage(rate, prior, ready):
    result = preflight.budget(rate, prior)
    assert result["ready"] is ready
    assert result["projected_campaign_cost_usd"] == pytest.approx(
        prior + (rate + preflight.STORAGE_RESERVE_PER_HOUR) / 3
    )


def test_controller_atomic_write_refuses_overwrite(tmp_path: Path):
    target = tmp_path / "state.json"
    controller.write(target, {"complete": True})
    assert json.loads(target.read_text()) == {"complete": True}
    with pytest.raises(FileExistsError):
        controller.write(target, {"complete": False})


def test_controller_requires_hash_bound_exact_authorization(monkeypatch, tmp_path: Path):
    proposal = tmp_path / "proposal.md"
    manifest = tmp_path / "manifest.json"
    authorization = tmp_path / "authorization.json"
    proposal.write_text("frozen proposal\n", encoding="utf-8")
    manifest.write_text("{\"authorization_status\":\"pending\"}\n", encoding="utf-8")
    monkeypatch.setattr(controller, "PROPOSAL_PATH", proposal)
    monkeypatch.setattr(controller, "MANIFEST_PATH", manifest)
    monkeypatch.setattr(controller, "AUTHORIZATION_PATH", authorization)
    with pytest.raises(RuntimeError, match="authorization record is absent"):
        controller.require_authorization()
    record = {
        "schema": "cm-runpod-corpus-authorization/v1", "authorized": True,
        "one_create": True, "no_replacement": True,
        "source_files": 71, "cases": 35, "jobs": 420, "calls": 630,
        "container_disk_gb": 12, "pod_volume_gb": 0, "network_volume": False,
        "lifetime_seconds": 1200, "phase_cap_usd": 0.10, "campaign_cap_usd": 0.20,
        "proposal_sha256": hashlib.sha256(proposal.read_bytes()).hexdigest(),
        "upload_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    }
    authorization.write_text(json.dumps(record), encoding="utf-8")
    assert controller.require_authorization()["calls"] == 630
    record["no_replacement"] = False
    authorization.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(RuntimeError, match="scope mismatch"):
        controller.require_authorization()
