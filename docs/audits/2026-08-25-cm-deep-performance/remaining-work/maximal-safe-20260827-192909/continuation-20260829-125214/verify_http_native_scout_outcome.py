"""Read-only postflight verification for the one authorized native scout attempt."""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import http_native_scout_preflight_v1 as preflight
import runpod_native_scout_controller_v1 as controller


HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "http-native-scout-execute-001"
CURRENT_POD_ID = "84442bdg4m47x8"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    run = load(RUN_DIR / "RUN.json")
    ready = load(RUN_DIR / "PREFLIGHT.json")
    resource = load(RUN_DIR / "POD-RESOURCE-CHECK.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    known = set(preflight.prior_attempts()["pod_ids"]) | {CURRENT_POD_ID}
    result = {
        "checked_utc": preflight.utc_now(),
        "resource_writes": 0,
        "create_requests_this_authorization": int(run.get("creation_attempted") is True),
        "automatic_replacement_queued": False,
        "controller_status": run.get("status"),
        "controller_error_type": run.get("error_type"),
        "pod_id": run.get("pod_id"),
        "source_files_uploaded": run.get("uploaded_source_files"),
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
    result["billing"] = {
        "metadata": billing["metadata"],
        "current_pod_rows": current_rows,
        "current_pod_observed_cost_usd": sum(row["amount"] for row in current_rows),
        "account_total_usd": billing["historical_total_usd"],
        "may_lag": True,
        "all_rows_attributed": all(row["podId"] in known for row in rows),
    }
    elapsed = float(run["elapsed_since_create_s"])
    quoted_rate = float(run["quoted_rate_usd_per_hour"])
    estimated_bound = (quoted_rate + controller.STORAGE_RATE_RESERVE) * elapsed / 3600
    result["estimated_attempt_cost_bound_usd"] = estimated_bound
    result["cost_within_caps"] = (
        max(estimated_bound, result["billing"]["current_pod_observed_cost_usd"]) <= controller.PHASE_CAP
        and max(estimated_bound, result["billing"]["current_pod_observed_cost_usd"]) <= controller.CAMPAIGN_CAP
    )

    pod = resource["pod"]
    result["actual_resource_identity_verified"] = (
        pod.get("id") == CURRENT_POD_ID
        and pod.get("name") == run.get("name")
        and pod.get("verified_v2_cloud") == "SECURE"
        and pod.get("cpuFlavorId") == "cpu3c"
        and pod.get("vcpuCount") == 2
        and float(pod.get("memoryInGb")) >= 4
        and float(pod.get("costPerHr")) == quoted_rate
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
    manifest_rows_match = all(
        (project / row["source"]).stat().st_size == row["bytes"]
        and hashlib.sha256((project / row["source"]).read_bytes()).hexdigest() == row["sha256"]
        for row in manifest["files"]
    )
    result["approved_source_manifest_verified"] = (
        len(manifest["files"]) == 30
        and sum(row["bytes"] for row in manifest["files"]) == manifest["bytes"]
        and manifest_rows_match
    )

    result["failure_diagnosis"] = {
        "confirmed": (
            "prior_cost_bound_usd" not in ready
            and ready.get("prior_attempts", {}).get("new_comparative_campaign_cost_before_scout_usd") == 0.0
            and run.get("error_type") == "KeyError"
            and run.get("uploaded_source_files") == 0
        ),
        "failing_expression": "ready['prior_cost_bound_usd']",
        "controller_line": 581,
        "stage": "after actual-resource observation and before source upload",
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
    result["workload_completed"] = False
    result["authorization_consumed"] = True
    output = HERE / (
        "HTTP-NATIVE-SCOUT-FINAL-VERIFICATION-"
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
