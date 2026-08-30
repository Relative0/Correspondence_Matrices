"""Reconcile the single authorized Linux-confirmation pod and frozen evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
CONTROLLER_PATH = HERE / "runpod_linux_one_pass_controller.py"
spec = importlib.util.spec_from_file_location("linux_confirmation_controller", CONTROLLER_PATH)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
RUN_DIR = controller.OUT


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    run = load(RUN_DIR / "RUN.json")
    identity = load(RUN_DIR / "POD-IDENTITY.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    watchdog = load(RUN_DIR / "WATCHDOG-RESULT.json")
    controller_release = load(RUN_DIR / "HOST-AWAKE-RELEASED-http-controller.json")
    watchdog_release = load(RUN_DIR / "HOST-AWAKE-RELEASED-http-watchdog.json")
    study = RUN_DIR / "evidence" / "run-output" / "linux-one-pass-confirmation"
    summary = load(study / "summary.json")
    artifact_manifest = load(study / "manifest.json")
    measurements = [json.loads(line) for line in
                    (study / "measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    pod_id = identity["pod_id"]

    with controller.preflight.session() as client:
        inventories = controller.inventories(client)
        details = {}
        for name, endpoint in (("v1", controller.preflight.V1), ("v2", controller.preflight.V2)):
            response = client.get(endpoint + "/pods/" + pod_id, timeout=10, allow_redirects=False)
            details[name] = response.status_code

    elapsed = float(run["elapsed_since_create_s"])
    actual_rate = float(run["actual_resources"]["rate_usd_per_hour"])
    projected_cost = float(run["actual_resources"]["projected_10_min_cost_usd"])
    estimated_cost = float(run["estimated_compute_cost_usd"])
    artifact_hashes_match = artifact_manifest.get("files_sha256") == {
        "measurements.jsonl": sha256(study / "measurements.jsonl"),
        "summary.json": sha256(study / "summary.json"),
    }
    frozen_hashes_match = (
        freeze.get("controller_sha256") == sha256(CONTROLLER_PATH)
        and freeze.get("authorization_sha256") == sha256(controller.AUTHORIZATION_PATH)
        and freeze.get("proposal_sha256") == sha256(controller.PROPOSAL_PATH)
        and freeze.get("manifest_sha256") == sha256(controller.MANIFEST_PATH)
        and freeze.get("source_files") == 16
        and freeze.get("source_bytes") == 573061
    )
    lifecycle_valid = (
        run.get("status") == "complete"
        and run.get("creation_attempted") is True
        and run.get("creation_http_status") == 201
        and run.get("creation_uncertain") is False
        and run.get("pod_created") is True
        and run.get("pod_id") == pod_id
        and run.get("uploaded_source_files") == 16
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
        and run.get("actual_resources", {}).get("cloud_evidence") == ["SECURE"]
        and run.get("actual_resources", {}).get("image") == controller.base.IMAGE
        and 0 < actual_rate <= controller.RATE_CAP
        and projected_cost <= controller.CAMPAIGN_CAP
        and estimated_cost <= controller.CAMPAIGN_CAP
    )
    scientific_valid = (
        summary.get("schema") == "crse-linux-one-pass-confirmation/v1"
        and summary.get("status") == "complete"
        and summary.get("semantic_mismatches") == 0
        and summary.get("config") == {"cases": 32, "cpu_threads": 1,
                                      "kernel_repeats": 128, "rounds": 5}
        and len(measurements) == 10
        and all(row.get("status") == "ok" and row.get("mismatches") == 0
                and row.get("case_count") == 32 for row in measurements)
        and artifact_hashes_match
    )
    absent = not any(inventories.values()) and details == {"v1": 404, "v2": 404}
    complete = all((lifecycle_valid, resources_valid, scientific_valid,
                    frozen_hashes_match, absent))
    result = {
        "schema": "crse-runpod-linux-confirmation-final-verification/v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "complete": complete,
        "pod_id": pod_id,
        "create_requests_this_authorization": 1,
        "automatic_replacement_queued": False,
        "owned_pod_absent_verified": absent,
        "inventories": inventories,
        "details_http_status": details,
        "lifecycle_valid": lifecycle_valid,
        "resources_valid": resources_valid,
        "frozen_hashes_match": frozen_hashes_match,
        "scientific_evidence_valid": scientific_valid,
        "artifact_hashes_match": artifact_hashes_match,
        "elapsed_since_create_seconds": elapsed,
        "cleanup_limit_seconds": controller.CLEANUP_AT,
        "reconciliation_limit_seconds": controller.HORIZON,
        "rate_usd_per_hour": actual_rate,
        "projected_10_minute_cost_usd": projected_cost,
        "estimated_compute_cost_usd": estimated_cost,
        "total_cost_cap_usd": controller.CAMPAIGN_CAP,
        "semantic_mismatches": summary["semantic_mismatches"],
        "confirmation_passed": summary["summaries"]["confirmation_passed"],
        "one_pass_speedup_over_no_rewrite": summary["summaries"]["one_pass_speedup_over_no_rewrite"],
    }
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    target = HERE / ("RUNPOD_LINUX_ONE_PASS_FINAL_VERIFICATION_" + timestamp + ".json")
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8", newline="\n")
    print(json.dumps({**result, "evidence_file": str(target)}, indent=2, sort_keys=True))
    return int(not complete)


if __name__ == "__main__":
    raise SystemExit(main())
