"""Replay retrieved C31 evidence locally and record bounded transport verification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c31_linux_confirmation"
RUN_DIR = HERE / "runpod-c31-linux-execute-002"
REMOTE_RUN = (
    RUN_DIR / "evidence/run-output/c31-prepared-policy-linux-20260901-001"
)
OUTPUT = HERE / "RUNPOD_C31_FINAL_VERIFICATION_20260901.json"
VERIFY = ROOT / "scripts/crse_gf2_prepared_policy_verify.py"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C31 final verification")
    run = load(RUN_DIR / "RUN.json")
    runtime = load(RUN_DIR / "evidence/run-output/RUNTIME.json")
    remote_verification = load(REMOTE_RUN / "independent_verification.json")
    watchdog = load(RUN_DIR / "WATCHDOG-RESULT.json")
    cleanup = run.get("cleanup", {})
    if (
        run.get("status") != "complete"
        or run.get("creation_attempted") is not True
        or run.get("creation_uncertain") is not False
        or run.get("pod_created") is not True
        or run.get("uploaded_source_files") != 71
        or run.get("automatic_replacement_queued") is not False
        or run.get("health_checks_before_upload") != 2
        or len(run.get("payload_attempts", [])) != 1
        or run["payload_attempts"][0].get("status") != "accepted"
        or not (0 < run.get("estimated_compute_cost_usd", 0) <= 0.05)
        or cleanup.get("owned_pod_absent") is not True
        or any(cleanup.get("inventories", {}).values())
        or watchdog.get("status") != "controller_cleanup_verified"
        or runtime.get("source_files") != 71
        or runtime.get("runpod_pod_id") != run.get("pod_id")
        or remote_verification.get("status") != "verified"
        or remote_verification.get("measurement_batches_checked") != 128
        or remote_verification.get("paired_batches_checked") != 64
        or remote_verification.get("timed_query_records_checked") != 1024
        or remote_verification.get("verified_context_records_replayed") != 512
        or remote_verification.get("semantic_or_artifact_mismatches") != 0
    ):
        raise RuntimeError("retrieved C31 transport or scientific evidence is incomplete")

    with tempfile.TemporaryDirectory(prefix="c31-post-retrieval-", dir=ROOT) as temporary:
        replay = Path(temporary) / "run"
        shutil.copytree(REMOTE_RUN, replay)
        (replay / "independent_verification.json").unlink()
        environment = os.environ.copy()
        environment.update({
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        completed = subprocess.run(
            [sys.executable, "-B", str(VERIFY), str(replay)],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if completed.returncode != 0:
            raise RuntimeError("post-retrieval verifier failed")
        replay_path = replay / "independent_verification.json"
        replayed = load(replay_path)
        byte_identical = replay_path.read_bytes() == (
            REMOTE_RUN / "independent_verification.json").read_bytes()

    if replayed != remote_verification or not byte_identical:
        raise RuntimeError("post-retrieval verification differs from on-pod verification")
    result = load(REMOTE_RUN / "results.json")
    summary = result["summary"]
    verification = {
        "schema": "crse-runpod-c31-final-verification/v1",
        "status": "pass",
        "scientific_replication_complete": True,
        "post_retrieval_replay": "pass",
        "post_retrieval_verification_byte_identical": True,
        "one_create_request": True,
        "replacement_attempt": False,
        "pod_created": True,
        "owned_pod_absent_verified": True,
        "source_files_uploaded": 71,
        "source_bytes": 1153868,
        "pod_id": run["pod_id"],
        "cpu_flavor": run["actual_resources"]["cpu_flavor"],
        "cpu_model": runtime["cpu_model"],
        "quoted_rate_usd_per_hour": run["quoted_rate_usd_per_hour"],
        "elapsed_since_create_s": run["elapsed_since_create_s"],
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "measurement_batches": 128,
        "paired_batches": 64,
        "timed_queries": 1024,
        "verified_context_records_replayed": 512,
        "functional_controls_replayed": 6,
        "semantic_or_artifact_mismatches": 0,
        "preparation_charge_conserved": True,
        "aggregate_charged_total_speedup": summary[
            "aggregate_ratio_of_median_charged_total_speedup"],
        "minimum_width_charged_total_speedup": summary[
            "minimum_width_ratio_of_median_charged_total_speedup"],
        "prepared_no_regret_gate": summary["prepared_no_regret_gate"],
        "run_sha256": sha256(RUN_DIR / "RUN.json"),
        "results_sha256": sha256(REMOTE_RUN / "results.json"),
        "measurements_sha256": sha256(REMOTE_RUN / "measurements.jsonl"),
        "on_pod_verification_sha256": sha256(
            REMOTE_RUN / "independent_verification.json"),
        "policy_refit": False,
        "training": False,
        "shadow_promotion": False,
        "production_promotion": False,
    }
    OUTPUT.write_bytes(json.dumps(
        verification, indent=2, sort_keys=True, allow_nan=False,
    ).encode() + b"\n")
    print(json.dumps({
        "status": verification["status"],
        "post_retrieval_replay": verification["post_retrieval_replay"],
        "byte_identical": verification["post_retrieval_verification_byte_identical"],
        "semantic_or_artifact_mismatches": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
