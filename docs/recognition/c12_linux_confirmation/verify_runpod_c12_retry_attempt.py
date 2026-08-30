"""Verify the reconciled transport-success/workload-failure C12 retry."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "runpod-c12-linux-execute-004"
OUTPUT = HERE / "RUNPOD_C12_LINUX_RETRY_FINAL_VERIFICATION_20260830.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    run = load(RUN_DIR / "RUN.json")
    watchdog = load(RUN_DIR / "WATCHDOG-RESULT.json")
    validation = load(RUN_DIR / "evidence/run-output/REMOTE-VALIDATION.json")
    runtime = load(RUN_DIR / "evidence/run-output/RUNTIME.json")
    stderr = (RUN_DIR / "evidence/run-output/yosys-c7-linux-confirmation.stderr.txt").read_text(encoding="utf-8")
    if (run.get("status") != "failed" or run.get("creation_attempted") is not True
            or run.get("creation_uncertain") is not False or run.get("pod_created") is not True
            or run.get("uploaded_source_files") != 14 or run.get("automatic_replacement_queued") is not False
            or run.get("payload_attempts", [{}])[0].get("status") != "proxy HTTP 404"
            or run.get("payload_attempts", [{}, {}])[1].get("status") != "accepted"
            or run.get("remote_progress", {}).get("remote_status") != "failed"
            or run.get("cleanup", {}).get("owned_pod_absent") is not True
            or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
            or watchdog.get("status") != "controller_cleanup_verified" or watchdog.get("errors") != []
            or validation.get("status") != "failed"
            or "No module named 'cmbench.output_budget'" not in stderr
            or runtime.get("source_files") != 14 or runtime.get("runpod_pod_id") != run.get("pod_id")
            or (RUN_DIR / "evidence/run-output/yosys-c7-linux-confirmation/summary.json").exists()
            or not 0 <= run.get("estimated_compute_cost_usd", -1) <= .05):
        raise SystemExit("C12 retry did not satisfy safe workload-failure invariants")
    result = {"schema": "crse-runpod-c12-retry-final-verification/v1",
        "status": "safe_workload_failure_reconciled", "complete": True,
        "scientific_confirmation_complete": False,
        "transport_upload_complete": True, "failure_stage": "remote Python import",
        "failure_reason": "missing cmbench/output_budget.py in frozen 14-file package",
        "create_requests_this_authorization": 1, "automatic_replacement_queued": False,
        "pod_created": True, "pod_id": run["pod_id"], "uploaded_source_files": 14,
        "payload_attempts": run["payload_attempts"], "semantic_measurements": 0,
        "owned_pod_absent_verified": True, "final_inventories": {"v1": [], "v2": []},
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "elapsed_since_create_s": run["elapsed_since_create_s"],
        "run_sha256": sha(RUN_DIR / "RUN.json"), "evidence_zip_sha256": sha(RUN_DIR / "evidence.zip"),
        "watchdog_sha256": sha(RUN_DIR / "WATCHDOG-RESULT.json")}
    OUTPUT.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
