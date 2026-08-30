from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


BASE = (
    Path(__file__).resolve().parents[1]
    / "docs/audits/2026-08-25-cm-deep-performance/remaining-work"
    / "maximal-safe-20260827-192909/continuation-20260829-125214"
)


@pytest.fixture(scope="module")
def modules():
    sys.path.insert(0, str(BASE))
    try:
        controller = importlib.import_module("runpod_w8_logikbench_conversion_controller_v1")
        preflight = importlib.import_module("http_w8_logikbench_conversion_preflight_v1")
        verifier = importlib.import_module("verify_w8_logikbench_conversion_upload_v2")
        yield controller, preflight, verifier
    finally:
        sys.path.remove(str(BASE))


def test_exact_v2_bundle_verifies(modules):
    _controller, _preflight, verifier = modules
    assert verifier.verify() == {
        "verified": True,
        "manifest_sha256": "5365b4362fc42790bf7107c6b8da29ec61b79faf8d69ac40bcfeb77a87640354",
        "bundle_sha256": "1b3796d6ded0f6d1b0d6266c5e783f1b0687aae9c7ecfdac901ad625c6e6ff95",
        "bundle_bytes": 204586,
        "source_files": 159,
        "source_bytes": 617274,
        "static_candidate_clusters": 70,
        "contains_credentials": False,
        "performance_measurement": False,
    }


def test_authorization_hashes_and_scope_are_frozen(modules):
    controller, _preflight, _verifier = modules
    authorization = controller.require_authorization()
    assert authorization["one_create"] is True
    assert authorization["no_replacement_within_this_controller"] is True
    assert authorization["system_packages_allowed"] == ["yosys"]
    assert authorization["source_builds_allowed"] == []
    assert authorization["campaign_cap_usd"] == 5.0
    assert authorization["performance_measurement"] is False


def test_create_payload_has_exact_resource_and_transport_bounds(modules):
    controller, _preflight, _verifier = modules
    manifest = controller.load(controller.MANIFEST_PATH)
    bundle = controller.frozen_bundle(manifest)
    raw = controller.prepare_payload(bundle, manifest, 1000.0)
    body = controller.create_payload(
        "cm-w8-logikbench-convert-v1-000000000000",
        {"id": "cpu3c"},
        "t" * 32,
        raw,
        1000.0,
    )
    assert len(raw) <= 8 << 20
    assert body["computeType"] == "CPU"
    assert body["cloudType"] == "SECURE"
    assert body["vcpuCount"] == 2
    assert body["containerDiskInGb"] == 12
    assert type(body["volumeInGb"]) is int and body["volumeInGb"] == 0
    assert body["ports"] == ["8080/http", "8081/http"]
    assert body["env"]["CM_HARD_DEADLINE"] == "2080.0"


def test_local_cost_bound_counts_each_pod_once(tmp_path, monkeypatch, modules):
    _controller, preflight, _verifier = modules
    monkeypatch.setattr(preflight, "HERE", tmp_path)
    rows = [
        ("a", {"pod_id": "pod-a", "pod_created": True, "estimated_compute_cost_usd": 0.01}),
        ("b", {"pod_id": "pod-a", "pod_created": True, "estimated_compute_cost_usd": 0.02}),
        ("c", {"pod_id": "pod-b", "pod_created": True, "estimated_compute_cost_usd": None}),
        ("d", {"pod_id": "pod-c", "pod_created": False, "estimated_compute_cost_usd": 99}),
    ]
    for name, value in rows:
        output = tmp_path / name
        output.mkdir()
        (output / "RUN.json").write_text(json.dumps(value), encoding="utf-8")
    result = preflight.local_campaign_cost_bound()
    assert result["unique_created_pods"] == 2
    assert result["known_estimated_compute_cost_usd"] == 0.02
    assert result["missing_cost_pod_ids"] == ["pod-b"]
    assert result["local_bound_before_unattributed_reserve_usd"] == pytest.approx(0.07)


def test_remote_program_and_worker_preserve_no_performance_claim():
    remote = (BASE / "runpod_w8_logikbench_conversion_remote_v2.py").read_text(encoding="utf-8")
    worker = (BASE / "runpod_w8_logikbench_conversion_worker_v2.py").read_text(encoding="utf-8")
    assert '"performance_measurement": False' in remote
    assert '"performance_claim_permitted": False' in remote
    assert '"performance_measurement": False' in worker
    assert '"performance_claim_permitted": False' in worker
    assert "TOTAL_CONVERSION_SECONDS = 600" in worker
    assert "MAX_TOTAL_BLIF_BYTES = 20 << 20" in worker
    assert "apt-get\", \"install\", \"-y\", \"--no-install-recommends\", \"yosys" in remote


def test_frozen_program_hashes_have_not_changed():
    expected = {
        "runpod_w8_logikbench_conversion_controller_v1.py": "98f4a7fc446b03aeefd1e19bdf0cb43a385c169e3adcec2c2e7d261aa73c5350",
        "http_w8_logikbench_conversion_preflight_v1.py": "a007225f8ea3392619e7856e5c4a2082cd9c2c6f5eafa91514f7735716aeab0e",
        "runpod_w8_logikbench_conversion_remote_v2.py": "8c7e7f997a9bf841e5863448c4e1992336c8f4357c953534b0767588fb2a8296",
        "http_native_scout_bootstrap_v2.py": "ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9",
        "RUNPOD-W8-LOGIKBENCH-CONVERSION-PROPOSAL-20260830.md": "e793937ef3f8e92799edd3da0df78fd74c01f2cf9a8bc434152073f4de4d366a",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((BASE / name).read_bytes()).hexdigest() == digest


def test_v3_worker_retained_byte_state_is_in_main_loop(tmp_path, monkeypatch):
    sys.path.insert(0, str(BASE))
    try:
        worker = importlib.import_module("runpod_w8_logikbench_conversion_worker_v3")
    finally:
        sys.path.remove(str(BASE))
    source = tmp_path / "source"
    clusters = []
    candidate_ids = []
    for index in range(70):
        name = f"case{index:02d}"
        cluster_id = "fixture-" + name
        relative = f"logikbench/benchmarks/group/{name}/rtl/{name}.v"
        path = source / relative
        path.parent.mkdir(parents=True)
        path.write_text(f"module {name}(input a, output y); assign y=a; endmodule\n", encoding="utf-8")
        candidate_ids.append(cluster_id)
        clusters.append({
            "cluster_id": cluster_id,
            "group": "group",
            "name": name,
            "source_set_sha256": hashlib.sha256(name.encode()).hexdigest(),
            "rtl_paths": [relative],
            "rtl_sha256": [hashlib.sha256(path.read_bytes()).hexdigest()],
        })
    admission = tmp_path / "admission.json"
    admission.write_text(json.dumps({
        "static_admitted_cluster_ids_in_frozen_order": candidate_ids,
        "clusters": clusters,
    }), encoding="utf-8")
    output = tmp_path / "output"

    monkeypatch.setattr(worker.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        stdout=b"Yosys fixture\n", stderr=b"", returncode=0
    ))
    monkeypatch.setattr(worker.platform, "platform", lambda: "test-platform")
    monkeypatch.setattr(worker.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(worker, "fixture_gate", lambda _output: {
        "fixtures": [{"semantic_equivalence": True}] * 5,
        "fixture_count": 5,
        "semantic_equivalence": True,
    })

    def fake_convert(_root, _top, _files, destination, timeout):
        destination.write_bytes(b".model fixture\n.end\n")
        return {
            "status": "converted",
            "error": None,
            "returncode": 0,
            "elapsed_seconds": 0.0,
            "stdout": "",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
            "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        }

    monkeypatch.setattr(worker, "convert", fake_convert)
    monkeypatch.setattr(sys, "argv", [
        worker.__file__, "--source-root", str(source),
        "--static-admission", str(admission), "--output", str(output),
    ])
    assert worker.main() == 0
    result = json.loads((output / "conversions.json").read_text(encoding="utf-8"))
    assert result["attempted"] == result["converted"] == 70
    assert result["rejected"] == 0
    assert result["retained_blif_bytes"] == 70 * len(b".model fixture\n.end\n")
    assert result["performance_claim_permitted"] is False
