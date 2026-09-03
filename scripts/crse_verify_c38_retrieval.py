"""Replay retrieved C38 evidence locally and record bounded transport verification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c38_linux_confirmation"
RUN_DIR = HERE / "runpod-c38-linux-execute-002"
RUN_NAME = "c38-c37-native-linux-gcc-20260903-001"
RETRIEVED_ROOT = RUN_DIR / "evidence/run-output"
REMOTE_RUN = RETRIEVED_ROOT / RUN_NAME
MANIFEST = HERE / "c38_linux_upload_manifest.json"
AUTHORIZATION = HERE / "RUNPOD_C38_TRANSPORT_RETRY_001_AUTHORIZED_2026_09_03.json"
RECONCILIATION = HERE / "C38_INITIAL_NO_CREATE_RECONCILIATION_20260903.json"
OUTPUT = HERE / "RUNPOD_C38_FINAL_VERIFICATION_20260903.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def zero_mismatches(document: dict[str, Any]) -> bool:
    return all(
        value == 0
        for key, value in document.items()
        if key.endswith("_mismatches")
    )


def replay_verifiers(manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="cm-c38-post-retrieval-") as temporary:
        package = Path(temporary) / "package"
        for row in manifest["files"]:
            source = ROOT / row["source"]
            if (
                not source.is_file()
                or source.stat().st_size != row["bytes"]
                or sha256(source) != row["sha256"]
            ):
                raise RuntimeError(f"C38 package source drifted: {row['source']}")
            target = package / row["target"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        shutil.copytree(RETRIEVED_ROOT, package / "run-output")
        replay = package / "run-output" / RUN_NAME
        expected_c37 = (replay / "independent_verification.json").read_bytes()
        expected_c38 = (replay / "c38_independent_verification.json").read_bytes()
        (replay / "independent_verification.json").unlink()
        (replay / "c38_independent_verification.json").unlink()
        environment = os.environ.copy()
        environment.update(
            {
                "OMP_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        commands = (
            (
                package / "scripts/crse_native_exact_confirmation_verify.py",
                "independent_verification.json",
            ),
            (
                package / "scripts/crse_c38_linux_replication_verify.py",
                "c38_independent_verification.json",
            ),
        )
        replayed: list[dict[str, Any]] = []
        for script, output_name in commands:
            completed = subprocess.run(
                [sys.executable, "-B", str(script), "--run-dir", str(replay)],
                cwd=package,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=240,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"post-retrieval verifier failed: {script.name}: "
                    f"{completed.stderr[-1000:]}"
                )
            replayed.append(load(replay / output_name))
        if (
            (replay / "independent_verification.json").read_bytes() != expected_c37
            or (replay / "c38_independent_verification.json").read_bytes()
            != expected_c38
        ):
            raise RuntimeError("post-retrieval verification is not byte-identical")
        return replayed[0], replayed[1]


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C38 final verification")
    run = load(RUN_DIR / "RUN.json")
    runtime = load(RETRIEVED_ROOT / "RUNTIME.json")
    result = load(REMOTE_RUN / "results.json")
    c37_verification = load(REMOTE_RUN / "independent_verification.json")
    c38_verification = load(REMOTE_RUN / "c38_independent_verification.json")
    watchdog = load(RUN_DIR / "WATCHDOG-RESULT.json")
    manifest = load(MANIFEST)
    authorization = load(AUTHORIZATION)
    reconciliation = load(RECONCILIATION)
    cleanup = run.get("cleanup", {})
    payload_attempts = run.get("payload_attempts", [])
    if (
        run.get("status") != "complete"
        or run.get("creation_attempted") is not True
        or run.get("creation_uncertain") is not False
        or run.get("pod_created") is not True
        or run.get("uploaded_source_files") != 44
        or run.get("automatic_replacement_queued") is not False
        or run.get("health_checks_before_upload") != 2
        or len(payload_attempts) != 2
        or payload_attempts[0].get("status") != "proxy HTTP 404"
        or payload_attempts[1].get("status") != "accepted"
        or not (0 < run.get("estimated_compute_cost_usd", 0) <= 0.05)
        or cleanup.get("owned_pod_absent") is not True
        or any(cleanup.get("inventories", {}).values())
        or watchdog.get("status") != "controller_cleanup_verified"
        or watchdog.get("errors") != []
        or runtime.get("source_files") != 44
        or runtime.get("runpod_pod_id") != run.get("pod_id")
        or manifest.get("file_count") != 44
        or manifest.get("bytes") != 1_797_840
        or authorization.get("authorized") is not True
        or authorization.get("one_create") is not True
        or authorization.get("no_replacement") is not True
        or run.get("authorization_record_sha256") != sha256(AUTHORIZATION)
        or reconciliation.get("authorized_create_consumed") is not False
        or reconciliation.get("owned_pod_absent") is not True
        or c37_verification.get("status") != "verified"
        or c38_verification.get("status") != "verified"
        or not zero_mismatches(c37_verification)
        or not zero_mismatches(c38_verification)
        or c37_verification.get("raw_sessions_checked") != 954
        or c37_verification.get("single_root_queries_checked") != 44_928
        or c37_verification.get("multi_root_output_queries_checked") != 48_384
        or c38_verification.get("raw_sessions_checked") != 954
        or c38_verification.get("single_root_queries_checked") != 44_928
        or c38_verification.get("multi_root_output_queries_checked") != 48_384
        or result.get("decision", {}).get("training") is not False
        or result.get("decision", {}).get("policy_refit") is not False
        or result.get("decision", {}).get("gate_refit") is not False
        or result.get("decision", {}).get("production_promotion") is not False
    ):
        raise RuntimeError("retrieved C38 transport or scientific evidence is incomplete")

    replayed_c37, replayed_c38 = replay_verifiers(manifest)
    if replayed_c37 != c37_verification or replayed_c38 != c38_verification:
        raise RuntimeError("post-retrieval replay differs from on-pod verification")

    single = result["single_root"]
    multi = result["multi_root"]
    case_speedups = single["case_median_speedups_over_python_r2"]
    slowest_case = min(case_speedups, key=case_speedups.get)
    verification = {
        "schema": "crse-runpod-c38-final-verification/v1",
        "status": "pass",
        "scientific_replication_complete": True,
        "exactness_verified": True,
        "post_retrieval_replay": "pass",
        "post_retrieval_verification_byte_identical": True,
        "one_create_request": True,
        "replacement_attempt": False,
        "pod_created": True,
        "owned_pod_absent_verified": True,
        "source_files_uploaded": 44,
        "source_bytes": 1_797_840,
        "retrieved_evidence_bytes": run["evidence"]["bytes"],
        "result_cap_bytes": 24 << 20,
        "pod_id": run["pod_id"],
        "cpu_flavor": run["actual_resources"]["cpu_flavor"],
        "cpu_model": runtime["cpu_model"],
        "compiler": c38_verification["compiler"],
        "quoted_rate_usd_per_hour": run["quoted_rate_usd_per_hour"],
        "elapsed_since_create_s": run["elapsed_since_create_s"],
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "raw_sessions": 954,
        "single_root_queries_checked": 44_928,
        "multi_root_output_queries_checked": 48_384,
        "semantic_or_artifact_mismatches": 0,
        "single_root_aggregate_speedup": single["native_speedup_over_python_r2"],
        "single_root_minimum_case_speedup": single[
            "minimum_case_speedup_over_python_r2"
        ],
        "single_root_slowest_case": slowest_case,
        "single_root_minimum_width_speedup": single[
            "minimum_width_speedup_over_python_r2"
        ],
        "multi_root_aggregate_speedup": multi["union_speedup_over_separate"],
        "multi_root_minimum_workload_speedup": multi["minimum_workload_speedup"],
        "all_predeclared_performance_gates_passed": result["decision"][
            "all_predeclared_gates_passed"
        ],
        "failed_performance_gates_retained": [
            key for key, passed in single["gates"].items() if not passed
        ],
        "run_sha256": sha256(RUN_DIR / "RUN.json"),
        "results_sha256": sha256(REMOTE_RUN / "results.json"),
        "measurements_sha256": sha256(REMOTE_RUN / "raw_measurements.jsonl"),
        "on_pod_c37_verification_sha256": sha256(
            REMOTE_RUN / "independent_verification.json"
        ),
        "on_pod_c38_verification_sha256": sha256(
            REMOTE_RUN / "c38_independent_verification.json"
        ),
        "training": False,
        "policy_refit": False,
        "gate_refit": False,
        "shadow_promotion": False,
        "production_promotion": False,
    }
    with OUTPUT.open("xb") as stream:
        stream.write(
            json.dumps(verification, indent=2, sort_keys=True, allow_nan=False).encode(
                "utf-8"
            )
            + b"\n"
        )
    print(
        json.dumps(
            {
                "status": verification["status"],
                "post_retrieval_replay": verification["post_retrieval_replay"],
                "byte_identical": verification[
                    "post_retrieval_verification_byte_identical"
                ],
                "exactness_verified": verification["exactness_verified"],
                "all_performance_gates": verification[
                    "all_predeclared_performance_gates_passed"
                ],
                "owned_pod_absent": verification["owned_pod_absent_verified"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
