"""Independently verify the successful single-port C7 Runpod confirmation."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTROLLER_PATH = HERE / "runpod_c7_linux_single_port_controller.py"
spec = importlib.util.spec_from_file_location("c7_single_port_controller", CONTROLLER_PATH)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
RUN_DIR = controller.OUT
ROOT = controller.PROJECT_ROOT


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    run = load(RUN_DIR / "RUN.json")
    identity = load(RUN_DIR / "POD-IDENTITY.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    watchdog = load(RUN_DIR / "WATCHDOG-RESULT.json")
    controller_release = load(RUN_DIR / "HOST-AWAKE-RELEASED-http-controller.json")
    watchdog_release = load(RUN_DIR / "HOST-AWAKE-RELEASED-http-watchdog.json")
    pod_id = identity["pod_id"]
    evidence_root = RUN_DIR / "evidence" / "run-output"
    study = evidence_root / "yosys-c7-linux-confirmation"
    summary_path = study / "summary.json"
    measurements_path = study / "measurements.jsonl"
    per_case_path = study / "per_case.json"
    summary = load(summary_path)
    artifact_manifest = load(study / "manifest.json")
    measurements = [json.loads(line) for line in measurements_path.read_text(encoding="utf-8").splitlines()]
    per_case = load(per_case_path)
    runtime = load(evidence_root / "RUNTIME.json")
    dependencies = load(evidence_root / "DEPENDENCIES.json")
    remote_validation = load(evidence_root / "REMOTE-VALIDATION.json")
    dataset = load(ROOT / "docs" / "recognition" / "runs" /
                   "yosys-source-anf-confirmation-20260830-002" / "dataset.json")

    with controller.preflight.session() as client:
        inventories = controller.inventories(client)
        details = {}
        for name, endpoint in (("v1", controller.preflight.V1), ("v2", controller.preflight.V2)):
            response = client.get(endpoint + "/pods/" + pod_id, timeout=10, allow_redirects=False)
            details[name] = response.status_code

    methods = {"set_source_anf", "packed_source_anf", "cached_packed_cold",
               "cached_packed_warm", "bitset_truth_vector_anf", "numpy_truth_vector_anf"}
    expected_keys = {(repetition, method, row["split"], row["case_id"])
                     for repetition in range(9) for method in methods for row in dataset}
    observed_keys = {(row.get("repetition"), row.get("method"), row.get("split"), row.get("case_id"))
                     for row in measurements}
    measured_hashes = {
        "measurements.jsonl": sha(measurements_path),
        "per_case.json": sha(per_case_path),
        "summary.json": sha(summary_path),
    }
    artifact_hashes_match = artifact_manifest.get("files_sha256") == measured_hashes
    frozen_hashes_match = (
        freeze.get("controller_sha256") == sha(CONTROLLER_PATH)
        and freeze.get("authorization_sha256") == sha(controller.AUTHORIZATION_PATH)
        and freeze.get("proposal_sha256") == sha(controller.PROPOSAL_PATH)
        and freeze.get("manifest_sha256") == sha(controller.MANIFEST_PATH)
        and freeze.get("bootstrap_sha256") == sha(controller.BOOTSTRAP_PATH)
        and freeze.get("source_files") == 14
        and freeze.get("source_bytes") == 322080
    )
    elapsed = float(run["elapsed_since_create_s"])
    actual_rate = float(run["actual_resources"]["rate_usd_per_hour"])
    projected_cost = float(run["actual_resources"]["projected_10_min_cost_usd"])
    estimated_cost = float(run["estimated_compute_cost_usd"])
    lifecycle_valid = (
        run.get("status") == "complete"
        and run.get("creation_attempted") is True
        and run.get("creation_http_status") == 201
        and run.get("creation_uncertain") is False
        and run.get("pod_created") is True
        and run.get("pod_id") == pod_id
        and run.get("uploaded_source_files") == 14
        and run.get("cleanup", {}).get("owned_pod_absent") is True
        and not any(run.get("cleanup", {}).get("inventories", {}).values())
        and watchdog.get("status") == "controller_cleanup_verified"
        and controller_release.get("released") is True
        and watchdog_release.get("released") is True
        and elapsed < controller.CLEANUP_AT
    )
    resources_valid = (
        run.get("actual_resources", {}).get("vcpu_count") == 2
        and run.get("actual_resources", {}).get("ram_gb", 0) >= 4
        and run.get("actual_resources", {}).get("container_disk_gb") == 12
        and run.get("actual_resources", {}).get("pod_volume_gb") == 0
        and run.get("actual_resources", {}).get("ports") == ["8080/http"]
        and run.get("actual_resources", {}).get("cloud_evidence") == ["SECURE"]
        and run.get("actual_resources", {}).get("image") == controller.base.IMAGE
        and math.isfinite(actual_rate) and 0 < actual_rate <= controller.RATE_CAP
        and projected_cost <= controller.CAMPAIGN_CAP and estimated_cost <= controller.CAMPAIGN_CAP
    )
    scientific_valid = (
        summary.get("schema") == "crse-yosys-source-anf-linux-confirmation/v1"
        and summary.get("status") == "complete"
        and summary.get("semantic_mismatches") == 0
        and summary.get("criteria", {}).get("exact") is True
        and summary.get("config", {}).get("cases") == 40
        and summary.get("config", {}).get("repetitions") == 9
        and set(summary.get("config", {}).get("methods", [])) == methods
        and summary.get("input") == {"dataset_sha256": "3ca1ae22fd79bac68c37e78fe497701cb100713b0077130e5263cb1f66145864",
                                    "training_use": False,
                                    "source_commit": "52ff6fa991f2ab509618d8aaad02f307aac78848"}
        and len(measurements) == 2160 and observed_keys == expected_keys
        and len(per_case) == 240
        and all(row.get("schema") == "crse-yosys-source-anf-linux-measurement/v1"
                and row.get("predicted") == row.get("label")
                and row.get("canonical_partition_match") is True
                and row.get("semantic_mismatch") is False for row in measurements)
        and artifact_hashes_match
        and dependencies.get("numpy") == "2.3.2"
        and runtime.get("source_files") == 14
        and runtime.get("runpod_pod_id") == pod_id
        and remote_validation.get("status") == "complete"
        and remote_validation.get("error") is None
    )
    absent = not any(inventories.values()) and details == {"v1": 404, "v2": 404}
    complete = all((lifecycle_valid, resources_valid, scientific_valid,
                    frozen_hashes_match, artifact_hashes_match, absent))
    result = {
        "schema": "crse-runpod-c7-linux-single-port-final-verification/v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if complete else "failed",
        "complete": complete,
        "scientific_confirmation_complete": scientific_valid,
        "pod_id": pod_id,
        "create_requests_this_authorization": 1,
        "automatic_replacement_queued": False,
        "uploaded_source_files": run.get("uploaded_source_files"),
        "owned_pod_absent_verified": absent,
        "inventories": inventories,
        "details_http_status": details,
        "lifecycle_valid": lifecycle_valid,
        "resources_valid": resources_valid,
        "scientific_evidence_valid": scientific_valid,
        "frozen_hashes_match": frozen_hashes_match,
        "artifact_hashes_match": artifact_hashes_match,
        "measurement_rows": len(measurements),
        "per_case_rows": len(per_case),
        "semantic_mismatches": summary.get("semantic_mismatches"),
        "criteria": summary.get("criteria"),
        "method_summary": summary.get("method_summary"),
        "elapsed_since_create_seconds": elapsed,
        "cleanup_limit_seconds": controller.CLEANUP_AT,
        "reconciliation_limit_seconds": controller.HORIZON,
        "rate_usd_per_hour": actual_rate,
        "projected_10_minute_cost_usd": projected_cost,
        "estimated_compute_cost_usd": estimated_cost,
        "total_cost_cap_usd": controller.CAMPAIGN_CAP,
    }
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    target = HERE / ("RUNPOD_C7_LINUX_SINGLE_PORT_FINAL_VERIFICATION_" + timestamp + ".json")
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({**result, "evidence_file": str(target)}, indent=2, sort_keys=True))
    return int(not complete)


if __name__ == "__main__":
    raise SystemExit(main())
