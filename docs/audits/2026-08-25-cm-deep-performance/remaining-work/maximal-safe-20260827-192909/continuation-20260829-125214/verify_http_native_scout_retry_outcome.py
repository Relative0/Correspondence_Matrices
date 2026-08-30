"""Read-only postflight verification for the one authorized native-scout retry."""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import http_native_scout_preflight_v2 as preflight
import runpod_native_scout_controller_v2 as controller


HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "http-native-scout-retry-execute-001"
CURRENT_POD_ID = "76exgpsv0y39bl"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    run = load(RUN_DIR / "RUN.json")
    resource = load(RUN_DIR / "POD-RESOURCE-CHECK.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    prior = preflight.prior_attempts()
    known = set(prior["pod_ids"]) | {CURRENT_POD_ID}
    result = {
        "checked_utc": preflight.utc_now(),
        "resource_writes": 0,
        "create_requests_this_authorization": int(run.get("creation_attempted") is True),
        "automatic_replacement_queued": False,
        "controller_status": run.get("status"),
        "controller_error_type": run.get("error_type"),
        "pod_id": run.get("pod_id"),
    }
    with preflight.session() as client:
        checks = {}
        for version, endpoint in (("v1", preflight.V1), ("v2", preflight.V2)):
            details = {}
            for pod_id in sorted(known):
                response = client.get(endpoint + "/pods/" + pod_id, timeout=10, allow_redirects=False)
                details[pod_id] = response.status_code
            checks[version] = {
                "details_http_status": details,
                "inventory": preflight.inventory(client, endpoint),
            }
        result["checks"] = checks
        result["owned_pods_absent_verified"] = all(
            not check["inventory"]
            and all(status == 404 for status in check["details_http_status"].values())
            for check in checks.values()
        )
        billing = preflight.billing_check(client)
    rows = billing["historical_account_rows"]
    current_rows = [row for row in rows if row["podId"] == CURRENT_POD_ID]
    current_observed = sum(row["amount"] for row in current_rows)
    current_bound = (
        float(run["quoted_rate_usd_per_hour"]) + controller.STORAGE_RATE_RESERVE
    ) * float(run["elapsed_since_create_s"]) / 3600
    campaign_bound = (
        float(run["actual_resources"]["prior_cost_bound_usd"])
        + max(current_observed, current_bound)
    )
    result["billing"] = {
        "metadata": billing["metadata"],
        "current_pod_rows": current_rows,
        "current_pod_observed_cost_usd": current_observed,
        "account_total_usd": billing["historical_total_usd"],
        "may_lag": True,
        "all_rows_attributed": all(row["podId"] in known for row in rows),
    }
    result["estimated_retry_cost_bound_usd"] = current_bound
    result["attributable_campaign_cost_bound_usd"] = campaign_bound
    result["cost_within_caps"] = (
        max(current_observed, current_bound) <= controller.PHASE_CAP
        and campaign_bound <= controller.CAMPAIGN_CAP
    )

    pod = resource["pod"]
    result["actual_resource_identity_verified"] = (
        pod.get("id") == CURRENT_POD_ID
        and pod.get("name") == run.get("name")
        and pod.get("verified_v2_cloud") == "SECURE"
        and pod.get("cpuFlavorId") == "cpu3c"
        and pod.get("vcpuCount") == 2
        and float(pod.get("memoryInGb")) >= 4
        and float(pod.get("costPerHr")) == float(run["quoted_rate_usd_per_hour"])
        and pod.get("imageName") == controller.base.IMAGE
        and pod.get("containerDiskInGb") == 12
        and type(pod.get("volumeInGb")) is int
        and pod.get("volumeInGb") == 0
        and pod.get("volumeMountPath") == "/workspace"
        and sorted(pod.get("ports")) == sorted(controller.EXPECTED_PORTS)
        and resource.get("network_volume_present") is False
        and resource.get("gpu") == {"count": None, "id": None}
    )

    releases = {}
    for role in ("http-controller", "http-watchdog"):
        release = load(RUN_DIR / ("HOST-AWAKE-RELEASED-" + role + ".json"))
        releases[role] = {
            **release,
            "pid_still_running": controller.windows_pid_running(release["pid"]),
        }
    result["guard_releases"] = releases
    result["guards_exited"] = all(
        release.get("released") is True and release["pid_still_running"] is False
        for release in releases.values()
    )
    result["watchdog"] = load(RUN_DIR / "WATCHDOG-RESULT.json")

    frozen_paths = (
        (Path(controller.__file__), "controller_sha256"),
        (Path(preflight.__file__), "preflight_sha256"),
        (controller.BOOTSTRAP_PATH, "bootstrap_sha256"),
        (controller.REMOTE_CODE_PATH, "remote_program_sha256"),
        (controller.MANIFEST_PATH, "manifest_sha256"),
        (controller.AUTHORIZATION_PATH, "authorization_sha256"),
        (controller.PROPOSAL_PATH, "proposal_sha256"),
        (controller.base.LOCK_PATH, "wheel_lock_sha256"),
    )
    result["frozen_transport_preserved"] = all(
        hashlib.sha256(path.read_bytes()).hexdigest() == freeze[field]
        for path, field in frozen_paths
    )
    controller.require_authorization()
    manifest = load(controller.MANIFEST_PATH)
    project = HERE.parents[5]
    result["approved_source_manifest_verified"] = (
        len(manifest["files"]) == 30
        and sum(row["bytes"] for row in manifest["files"]) == manifest["bytes"]
        and all(
            (project / row["source"]).stat().st_size == row["bytes"]
            and hashlib.sha256((project / row["source"]).read_bytes()).hexdigest() == row["sha256"]
            for row in manifest["files"]
        )
    )
    result["transfer_and_workload"] = {
        "bootstrap_health_confirmed": isinstance(run.get("bootstrap_ready_utc"), str),
        "payload_request_dispatched": True,
        "payload_acceptance_acknowledged": False,
        "payload_acceptance_uncertain": True,
        "controller_accepted_source_files": run.get("uploaded_source_files"),
        "worker_start_request_reached": "worker_started_utc" in run,
        "workload_completed": False,
        "evidence_retrieved": False,
    }
    result["failure_diagnosis"] = {
        "confirmed": (
            run.get("error_type") == "ReadTimeout"
            and result["transfer_and_workload"]["bootstrap_health_confirmed"]
            and run.get("uploaded_source_files") == 0
            and "worker_started_utc" not in run
        ),
        "failing_operation": "POST /payload response within the frozen 20-second client timeout",
        "stage": "after bootstrap health and before acknowledged upload or worker start",
        "payload_delivery_cannot_be_proven_from_a_read_timeout": True,
    }
    result["attempt_safely_reconciled"] = bool(
        result["create_requests_this_authorization"] == 1
        and run.get("creation_http_status") == 201
        and run.get("creation_uncertain") is False
        and run.get("cleanup", {}).get("owned_pod_absent") is True
        and result["owned_pods_absent_verified"]
        and result["billing"]["all_rows_attributed"]
        and result["cost_within_caps"]
        and result["actual_resource_identity_verified"]
        and result["guards_exited"]
        and result["watchdog"].get("status") == "controller_cleanup_verified"
        and result["frozen_transport_preserved"]
        and result["approved_source_manifest_verified"]
        and result["failure_diagnosis"]["confirmed"]
    )
    result["authorization_consumed"] = True
    output = HERE / (
        "HTTP-NATIVE-SCOUT-RETRY-FINAL-VERIFICATION-"
        + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        + ".json"
    )
    controller.write(output, result)
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(output))
    return int(not result["attempt_safely_reconciled"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}))
        raise SystemExit(2)
