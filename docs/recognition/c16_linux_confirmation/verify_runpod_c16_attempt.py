"""Verify the safely reconciled single-pod C16 Linux attempt."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "runpod-c16-linux-execute-001"
MANIFEST = HERE / "c16_linux_upload_manifest.json"
AUTHORIZATION = HERE / "RUNPOD_C16_EXACT_PAYLOAD_AUTHORIZED_2026_08_31.json"
OUTPUT = HERE / "RUNPOD_C16_LINUX_FINAL_VERIFICATION_20260831.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    run = load(RUN_DIR / "RUN.json")
    watchdog = load(RUN_DIR / "WATCHDOG-RESULT.json")
    resources = load(RUN_DIR / "POD-RESOURCE-CHECK.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    command = load(
        RUN_DIR / "evidence/run-output/yosys-c7-linux-confirmation.json"
    )
    remote_validation = load(
        RUN_DIR / "evidence/run-output/REMOTE-VALIDATION.json"
    )
    manifest = load(MANIFEST)
    authorization = load(AUTHORIZATION)
    expected_import_error = "ModuleNotFoundError: No module named 'cm_expr_serde'"

    if (
        run.get("status") != "failed"
        or run.get("error_type") != "FileNotFoundError"
        or run.get("creation_attempted") is not True
        or run.get("creation_uncertain") is not False
        or run.get("pod_created") is not True
        or run.get("uploaded_source_files") != 18
        or run.get("automatic_replacement_queued") is not False
        or run.get("payload_attempts") != [
            {
                "attempt": 1,
                "checked_utc": run["payload_attempts"][0].get("checked_utc"),
                "status": "accepted",
            }
        ]
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
        or len(run.get("cleanup", {}).get("attempts", [])) != 1
        or run["cleanup"]["attempts"][0].get("http_status") != 204
        or watchdog
        != {
            "errors": [],
            "finished_utc": watchdog.get("finished_utc"),
            "status": "controller_cleanup_verified",
        }
        or run.get("actual_resources", {}).get("rate_usd_per_hour") != 0.06
        or run.get("actual_resources", {}).get("ram_gb") != 4.0
        or run.get("actual_resources", {}).get("vcpu_count") != 2
        or run.get("actual_resources", {}).get("container_disk_gb") != 12
        or run.get("actual_resources", {}).get("pod_volume_gb") != 0
        or run.get("actual_resources", {}).get("ports") != ["8080/http"]
        or run.get("actual_resources", {}).get("cloud_evidence") != ["SECURE"]
        or resources.get("network_volume_present") is not False
        or freeze.get("source_files") != 18
        or freeze.get("source_bytes") != 423661
        or freeze.get("manifest_sha256") != sha(MANIFEST)
        or freeze.get("authorization_sha256") != sha(AUTHORIZATION)
        or freeze.get("credentials_recorded_or_uploaded") is not False
        or manifest.get("file_count") != 18
        or manifest.get("bytes") != 423661
        or authorization.get("authorized") is not True
        or authorization.get("one_create") is not True
        or authorization.get("no_replacement") is not True
        or authorization.get("controller_total_ceiling_usd") != 0.05
        or command.get("returncode") != 1
        or expected_import_error not in command.get("stderr_tail", "")
        or remote_validation.get("status") != "failed"
        or "summary.json" not in remote_validation.get("validation_error", "")
        or not (RUN_DIR / "evidence.zip").is_file()
        or not (RUN_DIR / "container.log").is_file()
        or (RUN_DIR / "evidence/run-output/c16-linux-confirmation/summary.json").exists()
        or not 0 <= run.get("estimated_compute_cost_usd", -1) <= 0.05
    ):
        raise SystemExit("C16 RunPod attempt did not satisfy safe-failure invariants")

    result = {
        "schema": "crse-runpod-c16-final-verification/v1",
        "status": "safe_failure_reconciled",
        "complete": True,
        "scientific_confirmation_complete": False,
        "failure_stage": "remote workload import bootstrap",
        "failure_type": "ModuleNotFoundError",
        "failure_detail": "cm_expr_serde was not on sys.path in the remote launcher",
        "create_requests_this_authorization": 1,
        "automatic_replacement_queued": False,
        "pod_created": True,
        "pod_id": run["pod_id"],
        "uploaded_source_files": 18,
        "uploaded_source_bytes": 423661,
        "retrieved_evidence_bytes": (RUN_DIR / "evidence.zip").stat().st_size,
        "semantic_measurements": 0,
        "owned_pod_absent_verified": True,
        "final_inventories": {"v1": [], "v2": []},
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "elapsed_since_create_s": run["elapsed_since_create_s"],
        "run_sha256": sha(RUN_DIR / "RUN.json"),
        "watchdog_sha256": sha(RUN_DIR / "WATCHDOG-RESULT.json"),
        "transport_freeze_sha256": sha(RUN_DIR / "TRANSPORT-FREEZE.json"),
        "evidence_zip_sha256": sha(RUN_DIR / "evidence.zip"),
        "manifest_sha256": sha(MANIFEST),
        "authorization_sha256": sha(AUTHORIZATION),
    }
    OUTPUT.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
