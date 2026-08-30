"""Verify the safely reconciled single-pod C12 transport attempt."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "runpod-c12-linux-execute-001"
OUTPUT = HERE / "RUNPOD_C12_LINUX_ATTEMPT_FINAL_VERIFICATION_20260830.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    run = load(RUN_DIR / "RUN.json")
    watchdog = load(RUN_DIR / "WATCHDOG-RESULT.json")
    resources = load(RUN_DIR / "POD-RESOURCE-CHECK.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    manifest = load(HERE / "c12_linux_upload_manifest.json")
    authorization = load(HERE / "RUNPOD_C12_LINUX_AUTHORIZED_2026_08_30.json")
    if (run.get("status") != "failed" or run.get("error") != "proxy HTTP 404"
            or run.get("creation_attempted") is not True or run.get("creation_uncertain") is not False
            or run.get("pod_created") is not True or run.get("uploaded_source_files") != 0
            or run.get("automatic_replacement_queued") is not False
            or run.get("cleanup", {}).get("owned_pod_absent") is not True
            or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
            or len(run.get("cleanup", {}).get("attempts", [])) != 1
            or run["cleanup"]["attempts"][0].get("http_status") != 204
            or watchdog != {"errors": [], "finished_utc": watchdog.get("finished_utc"),
                             "status": "controller_cleanup_verified"}
            or run.get("actual_resources", {}).get("rate_usd_per_hour") != 0.06
            or run.get("actual_resources", {}).get("ram_gb") != 4.0
            or run.get("actual_resources", {}).get("vcpu_count") != 2
            or run.get("actual_resources", {}).get("container_disk_gb") != 12
            or run.get("actual_resources", {}).get("pod_volume_gb") != 0
            or run.get("actual_resources", {}).get("ports") != ["8080/http"]
            or resources.get("network_volume_present") is not False
            or freeze.get("source_files") != 14 or freeze.get("source_bytes") != 355934
            or freeze.get("manifest_sha256") != sha(HERE / "c12_linux_upload_manifest.json")
            or freeze.get("authorization_sha256") != sha(HERE / "RUNPOD_C12_LINUX_AUTHORIZED_2026_08_30.json")
            or manifest.get("file_count") != 14 or manifest.get("bytes") != 355934
            or authorization.get("one_create") is not True or authorization.get("no_replacement") is not True
            or (RUN_DIR / "evidence.zip").exists() or (RUN_DIR / "container.log").exists()
            or not 0 <= run.get("estimated_compute_cost_usd", -1) <= .05):
        raise SystemExit("C12 Runpod attempt did not satisfy safe-failure invariants")
    result = {"schema": "crse-runpod-c12-attempt-final-verification/v1",
        "status": "safe_failure_reconciled", "complete": True,
        "scientific_confirmation_complete": False,
        "failure_stage": "POST /payload after successful GET /health",
        "provider_error": "proxy HTTP 404", "create_requests_this_authorization": 1,
        "automatic_replacement_queued": False, "pod_created": True,
        "pod_id": run["pod_id"], "uploaded_source_files": 0,
        "retrieved_result_bytes": 0, "semantic_measurements": 0,
        "owned_pod_absent_verified": True, "final_inventories": {"v1": [], "v2": []},
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "elapsed_since_create_s": run["elapsed_since_create_s"],
        "run_sha256": sha(RUN_DIR / "RUN.json"),
        "watchdog_sha256": sha(RUN_DIR / "WATCHDOG-RESULT.json"),
        "transport_freeze_sha256": sha(RUN_DIR / "TRANSPORT-FREEZE.json"),
        "manifest_sha256": sha(HERE / "c12_linux_upload_manifest.json"),
        "authorization_sha256": sha(HERE / "RUNPOD_C12_LINUX_AUTHORIZED_2026_08_30.json")}
    OUTPUT.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
