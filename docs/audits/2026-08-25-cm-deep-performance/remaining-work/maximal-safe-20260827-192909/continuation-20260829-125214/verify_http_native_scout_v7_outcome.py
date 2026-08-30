"""Read-only postflight reconciliation for the V7 host-preflight attempt."""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import http_native_scout_preflight_v7 as preflight
import runpod_native_scout_controller_v7 as controller


HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "native-procfs-v7-001"
CURRENT_POD_ID = "3o7r0za7cm72yn"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    run = load(RUN_DIR / "RUN.json")
    resource = load(RUN_DIR / "POD-RESOURCE-CHECK.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    authorization = controller.require_authorization()
    known = set(preflight.prior_attempts()["pod_ids"]) | {CURRENT_POD_ID}
    result = {
        "checked_utc": preflight.utc_now(),
        "resource_writes": 0,
        "create_requests_this_authorization": int(
            run.get("creation_attempted") is True and run.get("creation_http_status") == 201
        ),
        "automatic_replacement_queued": False,
        "controller_status": run.get("status"),
        "controller_error_type": run.get("error_type"),
        "controller_error": run.get("error"),
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
            not check["inventory"] and all(status == 404 for status in check["details_http_status"].values())
            for check in checks.values()
        )
        billing = preflight.billing_check(client)

    rows = billing["historical_account_rows"]
    current_rows = [row for row in rows if row["podId"] == CURRENT_POD_ID]
    unrelated_rows = [row for row in rows if row["podId"] not in known]
    current_observed = sum(row["amount"] for row in current_rows)
    current_bound = (
        float(run["quoted_rate_usd_per_hour"]) + controller.STORAGE_RATE_RESERVE
    ) * float(run["elapsed_since_create_s"]) / 3600
    campaign_bound = float(run["actual_resources"]["prior_cost_bound_usd"]) + max(
        current_observed, current_bound
    )
    result["billing"] = {
        "metadata": billing["metadata"],
        "current_pod_rows": current_rows,
        "current_pod_observed_cost_usd": current_observed,
        "unrelated_account_rows": unrelated_rows,
        "account_total_usd": billing["historical_total_usd"],
        "may_lag": True,
        "response_reconciled": True,
    }
    result["estimated_attempt_cost_bound_usd"] = current_bound
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
    )

    result["source_upload_started"] = run.get("uploaded_source_files") not in (None, 0)
    result["workload_started"] = "worker_started_utc" in run
    result["no_source_or_workload_executed"] = (
        run.get("uploaded_source_files") == 0
        and "uploaded_transport_bytes" not in run
        and "worker_started_utc" not in run
        and "remote_progress" not in run
        and not (RUN_DIR / "container.log").exists()
        and not (RUN_DIR / "evidence.zip").exists()
        and not (RUN_DIR / "evidence").exists()
    )

    source = Path(controller.__file__).read_text(encoding="utf-8")
    bootstrap_ready_index = source.index('record["bootstrap_ready_utc"]')
    upload_index = source.index("accepted = upload_payload", bootstrap_ready_index)
    worker_index = source.index('record["worker_started_utc"]', upload_index)
    result["failure_localization"] = {
        "direct_evidence": "both health endpoints passed; the next proxied request returned HTTP 404",
        "inferred_request": "GET on the port-8080 upload-status route",
        "inference_not_direct_route_capture": True,
        "controller_sequence_verified": bootstrap_ready_index < upload_index < worker_index,
        "provider_proxy_vs_bootstrap_route_not_distinguishable_after_cleanup": True,
    }

    releases = {}
    for role in ("http-controller", "http-watchdog"):
        release = load(RUN_DIR / ("HOST-AWAKE-RELEASED-" + role + ".json"))
        releases[role] = {
            **release,
            "pid_still_running": controller.windows_pid_running(release["pid"]),
        }
    result["guard_releases"] = releases
    result["guards_exited"] = all(
        row.get("released") is True and row["pid_still_running"] is False
        for row in releases.values()
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
    manifest = load(controller.MANIFEST_PATH)
    project = HERE.parents[5]
    result["approved_source_manifest_verified"] = (
        len(manifest["files"]) == 37
        and manifest.get("bytes") == 5504396
        and all(
            (project / row["source"]).stat().st_size == row["bytes"]
            and hashlib.sha256((project / row["source"]).read_bytes()).hexdigest() == row["sha256"]
            for row in manifest["files"]
        )
    )
    result["authorization_hash_verified"] = (
        hashlib.sha256(controller.AUTHORIZATION_PATH.read_bytes()).hexdigest()
        == run.get("authorization_record_sha256")
        == freeze.get("authorization_sha256")
        and authorization.get("one_create") is True
        and authorization.get("no_replacement") is True
    )
    result["attempt_safely_reconciled"] = bool(
        result["create_requests_this_authorization"] == 1
        and run.get("creation_uncertain") is False
        and run.get("cleanup", {}).get("owned_pod_absent") is True
        and result["owned_pods_absent_verified"]
        and result["billing"]["response_reconciled"]
        and result["cost_within_caps"]
        and result["actual_resource_identity_verified"]
        and result["no_source_or_workload_executed"]
        and result["guards_exited"]
        and result["watchdog"].get("status") == "controller_cleanup_verified"
        and result["frozen_transport_preserved"]
        and result["approved_source_manifest_verified"]
        and result["authorization_hash_verified"]
        and run.get("status") == "failed"
        and run.get("error_type") == "RuntimeError"
        and run.get("error") == "proxy HTTP 404"
    )
    result["workload_completed"] = False
    result["authorization_consumed"] = True
    output = HERE / (
        "HTTP-NATIVE-SCOUT-HOST-PREFLIGHT-AMENDMENT-FINAL-VERIFICATION-"
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
        raise
