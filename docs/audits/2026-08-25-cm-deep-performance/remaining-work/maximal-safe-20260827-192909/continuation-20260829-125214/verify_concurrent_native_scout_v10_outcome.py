"""Read-only safety/evidence reconciliation for the concurrently launched V10 pod."""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET
import zipfile

import http_native_scout_preflight_v7 as api
import runpod_native_scout_controller_v7 as safe_controller


HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "native-procfs-v10-001"
POD_ID = "kvpu2s8ozs7j27"
PREVIOUS_FINAL = HERE / "CONCURRENT-NATIVE-SCOUT-V9-FINAL-VERIFICATION-20260829-160007-270042.json"
AUTHORIZATION = HERE / "HTTP-NATIVE-SCOUT-V10-RSS-REREAD-AUTHORIZED-20260829.invalid-no-replacement"
PROPOSAL = HERE / "RUNPOD-NATIVE-SCOUT-BOUNDED-RSS-REREAD-RETRY-PROPOSAL-20260829.md"
CONTROLLER = HERE / "runpod_native_scout_controller_v10.py"
PREFLIGHT = HERE / "http_native_scout_preflight_v10.py"
MANIFEST = HERE / "RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V7-20260829.json"
BOOTSTRAP = HERE / "http_native_scout_bootstrap_v2.py"
REMOTE = HERE / "runpod_native_scout_remote_v4.py"
WHEEL_LOCK = HERE.parent / "RUNPOD-WHEEL-LOCK.json"
PHASE_CAP_USD = 0.10
CAMPAIGN_CAP_USD = 0.20
STORAGE_RATE_RESERVE = 0.01


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evidence_check():
    archive = RUN_DIR / "evidence.zip"
    log = (RUN_DIR / "container.log").read_text(encoding="utf-8")
    starts = [
        json.loads(line[9:])
        for line in log.splitlines()
        if line.startswith("CM_EVENT ") and '"kind": "evidence_start"' in line
    ]
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if len(starts) != 1 or digest != starts[0]["sha256"] or archive.stat().st_size != starts[0]["bytes"]:
        raise ValueError("retrieved V10 evidence differs from remote markers")
    extracted = RUN_DIR / "evidence"
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        if len(infos) != len({row.filename for row in infos}):
            raise ValueError("duplicate evidence member")
        for info in infos:
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError("unsafe evidence path")
            target = (extracted / pure).resolve()
            target.relative_to(extracted.resolve())
            if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(bundle.read(info)).digest():
                raise ValueError("extracted evidence differs from V10 archive")
    output = extracted / "run-output"
    validation = load(output / "REMOTE-VALIDATION.json")
    runtime = load(output / "RUNTIME.json")
    focused = load(output / "focused-tests.json")
    p5 = load(output / "p5-smoke.json")
    p5_verify = load(output / "p5-smoke-verify.json")
    p5_summary = load(output / "p5-smoke/summary.json")
    native = load(output / "native-scout.json")
    native_summary = load(output / "native-scout/summary.json")
    environment = load(output / "native-scout/environment.json")
    dependencies = load(output / "native-scout/dependencies.json")
    controls = load(output / "native-scout/linux-controls.json")
    cadical = load(output / "native-scout/cadical.json")
    before = load(output / "SOURCE-BEFORE.json")
    after = load(output / "SOURCE-AFTER.json")
    manifest = load(MANIFEST)
    expected_source = [
        {"target": row["target"], "bytes": row["bytes"], "sha256": row["sha256"]}
        for row in manifest["files"]
    ]
    junit_root = ET.parse(output / "focused.xml").getroot()
    suites = list(junit_root.iter("testsuite"))
    metadata = {
        key: sum(int(suite.get(key, "0")) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    cases = list(junit_root.iter("testcase"))
    case_outcomes = {
        "failures": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
        "skipped": sum(case.find("skipped") is not None for case in cases),
    }
    control_statuses = {name: row.get("status") for name, row in controls.items()}
    control_cleanup = all(
        row.get("resources", {}).get("cleanup_verified") is True
        and row.get("resources", {}).get("streams_closed") is True
        and row.get("resources", {}).get("whole_tree_rss_measured") is True
        for row in controls.values()
    )
    expected_versions = {
        "astutils": "0.0.6",
        "dd": "0.6.0",
        "networkx": "3.6.1",
        "ply": "3.10",
        "python-sat": "1.9.dev15",
        "setuptools": "84.0.0",
        "six": "1.17.0",
        "wheel": "0.48.0",
    }
    cadical_supervision = cadical.get("supervision", {})
    return {
        "archive_sha256": digest,
        "archive_bytes": archive.stat().st_size,
        "archive_files": len(infos),
        "runtime_pod_id": runtime.get("runpod_pod_id"),
        "runtime_source_files": runtime.get("source_files"),
        "runtime_affinity": runtime.get("affinity"),
        "focused_returncode": focused.get("returncode"),
        "junit_metadata": metadata,
        "junit_testcase_elements": len(cases),
        "junit_case_outcomes": case_outcomes,
        "p5_returncode": p5.get("returncode"),
        "p5_verify_returncode": p5_verify.get("returncode"),
        "p5_summary": p5_summary,
        "native_returncode": native.get("returncode"),
        "native_summary": native_summary,
        "native_dependency_versions": dependencies.get("versions"),
        "native_control_statuses": control_statuses,
        "native_control_cleanup_verified": control_cleanup,
        "native_affinity": environment.get("cpu", {}).get("affinity"),
        "native_memory_max_bytes": environment.get("cgroup", {}).get("fields", {}).get("memory.max", {}).get("value"),
        "cadical_status": cadical.get("worker", {}).get("status"),
        "cadical_native_execution": cadical.get("worker", {}).get("native_execution"),
        "cadical_cases": cadical.get("worker", {}).get("cases"),
        "cadical_cleanup_verified": cadical_supervision.get("cleanup_verified"),
        "cadical_whole_tree_rss_measured": cadical_supervision.get("whole_tree_rss_measured"),
        "cudd_result_created": (output / "native-scout/cudd.json").exists(),
        "d4_result_created": (output / "native-scout/d4.json").exists(),
        "perf_result_created": (output / "native-scout/perf.json").exists(),
        "source_unchanged": before == after == expected_source,
        "failure_confirmed": (
            validation.get("status") == "failed"
            and validation.get("error") == "RuntimeError: native-scout failed with exit code 1"
            and validation.get("validation_errors") == []
            and focused.get("returncode") == 0
            and len(cases) == 64
            and case_outcomes == {"failures": 0, "errors": 0, "skipped": 0}
            and metadata == {"tests": 184, "failures": 0, "errors": 0, "skipped": 0}
            and p5.get("returncode") == 0
            and p5_verify.get("returncode") == 0
            and p5_summary.get("status") == "passed"
            and p5_summary.get("planned_cells") == 144
            and p5_summary.get("reconciliation", {}).get("observed_cells") == 144
            and p5_summary.get("reconciliation", {}).get("statuses") == {"ok": 144}
            and native.get("returncode") == 1
            and native_summary.get("status") == "failed"
            and native_summary.get("error") == "cudd native worker failed: process_tree_measurement_incomplete"
            and native_summary.get("performance_measurement") is False
            and native_summary.get("performance_ranking_permitted") is False
            and dependencies.get("versions") == expected_versions
            and dependencies.get("commands") == 7
            and dependencies.get("temporary_artifacts_retained") is False
            and control_statuses == {"echo": "ok", "flood": "output_limit", "memory": "memory_limit", "tree": "timeout"}
            and control_cleanup
            and cadical.get("worker", {}).get("status") == "passed"
            and cadical.get("worker", {}).get("native_execution") is True
            and cadical.get("worker", {}).get("cases") == 7
            and cadical_supervision.get("cleanup_verified") is True
            and cadical_supervision.get("whole_tree_rss_measured") is True
            and not (output / "native-scout/cudd.json").exists()
            and not (output / "native-scout/d4.json").exists()
            and not (output / "native-scout/perf.json").exists()
            and environment.get("cpu", {}).get("allocated_logical_from_affinity") == 2
            and before == after == expected_source
            and runtime.get("runpod_pod_id") == POD_ID
            and runtime.get("source_files") == 37
        ),
    }


def main():
    run = load(RUN_DIR / "RUN.json")
    resource = load(RUN_DIR / "POD-RESOURCE-CHECK.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    previous_final = load(PREVIOUS_FINAL)
    authorization = load(AUTHORIZATION)
    known = set(previous_final["checks"]["v1"]["details_http_status"]) | {POD_ID}
    result = {
        "checked_utc": api.utc_now(),
        "resource_writes": 0,
        "concurrent_launch_not_owned_by_this_task": True,
        "create_requests_observed": int(
            run.get("creation_attempted") is True and run.get("creation_http_status") == 201
        ),
        "automatic_replacement_queued_by_this_task": False,
        "pod_id": run.get("pod_id"),
        "controller_status": run.get("status"),
        "controller_error": run.get("error"),
    }
    with api.session() as client:
        checks = {}
        for version, endpoint in (("v1", api.V1), ("v2", api.V2)):
            details = {}
            for pod_id in sorted(known):
                response = client.get(endpoint + "/pods/" + pod_id, timeout=10, allow_redirects=False)
                details[pod_id] = response.status_code
            checks[version] = {
                "details_http_status": details,
                "inventory": api.inventory(client, endpoint),
            }
        result["checks"] = checks
        result["all_known_pods_absent_verified"] = all(
            not check["inventory"] and all(status == 404 for status in check["details_http_status"].values())
            for check in checks.values()
        )
        billing = api.billing_check(client)
    current_rows = [row for row in billing["historical_account_rows"] if row["podId"] == POD_ID]
    current_observed = sum(row["amount"] for row in current_rows)
    attempt_bound = (
        float(run["quoted_rate_usd_per_hour"]) + STORAGE_RATE_RESERVE
    ) * float(run["elapsed_since_create_s"]) / 3600
    correct_prior_bound = float(previous_final["corrected_attributable_campaign_bound_usd"])
    corrected_campaign_bound = correct_prior_bound + max(current_observed, attempt_bound)
    result["billing"] = {
        "metadata": billing["metadata"],
        "current_pod_rows": current_rows,
        "current_pod_observed_cost_usd": current_observed,
        "account_total_usd": billing["historical_total_usd"],
        "may_lag": True,
    }
    result["estimated_attempt_cost_bound_usd"] = attempt_bound
    result["correct_prior_campaign_bound_usd"] = correct_prior_bound
    result["controller_prior_cost_omitted_v7_attempt"] = (
        float(run["actual_resources"]["prior_cost_bound_usd"]) < correct_prior_bound
    )
    result["corrected_attributable_campaign_bound_usd"] = corrected_campaign_bound
    result["cost_within_user_caps"] = (
        max(current_observed, attempt_bound) <= PHASE_CAP_USD
        and corrected_campaign_bound <= CAMPAIGN_CAP_USD
    )
    pod = resource["pod"]
    result["actual_resource_identity_verified"] = (
        pod.get("id") == POD_ID
        and pod.get("name") == run.get("name")
        and pod.get("verified_v2_cloud") == "SECURE"
        and pod.get("cpuFlavorId") == "cpu3c"
        and pod.get("vcpuCount") == 2
        and float(pod.get("memoryInGb")) >= 4
        and float(pod.get("costPerHr")) == 0.06
        and pod.get("imageName") == safe_controller.base.IMAGE
        and pod.get("containerDiskInGb") == 12
        and type(pod.get("volumeInGb")) is int
        and pod.get("volumeInGb") == 0
        and sorted(pod.get("ports")) == sorted(safe_controller.EXPECTED_PORTS)
        and resource.get("network_volume_present") is False
    )
    result["chunked_transport_verified"] = (
        run.get("uploaded_source_files") == 37
        and run.get("uploaded_transport_bytes") == freeze.get("transport_payload_bytes")
        and run.get("upload_chunks") == math.ceil(freeze["transport_payload_bytes"] / safe_controller.CHUNK_BYTES)
        and run.get("upload_payload_sha256") == freeze.get("transport_payload_sha256")
        and run.get("remote_progress", {}).get("uploaded") is True
        and run.get("remote_progress", {}).get("started") is True
    )
    releases = {}
    for role in ("http-controller", "http-watchdog"):
        release = load(RUN_DIR / ("HOST-AWAKE-RELEASED-" + role + ".json"))
        releases[role] = {
            **release,
            "pid_still_running": safe_controller.windows_pid_running(release["pid"]),
        }
    result["guard_releases"] = releases
    result["guards_exited"] = all(
        row.get("released") is True and row["pid_still_running"] is False
        for row in releases.values()
    )
    result["watchdog"] = load(RUN_DIR / "WATCHDOG-RESULT.json")
    frozen_paths = (
        (CONTROLLER, "controller_sha256"),
        (PREFLIGHT, "preflight_sha256"),
        (BOOTSTRAP, "bootstrap_sha256"),
        (REMOTE, "remote_program_sha256"),
        (MANIFEST, "manifest_sha256"),
        (AUTHORIZATION, "authorization_sha256"),
        (PROPOSAL, "proposal_sha256"),
        (WHEEL_LOCK, "wheel_lock_sha256"),
    )
    result["frozen_transport_preserved"] = all(
        hashlib.sha256(path.read_bytes()).hexdigest() == freeze[field]
        for path, field in frozen_paths
    )
    manifest = load(MANIFEST)
    project = HERE.parents[5]
    worktree_mismatches = [
        row["source"]
        for row in manifest["files"]
        if not (project / row["source"]).is_file()
        or (project / row["source"]).stat().st_size != row["bytes"]
        or hashlib.sha256((project / row["source"]).read_bytes()).hexdigest() != row["sha256"]
    ]
    result["current_worktree_source_manifest_verified"] = not worktree_mismatches
    result["current_worktree_source_mismatches"] = worktree_mismatches
    result["evidence"] = evidence_check()
    result["uploaded_source_manifest_verified"] = result["evidence"]["source_unchanged"]
    result["authorization_scope"] = {
        "recorded_aggregate_campaign_cap_usd": authorization.get(
            "campaign_cap_usd", authorization.get("aggregate_campaign_cap_usd")
        ),
        "user_campaign_cap_usd": CAMPAIGN_CAP_USD,
        "record_has_no_replacement": authorization.get("no_replacement") is True,
        "record_text": authorization.get("authorization_text"),
        "conflicts_with_user_no_replacement_boundary": True,
        "invalidated_for_replay": not (HERE / "HTTP-NATIVE-SCOUT-V10-RSS-REREAD-AUTHORIZED-20260829.json").exists(),
    }
    result["authorization_compliant"] = False
    result["attempt_safely_reconciled"] = bool(
        result["create_requests_observed"] == 1
        and run.get("creation_uncertain") is False
        and run.get("cleanup", {}).get("owned_pod_absent") is True
        and result["all_known_pods_absent_verified"]
        and result["cost_within_user_caps"]
        and result["actual_resource_identity_verified"]
        and result["chunked_transport_verified"]
        and result["guards_exited"]
        and result["watchdog"].get("status") == "controller_cleanup_verified"
        and result["frozen_transport_preserved"]
        and result["uploaded_source_manifest_verified"]
        and result["evidence"]["failure_confirmed"]
    )
    result["workload_completed"] = False
    result["no_further_create_authorized"] = True
    output = HERE / (
        "CONCURRENT-NATIVE-SCOUT-V10-FINAL-VERIFICATION-"
        + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        + ".json"
    )
    safe_controller.write(output, result)
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(output))
    return int(not result["attempt_safely_reconciled"])


if __name__ == "__main__":
    raise SystemExit(main())
