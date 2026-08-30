"""Reconcile the one authorized C7 pod after its pre-upload transport failure."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTROLLER_PATH = HERE / "runpod_c7_linux_confirmation_controller.py"
spec = importlib.util.spec_from_file_location("c7_linux_confirmation_controller", CONTROLLER_PATH)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
RUN_DIR = controller.OUT


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
    frozen_hashes_match = (
        freeze.get("controller_sha256") == sha(CONTROLLER_PATH)
        and freeze.get("authorization_sha256") == sha(controller.AUTHORIZATION_PATH)
        and freeze.get("proposal_sha256") == sha(controller.PROPOSAL_PATH)
        and freeze.get("manifest_sha256") == sha(controller.MANIFEST_PATH)
        and freeze.get("source_files") == 14
        and freeze.get("source_bytes") == 322080
    )
    lifecycle_valid = (
        run.get("status") == "failed"
        and run.get("error") == "proxy HTTP 404"
        and run.get("creation_attempted") is True
        and run.get("creation_http_status") == 201
        and run.get("creation_uncertain") is False
        and run.get("pod_created") is True
        and run.get("pod_id") == pod_id
        and run.get("uploaded_source_files") == 0
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
        and math.isfinite(actual_rate) and 0 < actual_rate <= controller.RATE_CAP
        and projected_cost <= controller.CAMPAIGN_CAP
        and estimated_cost <= controller.CAMPAIGN_CAP
    )
    absent = not any(inventories.values()) and details == {"v1": 404, "v2": 404}
    safely_reconciled = all((lifecycle_valid, resources_valid, frozen_hashes_match, absent))
    result = {
        "schema": "crse-runpod-c7-linux-confirmation-final-verification/v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "status": "safe_failure_reconciled" if safely_reconciled else "reconciliation_failed",
        "complete": safely_reconciled,
        "scientific_confirmation_complete": False,
        "failure_stage": "token-gated payload upload",
        "failure": "HTTP 404 before source upload",
        "pod_id": pod_id,
        "create_requests_this_authorization": 1,
        "automatic_replacement_queued": False,
        "uploaded_source_files": 0,
        "owned_pod_absent_verified": absent,
        "inventories": inventories,
        "details_http_status": details,
        "lifecycle_valid": lifecycle_valid,
        "resources_valid": resources_valid,
        "frozen_hashes_match": frozen_hashes_match,
        "elapsed_since_create_seconds": elapsed,
        "cleanup_limit_seconds": controller.CLEANUP_AT,
        "reconciliation_limit_seconds": controller.HORIZON,
        "rate_usd_per_hour": actual_rate,
        "projected_10_minute_cost_usd": projected_cost,
        "estimated_compute_cost_usd": estimated_cost,
        "total_cost_cap_usd": controller.CAMPAIGN_CAP,
    }
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    target = HERE / ("RUNPOD_C7_LINUX_FINAL_VERIFICATION_" + timestamp + ".json")
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({**result, "evidence_file": str(target)}, indent=2, sort_keys=True))
    return int(not safely_reconciled)


if __name__ == "__main__":
    raise SystemExit(main())
