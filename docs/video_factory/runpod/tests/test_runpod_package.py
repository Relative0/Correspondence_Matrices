from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT.parent
CM_REPO = FACTORY.parents[1]
TOOLS = CM_REPO.parent / "PoP" / "Tools"
IVC = TOOLS / "Master-Video-Creator"
POP = TOOLS / "POP-Video-Creator"
sys.path.insert(0, str(ROOT))

import batch_runner
import controller
import execute_approved_v4
import package_bundle
import runpod_watchdog
import worker


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_allowlist_expands_required_code_and_excludes_sensitive_or_windows_paths():
    allowlist = json.loads((ROOT / "allowlist.json").read_text("utf-8"))
    selected = package_bundle.expand(
        allowlist, {"cm": FACTORY, "ivc": IVC, "pop": POP, "runpod": ROOT}
    )
    paths = {path for path, _data, _category in selected}
    assert "ivc/src/ivc_generators/video_spec.py" in paths
    assert "ivc/schemas/orchestration_response.schema.json" in paths
    assert "pop/pop_video/render/cm_science.py" in paths
    assert "cm/proofs/cm-foundation/resolved.spec.json" in paths
    assert all(".env" not in path and "__pycache__" not in path for path in paths)
    assert all(b"C:\\" not in data for _path, data, _category in selected)


def test_normalized_assembly_uses_bundle_placeholder():
    source = FACTORY / "proofs" / "cm-foundation" / "assembly.spec.json"
    data = package_bundle.normalized_bytes(
        "cm/proofs/cm-foundation/assembly.spec.json", source
    )
    request = json.loads(data)["slots"][0]["source"]["request"]
    assert request["spec"] == "${BUNDLE_ROOT}/cm/proofs/cm-foundation/resolved.spec.json"


def test_worker_bundle_verification_rejects_changed_payload(tmp_path):
    payload = tmp_path / "payload.txt"
    payload.write_text("bound", encoding="utf-8")
    files = [{"path": "payload.txt", "size": 5, "sha256": digest(payload), "category": "fixture"}]
    manifest = {"files": files, "payload_sha256": hashlib.sha256(worker.canonical_bytes(files)).hexdigest()}
    (tmp_path / "package_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    worker.verify_bundle(tmp_path)
    payload.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="bundle file mismatch"):
        worker.verify_bundle(tmp_path)


def test_batch_resume_requires_a_passed_result(tmp_path):
    result = tmp_path / "render_result.json"
    result.write_text(json.dumps({"status": "failed", "passed": False}), encoding="utf-8")
    assert not batch_runner.verified_finished(result)
    result.write_text(json.dumps({"status": "passed", "passed": True}), encoding="utf-8")
    assert batch_runner.verified_finished(result)
    assert not batch_runner.verified_finished(result, "a" * 64)
    result.write_text(json.dumps({
        "status": "passed", "passed": True,
        "technical_observations": {"bundle_payload_sha256": "a" * 64},
    }), encoding="utf-8")
    assert batch_runner.verified_finished(result, "a" * 64)


class FakeBackend:
    def __init__(self, *, wrong_shape: bool = False):
        self.wrong_shape = wrong_shape
        self.creates = 0
        self.deleted = []
        self.pods = set()
        self.tokens = []
        self.execution_limits = None

    def quote(self, authorization):
        return 0.18

    def create(self, authorization):
        self.creates += 1
        self.pods.add("owned-1")
        return {"id": "owned-1"}

    def shape(self, pod_id):
        return {
            "cloud_type": "SECURE", "cpu_flavor": "cpu5c", "vcpu": 4,
            "ram_gb": 8 if not self.wrong_shape else 4,
            "container_disk_gb": 30, "volume_gb": 0,
        }

    def upload(self, pod_id, bundle, bootstrap_token):
        self.tokens.append(bootstrap_token)

    def execute(self, pod_id, batch_sha256, bootstrap_token, timeout_seconds, max_total_cost_usd):
        assert bootstrap_token == self.tokens[-1]
        self.execution_limits = (timeout_seconds, max_total_cost_usd)

    def download(self, pod_id, destination):
        destination.mkdir(parents=True, exist_ok=True)
        media = destination / "video.mp4"
        media.write_bytes(b"video")
        result = destination / "render_result.json"
        result.write_text(json.dumps({
            "status": "passed", "passed": True, "outputs": {"video": digest(media)}
        }), encoding="utf-8")
        return [media, result]

    def delete(self, pod_id):
        self.deleted.append(pod_id)
        self.pods.discard(pod_id)

    def owned_inventory(self, authorization_id):
        return set(self.pods)


def authorization(bundle: Path, batch: Path) -> controller.Authorization:
    return controller.Authorization(
        authorization_id="cm-video-proof3-remote-v1", batch_id="cm-video-level1-proof3-v1",
        batch_manifest_sha256=digest(batch), bundle_sha256=digest(bundle),
        image="cm-video-worker:fixture", cloud_type="SECURE", cpu_flavor="cpu5c",
        vcpu=4, ram_gb=8, container_disk_gb=30, volume_gb=0, country_codes=(),
        max_creates=1, max_parallel_pods=1, max_rate_usd_per_hour=0.27,
        max_total_cost_usd=0.25, timeout_seconds=1800, cleanup="delete_on_terminal",
    )


def test_controller_binds_hashes_limits_token_results_cleanup_and_reconciliation(tmp_path):
    bundle = tmp_path / "bundle.zip"
    batch = tmp_path / "batch.json"
    bundle.write_bytes(b"bundle")
    batch.write_bytes(b"batch")
    backend = FakeBackend()
    events = tmp_path / "events.jsonl"
    ctl = controller.OwnedPodController(backend, events)
    ctl.run(authorization(bundle, batch), bundle, batch, tmp_path / "downloads")
    assert backend.creates == 1
    assert backend.deleted == ["owned-1"]
    assert backend.execution_limits == (1800, 0.25)
    log = events.read_text("utf-8")
    assert backend.tokens[0] not in log
    assert log.index("results_verified") < log.index("owned_pod_deleted") < log.index("inventory_reconciled")


def test_shape_mismatch_fails_closed_without_replacement_and_deletes_only_owned(tmp_path):
    bundle = tmp_path / "bundle.zip"
    batch = tmp_path / "batch.json"
    bundle.write_bytes(b"bundle")
    batch.write_bytes(b"batch")
    backend = FakeBackend(wrong_shape=True)
    ctl = controller.OwnedPodController(backend, tmp_path / "events.jsonl")
    with pytest.raises(RuntimeError, match="shape"):
        ctl.run(authorization(bundle, batch), bundle, batch, tmp_path / "downloads")
    assert backend.creates == 1
    assert backend.deleted == ["owned-1"]


def test_container_definition_is_digest_pinned_and_has_no_service_port():
    dockerfile = (ROOT / "Dockerfile").read_text("utf-8")
    assert "FROM python:3.10.15-slim-bookworm@sha256:" in dockerfile
    assert "EXPOSE" not in dockerfile


def test_watchdog_acknowledges_clean_owned_inventory_before_create(tmp_path, monkeypatch):
    assert runpod_watchdog.ROOT == CM_REPO
    state_path = tmp_path / "state.json"
    ack_path = tmp_path / "ack.json"
    events = tmp_path / "events.jsonl"
    state = {
        "authorization_id": "auth-fixture",
        "pod_name": "owned-fixture",
        "pod_id": None,
        "cleanup_epoch": 1234.5,
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(runpod_watchdog, "session", FakeSession)
    monkeypatch.setattr(runpod_watchdog, "owned", lambda _client, _state: set())
    assert runpod_watchdog.arm(state_path, ack_path, events) == state
    ack = json.loads(ack_path.read_text("utf-8"))
    assert ack["status"] == "armed"
    assert ack["state_sha256"] == digest(state_path)
    assert ack["credential_value_recorded"] is False
    assert '"event": "armed"' in events.read_text("utf-8")


def test_approved_controller_verifies_the_frozen_bundle_without_live_source_reads():
    preflight = json.loads((ROOT / "preflight.json").read_text("utf-8"))
    bundle = ROOT / preflight["bundle"]["file"]
    result = execute_approved_v4.verify_frozen_bundle(bundle, FACTORY / "batch_manifest.json")
    assert result == {"files": 156, "bundle_bytes": 419939}
