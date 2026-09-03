from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


BASE = Path(
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/continuation-20260829-125214"
).resolve()
WORKER_PATH = BASE / "runpod_w8_logikbench_semantic_worker_v1.py"


def load_worker():
    spec = importlib.util.spec_from_file_location("w8_semantic_worker_under_test", WORKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_selection_keys_and_round_robin_are_deterministic():
    worker = load_worker()
    rows = []
    for index in range(42):
        rows.append({
            "cluster_id": f"cluster-{index:02d}",
            "root": f"root-{index:02d}",
            "blif_sha256": digest(f"blif-{index}".encode()),
            "group": ("arithmetic", "basic", "blocks")[index % 3],
            "k": (4, 8, 12, 16)[index % 4],
            "source_nodes": (32, 128, 1024)[index % 3],
        })
    first = [row["cluster_id"] for row in worker.select_primary([dict(row) for row in rows])]
    second = [row["cluster_id"] for row in worker.select_primary([dict(row) for row in reversed(rows)])]
    assert first == second
    assert len(first) == len(set(first)) == 30


def test_one_case_refuses_identity_mismatch_without_importing_parser(tmp_path, capsys):
    worker = load_worker()
    source = tmp_path / "case.blif"
    source.write_bytes(b".model x\n.end\n")
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({
        "cluster_id": "cluster-x",
        "path": str(source),
        "blif_sha256": "0" * 64,
    }), encoding="utf-8")
    assert worker.one_case(payload) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "rejected"
    assert result["error"] == "case_exception"
    assert result["performance_measurement"] is False
    assert result["performance_claim_permitted"] is False


def test_fake_parent_run_freezes_exactly_thirty_unique_cases(tmp_path, monkeypatch, capsys):
    worker = load_worker()
    conversion_root = tmp_path / "conversion"
    conversion_root.mkdir()
    converted = []
    admission_rows = []
    acquisition_rows = []
    for index in range(64):
        cluster_id = f"logikbench-{('arithmetic', 'basic', 'blocks')[index % 3]}-case{index:02d}"
        blif_sha = digest(f"converted-{index}".encode())
        converted.append({"cluster_id": cluster_id, "status": "converted", "sha256": blif_sha})
        group = ("arithmetic", "basic", "blocks")[index % 3]
        name = f"case{index:02d}"
        admission_rows.append({
            "cluster_id": cluster_id,
            "group": group,
            "name": name,
            "source_set_sha256": digest(f"source-set-{index}".encode()),
            "tree_sha256": digest(f"tree-{index}".encode()),
            "rtl_paths": [f"rtl/{name}.v"],
            "rtl_sha256": [digest(f"rtl-{index}".encode())],
            "license_ids": ["MIT"],
            "license_paths": ["LICENSE"],
        })
        acquisition_rows.append({"cluster_id": cluster_id, "ai_provenance_present": False})
    (conversion_root / "conversions.json").write_text(json.dumps({
        "attempted": 70,
        "converted": 64,
        "rows": converted + [
            {"cluster_id": f"rejected-{index}", "status": "rejected"} for index in range(6)
        ],
    }), encoding="utf-8")
    admission = tmp_path / "admission.json"
    admission.write_text(json.dumps({"clusters": admission_rows}), encoding="utf-8")
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_text(json.dumps({
        "repository": "https://example.invalid/repo.git",
        "commit": "a" * 40,
        "clusters": acquisition_rows,
    }), encoding="utf-8")

    def fake_run(command, **_kwargs):
        payload = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
        index = int(payload["cluster_id"].rsplit("case", 1)[1])
        semantic_index = index // 2
        k = (4, 8, 12, 16)[semantic_index % 4]
        root = f"root-{index:02d}"
        row = {
            "schema": "cm-comparative-w8-semantic-case/v1",
            "cluster_id": payload["cluster_id"],
            "blif_sha256": payload["blif_sha256"],
            "status": "eligible",
            "performance_measurement": False,
            "performance_claim_permitted": False,
            "model": "fixture",
            "inputs": k,
            "outputs": 1,
            "eligible_output_count": 1,
            "root": root,
            "root_selection_key": digest(("cm-w8-root-v1\0" + payload["cluster_id"] + "\0" + root).encode()),
            "support": [f"x{i}" for i in range(k)],
            "k": k,
            "source_nodes": (32, 128, 1024)[semantic_index % 3],
            "source_edges": 10,
            "depth": 3,
            "local_fanin": 2,
            "local_cubes": 1,
            "local_literals": 2,
            "truth_sha256": digest(f"truth-{semantic_index}".encode()),
            "truth_ones": 4,
            "truth_density_ppm": 500000,
            "oracle_sha256": digest(f"oracle-{semantic_index}".encode()),
            "translation_compatible": True,
        }
        return SimpleNamespace(stdout=json.dumps(row).encode(), stderr=b"", returncode=0)

    monkeypatch.setattr(worker.subprocess, "run", fake_run)
    output = tmp_path / "output"
    monkeypatch.setattr("sys.argv", [
        str(WORKER_PATH),
        "--conversion-root", str(conversion_root),
        "--admission", str(admission),
        "--acquisition", str(acquisition),
        "--output", str(output),
    ])
    assert worker.main() == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "converted_inputs": 64,
        "eligible": 64,
        "performance_measurement": False,
        "primary_selected": 30,
        "semantic_duplicates": 32,
        "terminal_rows": 64,
        "unique_eligible": 32,
    }
    scout = json.loads((output / "semantic-scout.json").read_text(encoding="utf-8"))
    draft = json.loads((output / "confirmation-draft.json").read_text(encoding="utf-8"))
    oracle = json.loads((output / "oracle-package.json").read_text(encoding="utf-8"))
    assert scout["primary_selected"] == draft["case_count"] == len(oracle["rows"]) == 30
    assert len({case["cluster_id"] for case in draft["cases"]}) == 30
    assert all(case["source"]["path"].startswith("sources/logikbench-") for case in draft["cases"])
    assert draft["performance_claim_permitted"] is False


def test_worker_declares_bounded_no_timing_contract():
    source = WORKER_PATH.read_text(encoding="utf-8")
    assert "PER_CASE_SECONDS = 45" in source
    assert "TOTAL_SECONDS = 720" in source
    assert "PRIMARY_CASES = 30" in source
    assert '"performance_measurement": False' in source
    assert '"performance_claim_permitted": False' in source


def test_historical_upload_package_refuses_live_source_drift():
    spec = importlib.util.spec_from_file_location(
        "w8_semantic_upload_verifier",
        BASE / "verify_w8_logikbench_semantic_upload_v1.py",
    )
    verifier = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(verifier)
    with pytest.raises(RuntimeError, match="source changed: bitset_backend.py"):
        verifier.verify()


def test_remote_wrapper_is_dependency_locked_and_semantic_only():
    source = (BASE / "runpod_w8_logikbench_semantic_remote_v1.py").read_text(encoding="utf-8")
    assert '"--require-hashes", "--only-binary=:all:"' in source
    assert '"tests/test_blif_recognition.py"' in source
    assert 'name="semantic-root-oracle-scout"' in source
    assert '"performance_measurement": False' in source
    assert '"performance_claim_permitted": False' in source
    assert "apt-get" not in source
    assert "yosys" not in source.lower()


def test_controller_preserves_one_create_zero_volume_and_exact_payload():
    source = (BASE / "runpod_w8_logikbench_semantic_controller_v1.py").read_text(encoding="utf-8")
    assert '"one_create": True' in source
    assert '"no_replacement_within_this_controller": True' in source
    assert '"containerDiskInGb": 12, "volumeInGb": 0' in source
    assert '"network_volume": False' in source
    assert '"source_files": 82' in source
    assert '"converted_clusters": 64' in source
    assert '"required_primary_cases": 30' in source
    assert '"semantic_root_oracle_only": True' in source
    assert "142f6d5e6ad4fe68ef3f64e6a74a0236fa786ae9e990c27ea1ed8c533faa24aa" in source
    assert "be42ee3517167e83168b138e8607eeebf5c6cc66d6660167daa2b38b425277b3" not in source


def test_manifest_excludes_secret_like_targets():
    manifest = json.loads((
        BASE / "RUNPOD-W8-LOGIKBENCH-SEMANTIC-UPLOAD-MANIFEST-V1-20260830.json"
    ).read_text(encoding="utf-8"))
    targets = [row["target"].lower() for row in manifest["files"]]
    assert len(targets) == len(set(targets)) == 82
    assert sum(target.startswith("w8-conversion/converted/") for target in targets) == 64
    assert all(".env" not in target for target in targets)
    assert all(".git" not in target for target in targets)
    assert all(not target.endswith((".pem", ".key", ".db", ".sqlite")) for target in targets)


def test_retry_controller_uses_same_payload_and_smaller_bounded_chunks():
    source = (BASE / "runpod_w8_logikbench_semantic_controller_v2.py").read_text(encoding="utf-8")
    assert "CHUNK_BYTES = 64 << 10" in source
    assert 'OUT = HERE / "w8-logikbench-semantic-v2-001"' in source
    assert '"retry_after_transport_failure": True' in source
    assert '"prior_failed_uploaded_source_files": 0' in source
    assert '"prior_failed_cleanup_verified": True' in source
    assert '"volumeInGb": 0' in source
    assert "142f6d5e6ad4fe68ef3f64e6a74a0236fa786ae9e990c27ea1ed8c533faa24aa" in source
    assert '"event": "chunk-acknowledged"' in source
    assert '"event": "payload-validated"' in source


def test_v3_retry_preserves_payload_and_adds_compatible_cpu_fallbacks():
    controller = (BASE / "runpod_w8_logikbench_semantic_controller_v3.py").read_text(encoding="utf-8")
    preflight = (BASE / "http_w8_logikbench_semantic_preflight_v2.py").read_text(encoding="utf-8")
    assert 'OUT = HERE / "w8-logikbench-semantic-v3-001"' in controller
    assert '"prior_no_create_run": "w8-logikbench-semantic-v2-001"' in controller
    assert '"prior_no_create_verified": True' in controller
    assert "CHUNK_BYTES = 64 << 10" in controller
    assert "142f6d5e6ad4fe68ef3f64e6a74a0236fa786ae9e990c27ea1ed8c533faa24aa" in controller
    assert 'FLAVORS = ("cpu3c", "cpu3g", "cpu3m", "cpu5c", "cpu5g", "cpu5m")' in preflight
    assert "ThreadPoolExecutor(max_workers=6)" in preflight
    assert "RATE_CAP = 0.25" in preflight
