"""Read-only postflight and partial-evidence audit for the P5-corrected scout."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET
import zipfile

import http_native_scout_preflight_v5 as preflight
import runpod_native_scout_controller_v5 as controller


HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "http-native-scout-p5-cli-retry-execute-001"
CURRENT_POD_ID = "pow0qre2q39m4t"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evidence_check():
    archive = RUN_DIR / "evidence.zip"
    log = (RUN_DIR / "container.log").read_text(encoding="utf-8")
    starts = [json.loads(line[9:]) for line in log.splitlines()
              if line.startswith("CM_EVENT ") and '"kind": "evidence_start"' in line]
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if len(starts) != 1 or digest != starts[0]["sha256"] or archive.stat().st_size != starts[0]["bytes"]:
        raise ValueError("retrieved failure evidence differs from remote markers")
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
                raise ValueError("extracted evidence differs from archive")
    output = extracted / "run-output"
    validation = load(output / "REMOTE-VALIDATION.json")
    runtime = load(output / "RUNTIME.json")
    focused = load(output / "focused-tests.json")
    p5 = load(output / "p5-smoke.json")
    p5_verify = load(output / "p5-smoke-verify.json")
    p5_summary = load(output / "p5-smoke/summary.json")
    native = load(output / "native-scout.json")
    native_summary = load(output / "native-scout/summary.json")
    native_environment = load(output / "native-scout/environment.json")
    native_dependencies = load(output / "native-scout/dependencies.json")
    native_controls = load(output / "native-scout/linux-controls.json")
    before = load(output / "SOURCE-BEFORE.json")
    after = load(output / "SOURCE-AFTER.json")
    junit_root = ET.parse(output / "focused.xml").getroot()
    suites = list(junit_root.iter("testsuite"))
    metadata = {key: sum(int(suite.get(key, "0")) for suite in suites)
                for key in ("tests", "failures", "errors", "skipped")}
    cases = list(junit_root.iter("testcase"))
    failed_cases = [case for case in cases if case.find("failure") is not None]
    error_cases = [case for case in cases if case.find("error") is not None]
    skipped_cases = [case for case in cases if case.find("skipped") is not None]
    manifest = load(controller.MANIFEST_PATH)
    expected = [{"target": row["target"], "bytes": row["bytes"], "sha256": row["sha256"]}
                for row in manifest["files"]]
    expected_versions = {
        "astutils": "0.0.6", "dd": "0.6.0", "networkx": "3.6.1", "ply": "3.10",
        "python-sat": "1.9.dev15", "setuptools": "84.0.0", "six": "1.17.0", "wheel": "0.48.0",
    }
    control_statuses = {name: row.get("status") for name, row in native_controls.items()}
    control_cleanup = all(
        row.get("resources", {}).get("cleanup_verified") is True
        and row.get("resources", {}).get("streams_closed") is True
        and row.get("resources", {}).get("whole_tree_rss_measured") is True
        for row in native_controls.values()
    )
    return {
        "archive_sha256": digest,
        "archive_bytes": archive.stat().st_size,
        "archive_files": len(infos),
        "remote_status": validation.get("status"),
        "remote_error": validation.get("error"),
        "remote_validation_errors": validation.get("validation_errors"),
        "runtime_pod_id": runtime.get("runpod_pod_id"),
        "runtime_source_files": runtime.get("source_files"),
        "runtime_affinity": runtime.get("affinity"),
        "focused_returncode": focused.get("returncode"),
        "p5_returncode": p5.get("returncode"),
        "p5_verify_returncode": p5_verify.get("returncode"),
        "p5_command": p5.get("command"),
        "p5_summary": p5_summary,
        "native_returncode": native.get("returncode"),
        "native_summary": native_summary,
        "native_dependency_versions": native_dependencies.get("versions"),
        "native_control_statuses": control_statuses,
        "native_control_cleanup_verified": control_cleanup,
        "native_affinity": native_environment.get("cpu", {}).get("affinity"),
        "native_memory_max_bytes": native_environment.get("cgroup", {}).get("fields", {}).get("memory.max", {}).get("value"),
        "junit_metadata": metadata,
        "junit_testcase_elements": len(cases),
        "junit_failed_testcase_elements": len(failed_cases),
        "junit_error_testcase_elements": len(error_cases),
        "junit_skipped_testcase_elements": len(skipped_cases),
        "source_after_recorded": True,
        "source_unchanged": before == after == expected,
        "primary_failure_confirmed": (
            validation.get("status") == "failed"
            and validation.get("error") == "RuntimeError: native-scout failed with exit code 1"
            and focused.get("returncode") == 0
            and p5.get("returncode") == 0
            and p5_verify.get("returncode") == 0
            and p5_summary.get("status") == "passed"
            and p5_summary.get("planned_cells") == 144
            and p5_summary.get("reconciliation", {}).get("observed_cells") == 144
            and p5_summary.get("reconciliation", {}).get("statuses") == {"ok": 144}
            and native.get("returncode") == 1
            and native_summary.get("status") == "failed"
            and native_summary.get("error") == "sat native worker failed: process_tree_measurement_incomplete"
            and native_summary.get("performance_measurement") is False
            and native_summary.get("performance_ranking_permitted") is False
            and native_dependencies.get("versions") == expected_versions
            and native_dependencies.get("commands") == 7
            and native_dependencies.get("temporary_artifacts_retained") is False
            and control_statuses == {"echo": "ok", "flood": "output_limit", "memory": "memory_limit", "tree": "timeout"}
            and control_cleanup
            and native_environment.get("cpu", {}).get("allocated_logical_from_affinity") == 2
            and native_environment.get("cgroup", {}).get("fields", {}).get("memory.max", {}).get("value") == 3999997952
            and not (output / "native-scout/cadical.json").exists()
            and not (output / "native-scout/cudd.json").exists()
            and not (output / "native-scout/d4.json").exists()
            and not (output / "native-scout/perf.json").exists()
            and len(cases) == 60
            and not failed_cases and not error_cases and not skipped_cases
            and metadata == {"tests": 180, "failures": 0, "errors": 0, "skipped": 0}
            and validation.get("junit_testcases") == {
                "tests": 60, "failures": 0, "errors": 0, "skipped": 0
            }
            and validation.get("source_unchanged") is True
            and before == after == expected
            and validation.get("validation_errors") == []
            and validation.get("smoke_summary") == {
                "status": "passed", "planned_cells": 144, "observed_cells": 144, "statuses": {"ok": 144}
            }
            and runtime.get("runpod_pod_id") == CURRENT_POD_ID
            and runtime.get("source_files") == 37
        ),
        "p5_started": (output / "p5-smoke.json").exists(),
        "p5_summary_created": (output / "p5-smoke/summary.json").exists(),
        "native_scout_started": (output / "native-scout").exists(),
        "native_summary_created": (output / "native-scout/summary.json").exists(),
    }


def main():
    run = load(RUN_DIR / "RUN.json")
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
    campaign_bound = float(run["actual_resources"]["prior_cost_bound_usd"]) + max(current_observed, current_bound)
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
    result["cost_within_caps"] = max(current_observed, current_bound) <= controller.PHASE_CAP and campaign_bound <= controller.CAMPAIGN_CAP

    pod = resource["pod"]
    result["actual_resource_identity_verified"] = (
        pod.get("id") == CURRENT_POD_ID and pod.get("name") == run.get("name")
        and pod.get("verified_v2_cloud") == "SECURE" and pod.get("cpuFlavorId") == "cpu3c"
        and pod.get("vcpuCount") == 2 and float(pod.get("memoryInGb")) >= 4
        and float(pod.get("costPerHr")) == float(run["quoted_rate_usd_per_hour"])
        and pod.get("imageName") == controller.base.IMAGE and pod.get("containerDiskInGb") == 12
        and type(pod.get("volumeInGb")) is int and pod.get("volumeInGb") == 0
        and pod.get("volumeMountPath") == "/workspace"
        and sorted(pod.get("ports")) == sorted(controller.EXPECTED_PORTS)
        and resource.get("network_volume_present") is False
    )
    result["chunked_transport_verified"] = (
        run.get("uploaded_source_files") == 37
        and run.get("uploaded_transport_bytes") == freeze.get("transport_payload_bytes")
        and run.get("upload_chunks") == math.ceil(freeze["transport_payload_bytes"] / controller.CHUNK_BYTES)
        and run.get("upload_payload_sha256") == freeze.get("transport_payload_sha256")
        and run.get("remote_progress", {}).get("uploaded") is True
        and run.get("remote_progress", {}).get("started") is True
    )

    releases = {}
    for role in ("http-controller", "http-watchdog"):
        release = load(RUN_DIR / ("HOST-AWAKE-RELEASED-" + role + ".json"))
        releases[role] = {**release, "pid_still_running": controller.windows_pid_running(release["pid"])}
    result["guard_releases"] = releases
    result["guards_exited"] = all(row.get("released") is True and row["pid_still_running"] is False for row in releases.values())
    result["watchdog"] = load(RUN_DIR / "WATCHDOG-RESULT.json")

    frozen_paths = (
        (Path(controller.__file__), "controller_sha256"), (Path(preflight.__file__), "preflight_sha256"),
        (controller.BOOTSTRAP_PATH, "bootstrap_sha256"), (controller.REMOTE_CODE_PATH, "remote_program_sha256"),
        (controller.MANIFEST_PATH, "manifest_sha256"), (controller.AUTHORIZATION_PATH, "authorization_sha256"),
        (controller.PROPOSAL_PATH, "proposal_sha256"), (controller.base.LOCK_PATH, "wheel_lock_sha256"),
    )
    result["frozen_transport_preserved"] = all(
        hashlib.sha256(path.read_bytes()).hexdigest() == freeze[field] for path, field in frozen_paths
    )
    controller.require_authorization()
    manifest = load(controller.MANIFEST_PATH)
    project = HERE.parents[5]
    result["approved_source_manifest_verified"] = len(manifest["files"]) == 37 and all(
        (project / row["source"]).stat().st_size == row["bytes"]
        and hashlib.sha256((project / row["source"]).read_bytes()).hexdigest() == row["sha256"]
        for row in manifest["files"]
    )
    result["evidence"] = evidence_check()
    result["failure_evidence_preserved"] = (
        run.get("error_type") == "RuntimeError"
        and run.get("error") == "remote workload reported failure"
        and run.get("evidence", {}).get("verified") is False
        and run.get("evidence", {}).get("validation", {}).get("source_unchanged") is True
        and result["evidence"]["p5_started"]
        and result["evidence"]["p5_summary_created"]
        and result["evidence"]["native_scout_started"]
        and result["evidence"]["native_summary_created"]
    )
    result["attempt_safely_reconciled"] = bool(
        result["create_requests_this_authorization"] == 1 and run.get("creation_http_status") == 201
        and run.get("creation_uncertain") is False and run.get("cleanup", {}).get("owned_pod_absent") is True
        and result["owned_pods_absent_verified"] and result["billing"]["response_reconciled"]
        and result["cost_within_caps"] and result["actual_resource_identity_verified"]
        and result["chunked_transport_verified"] and result["guards_exited"]
        and result["watchdog"].get("status") == "controller_cleanup_verified"
        and result["frozen_transport_preserved"] and result["approved_source_manifest_verified"]
        and result["evidence"]["primary_failure_confirmed"] and result["failure_evidence_preserved"]
    )
    result["workload_completed"] = False
    result["authorization_consumed"] = True
    output = HERE / ("HTTP-NATIVE-SCOUT-P5-FINAL-VERIFICATION-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json")
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
