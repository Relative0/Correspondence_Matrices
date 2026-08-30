"""Read-only safety/evidence reconciliation for external native-gap V14-V20."""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET
import zipfile

import verify_external_native_gap_v13_outcome as prior


HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "native-gap-v20-001"
POD_ID = "rg3zlg5gbdbp5p"
PREVIOUS_FINAL = HERE / "EXTERNAL-NATIVE-GAP-V13-FINAL-VERIFICATION-20260829-162224-598946.json"
INTERMEDIATE = {version: HERE / f"native-gap-v{version}-001" for version in range(14, 21)}
CREATED_VERSIONS = (15, 16, 17, 19, 20)
LOCAL_ONLY_VERSIONS = (14, 18)
AUTHORIZATION = HERE / "HTTP-NATIVE-GAP-CAMPAIGN-V20-AUTHORIZED-20260829.json"
PROPOSAL = HERE / "RUNPOD-NATIVE-GAP-CAMPAIGN-V20-D4V2-BARE-COMMENT-PROPOSAL-20260829.md"
CONTROLLER = HERE / "runpod_native_gap_controller_v20.py"
PREFLIGHT = HERE / "http_native_gap_preflight_v20.py"
MANIFEST = HERE / "RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V14-20260829.json"
BOOTSTRAP = HERE / "http_native_scout_bootstrap_v2.py"
REMOTE = HERE / "runpod_native_scout_remote_v4.py"
WHEEL_LOCK = HERE.parent / "RUNPOD-WHEEL-LOCK.json"
PHASE_CAP_USD = 0.10
CAMPAIGN_CAP_USD = 0.20
STORAGE_RATE_RESERVE = 0.01


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def guard_release(run_dir, role):
    release = load(run_dir / ("HOST-AWAKE-RELEASED-" + role + ".json"))
    current_running = prior.prior.safe_controller.windows_pid_running(release["pid"])
    created = prior.prior.windows_process_created_utc(release["pid"]) if current_running else None
    released = datetime.fromisoformat(release["released_utc"])
    reused = created is not None and created > released
    return {
        **release,
        "current_pid_occupant_running": current_running,
        "current_pid_occupant_created_utc": created.isoformat() if created is not None else None,
        "pid_reused_after_release": reused,
        "original_process_still_running": current_running and not reused,
    }


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
        raise ValueError("retrieved V20 evidence differs from remote markers")
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
                raise ValueError("extracted evidence differs from V20 archive")
    output = extracted / "run-output"
    validation = load(output / "REMOTE-VALIDATION.json")
    runtime = load(output / "RUNTIME.json")
    focused = load(output / "focused-tests.json")
    p5 = load(output / "p5-smoke.json")
    p5_verify = load(output / "p5-smoke-verify.json")
    p5_summary = load(output / "p5-smoke/summary.json")
    native = load(output / "native-scout.json")
    summary = load(output / "native-scout/summary.json")
    environment = load(output / "native-scout/environment.json")
    dependencies = load(output / "native-scout/dependencies.json")
    controls = load(output / "native-scout/linux-controls.json")
    cadical = load(output / "native-scout/cadical.json")
    cudd = load(output / "native-scout/cudd.json")
    d4 = load(output / "native-scout/d4.json")
    perf = load(output / "native-scout/perf.json")
    before = load(output / "SOURCE-BEFORE.json")
    after = load(output / "SOURCE-AFTER.json")
    manifest = load(MANIFEST)
    expected_source = [
        {"target": row["target"], "bytes": row["bytes"], "sha256": row["sha256"]}
        for row in manifest["files"]
    ]
    root = ET.parse(output / "focused.xml").getroot()
    suites = list(root.iter("testsuite"))
    metadata = {
        key: sum(int(suite.get(key, "0")) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    cases = list(root.iter("testcase"))
    outcomes = {
        "failures": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
        "skipped": sum(case.find("skipped") is not None for case in cases),
    }
    expected_versions = {
        "astutils": "0.0.6", "dd": "0.6.0", "networkx": "3.6.1",
        "ply": "3.10", "python-sat": "1.9.dev15", "setuptools": "84.0.0",
        "six": "1.17.0", "wheel": "0.48.0",
    }
    control_statuses = {name: row.get("status") for name, row in controls.items()}
    control_cleanup = all(
        row.get("resources", {}).get("cleanup_verified") is True
        and row.get("resources", {}).get("streams_closed") is True
        and row.get("resources", {}).get("whole_tree_rss_measured") is True
        for row in controls.values()
    )
    d4_expected = {
        "true-k1": 2, "false-k1": 0, "all-k3": 8, "unused-k3": 4, "conflict-k2": 0,
    }
    d4_cases = {row.get("case"): row for row in d4.get("cases", [])}
    d4_exact = set(d4_cases) == set(d4_expected) and all(
        row.get("expected") == d4_expected[name]
        and row.get("parsed", {}).get("count") == d4_expected[name]
        and row.get("parsed", {}).get("task") == "exact_count"
        and row.get("parsed", {}).get("lifecycle") == "cold_cli_including_process_start"
        and row.get("parsed", {}).get("output_contract") == "d4v2_competition_exact_integer"
        and row.get("supervision", {}).get("cleanup_verified") is True
        and row.get("supervision", {}).get("whole_tree_rss_measured") is True
        for name, row in d4_cases.items()
    )
    cadical_supervision = cadical.get("supervision", {})
    cudd_supervision = cudd.get("supervision", {})
    completed = (
        validation.get("status") == "complete"
        and validation.get("error") is None
        and validation.get("validation_errors") == []
        and validation.get("native_summary") == {
            "cadical": "passed", "cudd": "passed", "d4": "passed",
            "dependencies": "passed", "linux_controls": "passed", "native_failures": 0,
            "perf": "unavailable", "performance_measurement": False,
            "performance_ranking_permitted": False, "semantic_mismatches": 0,
            "status": "passed",
        }
        and focused.get("returncode") == 0
        and len(cases) == 68
        and outcomes == {"failures": 0, "errors": 0, "skipped": 0}
        and metadata == {"tests": 192, "failures": 0, "errors": 0, "skipped": 0}
        and p5.get("returncode") == 0
        and p5_verify.get("returncode") == 0
        and p5_summary.get("status") == "passed"
        and p5_summary.get("planned_cells") == 144
        and p5_summary.get("reconciliation", {}).get("observed_cells") == 144
        and p5_summary.get("reconciliation", {}).get("statuses") == {"ok": 144}
        and native.get("returncode") == 0
        and summary.get("status") == "passed"
        and summary.get("cadical") == summary.get("cudd") == summary.get("d4") == "passed"
        and summary.get("perf") == "unavailable"
        and summary.get("native_failures") == summary.get("semantic_mismatches") == 0
        and summary.get("performance_measurement") is False
        and summary.get("performance_ranking_permitted") is False
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
        and cudd.get("worker", {}).get("status") == "passed"
        and cudd.get("worker", {}).get("native_execution") is True
        and cudd.get("worker", {}).get("cases") == 4
        and cudd.get("worker", {}).get("dump_reload_exact") is True
        and cudd_supervision.get("cleanup_verified") is True
        and cudd_supervision.get("whole_tree_rss_measured") is True
        and d4.get("status") == "passed"
        and d4.get("native_execution") is True
        and d4.get("identity") == {
            "bytes": 5054920, "file": "d4",
            "sha256": "29cb30f351ed92b02343e5e7a98b082e949d9838245f37c0bcdecf68a57ffd39",
            "status": "identified",
        }
        and d4.get("elf", {}).get("linkage", {}).get("linkage") == "static"
        and d4.get("elf", {}).get("dependency_check", {}).get("status") == "not_applicable_static"
        and d4_exact
        and perf == {"reason": "perf_not_installed", "status": "unavailable"}
        and environment.get("cpu", {}).get("allocated_logical_from_affinity") == 2
        and before == after == expected_source
        and runtime.get("runpod_pod_id") == POD_ID
        and runtime.get("source_files") == 37
    )
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
        "junit_case_outcomes": outcomes,
        "p5_status": p5_summary.get("status"),
        "p5_cells": p5_summary.get("reconciliation", {}).get("observed_cells"),
        "native_summary": summary,
        "native_dependency_versions": dependencies.get("versions"),
        "native_control_statuses": control_statuses,
        "native_control_cleanup_verified": control_cleanup,
        "cadical_status": cadical.get("worker", {}).get("status"),
        "cadical_cases": cadical.get("worker", {}).get("cases"),
        "cudd_status": cudd.get("worker", {}).get("status"),
        "cudd_cases": cudd.get("worker", {}).get("cases"),
        "cudd_dump_reload_exact": cudd.get("worker", {}).get("dump_reload_exact"),
        "d4_status": d4.get("status"),
        "d4_cases": {name: row.get("parsed", {}).get("count") for name, row in d4_cases.items()},
        "d4_identity": d4.get("identity"),
        "d4_static_linkage": d4.get("elf", {}).get("linkage", {}).get("linkage"),
        "perf": perf,
        "source_unchanged": before == after == expected_source,
        "readiness_completed": completed,
        "performance_measurement": False,
        "performance_ranking_permitted": False,
    }


def main():
    previous = load(PREVIOUS_FINAL)
    runs = {version: load(path / "RUN.json") for version, path in INTERMEDIATE.items()}
    result = {
        "checked_utc": prior.prior.api.utc_now(),
        "resource_writes": 0,
        "concurrent_launches_not_owned_by_this_task": True,
        "automatic_replacement_queued_by_this_task": False,
        "created_versions": list(CREATED_VERSIONS),
        "local_only_versions": list(LOCAL_ONLY_VERSIONS),
    }
    known = set(previous["checks"]["v1"]["details_http_status"])
    known.update(runs[version]["pod_id"] for version in CREATED_VERSIONS)
    with prior.prior.api.session() as client:
        checks = {}
        for version, endpoint in (("v1", prior.prior.api.V1), ("v2", prior.prior.api.V2)):
            details = {}
            for pod_id in sorted(known):
                response = client.get(endpoint + "/pods/" + pod_id, timeout=10, allow_redirects=False)
                details[pod_id] = response.status_code
            checks[version] = {"details_http_status": details, "inventory": prior.prior.api.inventory(client, endpoint)}
        result["checks"] = checks
        result["all_known_pods_absent_verified"] = all(
            not row["inventory"] and all(status == 404 for status in row["details_http_status"].values())
            for row in checks.values()
        )
        billing = prior.prior.api.billing_check(client)
    historical = billing["historical_account_rows"]
    attempt_costs = {}
    for version in CREATED_VERSIONS:
        run = runs[version]
        pod_id = run["pod_id"]
        observed = sum(row["amount"] for row in historical if row["podId"] == pod_id)
        elapsed_bound = (float(run["quoted_rate_usd_per_hour"]) + STORAGE_RATE_RESERVE) * float(run["elapsed_since_create_s"]) / 3600
        attempt_costs[str(version)] = {
            "pod_id": pod_id,
            "observed_cost_usd": observed,
            "elapsed_rate_bound_usd": elapsed_bound,
            "attributable_bound_usd": max(observed, elapsed_bound),
        }
    corrected = float(previous["corrected_attributable_campaign_bound_usd"]) + sum(
        row["attributable_bound_usd"] for row in attempt_costs.values()
    )
    result["billing"] = {
        "metadata": billing["metadata"], "account_total_usd": billing["historical_total_usd"],
        "attempts": attempt_costs, "may_lag": True,
    }
    result["correct_prior_campaign_bound_usd"] = previous["corrected_attributable_campaign_bound_usd"]
    result["corrected_attributable_campaign_bound_usd"] = corrected
    result["cost_within_user_caps"] = (
        all(row["attributable_bound_usd"] <= PHASE_CAP_USD for row in attempt_costs.values())
        and corrected <= CAMPAIGN_CAP_USD
    )
    result["local_only_attempts_made_no_create"] = all(
        runs[version].get("creation_attempted") is False and runs[version].get("pod_id") is None
        for version in LOCAL_ONLY_VERSIONS
    )
    cleanup = {}
    for version in CREATED_VERSIONS:
        run = runs[version]
        run_dir = INTERMEDIATE[version]
        releases = {role: guard_release(run_dir, role) for role in ("http-controller", "http-watchdog")}
        watchdog = load(run_dir / "WATCHDOG-RESULT.json")
        cleanup[str(version)] = {
            "creation_http_status": run.get("creation_http_status"),
            "creation_uncertain": run.get("creation_uncertain"),
            "owned_pod_absent": run.get("cleanup", {}).get("owned_pod_absent"),
            "watchdog_status": watchdog.get("status"),
            "guards": releases,
            "verified": (
                run.get("creation_http_status") == 201
                and run.get("creation_uncertain") is False
                and run.get("cleanup", {}).get("owned_pod_absent") is True
                and watchdog.get("status") == "controller_cleanup_verified"
                and all(row.get("released") is True and row["original_process_still_running"] is False for row in releases.values())
            ),
        }
    result["attempt_cleanup"] = cleanup
    result["all_created_attempts_cleaned"] = all(row["verified"] for row in cleanup.values())
    run = runs[20]
    resource = load(RUN_DIR / "POD-RESOURCE-CHECK.json")
    freeze = load(RUN_DIR / "TRANSPORT-FREEZE.json")
    pod = resource["pod"]
    result["actual_resource_identity_verified"] = (
        pod.get("id") == POD_ID and pod.get("name") == run.get("name")
        and pod.get("verified_v2_cloud") == "SECURE" and pod.get("cpuFlavorId") == "cpu3c"
        and pod.get("vcpuCount") == 2 and float(pod.get("memoryInGb")) >= 4
        and float(pod.get("costPerHr")) == 0.06
        and pod.get("imageName") == prior.prior.safe_controller.base.IMAGE
        and pod.get("containerDiskInGb") == 12
        and type(pod.get("volumeInGb")) is int and pod.get("volumeInGb") == 0
        and sorted(pod.get("ports")) == sorted(prior.prior.safe_controller.EXPECTED_PORTS)
        and resource.get("network_volume_present") is False
    )
    result["chunked_transport_verified"] = (
        run.get("uploaded_source_files") == 37
        and run.get("uploaded_transport_bytes") == freeze.get("transport_payload_bytes")
        and run.get("upload_chunks") == math.ceil(freeze["transport_payload_bytes"] / prior.prior.safe_controller.CHUNK_BYTES)
        and run.get("upload_payload_sha256") == freeze.get("transport_payload_sha256")
        and run.get("remote_progress", {}).get("uploaded") is True
        and run.get("remote_progress", {}).get("started") is True
        and run.get("remote_progress", {}).get("done") is True
    )
    frozen_paths = (
        (CONTROLLER, "controller_sha256"), (PREFLIGHT, "preflight_sha256"),
        (BOOTSTRAP, "bootstrap_sha256"), (REMOTE, "remote_program_sha256"),
        (MANIFEST, "manifest_sha256"), (AUTHORIZATION, "authorization_sha256"),
        (PROPOSAL, "proposal_sha256"), (WHEEL_LOCK, "wheel_lock_sha256"),
    )
    result["frozen_transport_preserved"] = all(
        hashlib.sha256(path.read_bytes()).hexdigest() == freeze[field] for path, field in frozen_paths
    )
    result["evidence"] = evidence_check()
    authorization = load(AUTHORIZATION)
    result["authorization_scope"] = {
        "recorded_campaign_cap_usd": authorization.get("campaign_cap_usd"),
        "user_campaign_cap_usd": CAMPAIGN_CAP_USD,
        "record_has_no_replacement": authorization.get("no_replacement") is True,
        "record_text": authorization.get("authorization_basis"),
        "claims_separate_newer_cross_task_authority": True,
        "cross_task_authority_verifiable_from_this_task": False,
    }
    result["authorization_compliant"] = None
    result["campaign_safely_reconciled"] = bool(
        result["all_known_pods_absent_verified"]
        and result["cost_within_user_caps"]
        and result["local_only_attempts_made_no_create"]
        and result["all_created_attempts_cleaned"]
        and result["actual_resource_identity_verified"]
        and result["chunked_transport_verified"]
        and result["frozen_transport_preserved"]
        and result["evidence"]["source_unchanged"]
        and result["evidence"]["readiness_completed"]
    )
    result["native_readiness_completed"] = result["evidence"]["readiness_completed"]
    result["performance_measurement"] = False
    result["no_further_create_authorized_by_this_task"] = True
    output = HERE / (
        "EXTERNAL-NATIVE-GAP-V20-FINAL-VERIFICATION-"
        + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json"
    )
    prior.prior.safe_controller.write(output, result)
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(output))
    return int(not result["campaign_safely_reconciled"])


if __name__ == "__main__":
    raise SystemExit(main())
