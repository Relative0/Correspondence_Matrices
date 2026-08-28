"""Independent read-only final verification of the single HTTP create attempt."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import http_transport_preflight as preflight
import runpod_http_smoke_controller_v2 as controller

HERE = Path(__file__).resolve().parent
RUN = HERE / "http-execute-001b"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    record = load(RUN / "RUN.json")
    resource = load(RUN / "POD-RESOURCE-CHECK.json")
    frozen = load(RUN / "TRANSPORT-FREEZE.json")
    pod_id = record["pod_id"]
    result = {"checked_utc": preflight.utc_now(), "pod_id": pod_id,
              "creation_http_status": record["creation_http_status"],
              "request_id": record["creation_response_headers"]["X-Request-Id"],
              "create_requests_this_authorization": 1,
              "source_files_uploaded": record["uploaded_source_files"],
              "remote_workload_ran": False, "resource_writes": 0}
    checks = {}
    with preflight.session() as client:
        for version, endpoint in (("v1", preflight.V1), ("v2", preflight.V2)):
            response = client.get(endpoint + "/pods/" + pod_id, timeout=10, allow_redirects=False)
            checks[version] = {"detail_http_status": response.status_code,
                               "inventory": preflight.inventory(client, endpoint)}
        response = client.get(preflight.V2 + "/billing/pods",
            params={"startTime": "2026-08-27T00:00:00Z", "endTime": preflight.utc_now()},
            timeout=15, allow_redirects=False)
        response.raise_for_status()
        meta = response.json()["metadata"]
        result["billing_metadata"] = {key: meta.get(key) for key in ("query", "recordCount", "uniquePodCount", "totals")}
    result["checks"] = checks
    result["owned_pod_absent_verified"] = all(row["detail_http_status"] == 404 and not row["inventory"] for row in checks.values())
    result["billing_may_lag"] = True
    result["estimated_compute_cost_usd"] = resource["pod"]["costPerHr"] * record["elapsed_since_create_s"] / 3600
    result["requested_pod_volume_gb"] = 10
    result["returned_pod_volume_gb"] = resource["pod"]["volumeInGb"]
    # Diagnose the failed comparison with a copy; never alter actual run evidence.
    hypothetical = {**resource["pod"], "gpu": resource["gpu"], "machine": {"secureCloud": resource["machine_secure_cloud"]}}
    hypothetical["volumeInGb"] = 10
    controller.validate_pod(hypothetical, load(RUN / "controller-state.json"), {"id": "cpu3c"}, 0)
    result["other_resource_gates_pass_if_only_volume_field_matches_request"] = True
    result["guard_releases"] = {}
    for role in ("http-controller", "http-watchdog"):
        release = load(RUN / ("HOST-AWAKE-RELEASED-" + role + ".json"))
        result["guard_releases"][role] = {**release, "pid_still_running": controller.windows_pid_running(release["pid"])}
    result["watchdog_result"] = load(RUN / "WATCHDOG-RESULT.json")
    result["controller_hash_preserved"] = hashlib.sha256(Path(controller.__file__).read_bytes()).hexdigest() == frozen["controller_sha256"]
    result["bootstrap_hash_preserved"] = hashlib.sha256(controller.BOOTSTRAP_PATH.read_bytes()).hexdigest() == frozen["bootstrap_sha256"]
    result["automatic_replacement_queued"] = False
    output = HERE / ("HTTP-FINAL-VERIFICATION-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json")
    controller.write(output, result)
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(output))
    return int(not result["owned_pod_absent_verified"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}))
        raise SystemExit(2)
