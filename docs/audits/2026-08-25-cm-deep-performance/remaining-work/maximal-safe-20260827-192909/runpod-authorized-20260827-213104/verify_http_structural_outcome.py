"""Independent postflight and bounded saved-evidence verification for the structural study."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET
import zipfile

import http_structural_preflight_v3 as preflight
import runpod_structural_controller_v4 as controller

HERE = Path(__file__).resolve().parent
RUN = HERE / "http-structural-execute-001"
EXPECTED_FAMILIES = {"mixed-chain", "shared-diamond", "wide-and", "alternating-tree", "reconvergent-xor"}
EXPECTED_K = {6, 8, 12, 16}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_check(record):
    archive = RUN / "evidence.zip"
    if not record.get("evidence") or archive.stat().st_size > controller.CAP:
        raise ValueError("controller did not accept bounded complete evidence")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != record["evidence"]["sha256"]:
        raise ValueError("saved archive hash differs")
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        if (len({row.filename for row in infos}) != len(infos)
            or sum(row.file_size for row in infos) + archive.stat().st_size > controller.CAP):
            raise ValueError("duplicate or excessive archived evidence")
        for info in infos:
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError("unsafe archive member")
            target = (RUN / "evidence" / pure).resolve()
            target.relative_to((RUN / "evidence").resolve())
            if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(bundle.read(info)).digest():
                raise ValueError("extracted member differs from archive")
    output = RUN / "evidence/run-output"
    structural = output / "structural"
    runtime = load(output / "RUNTIME.json")
    validation = load(output / "REMOTE-VALIDATION.json")
    summary = load(structural / "summary.json")
    jobs = load(structural / "jobs.json")
    raw_text = (structural / "raw.jsonl").read_text(encoding="utf-8")
    if not raw_text.endswith("\n"):
        raise ValueError("incomplete final raw row")
    rows = [json.loads(line) for line in raw_text.splitlines()]
    junit = ET.parse(output / "focused.xml").getroot()
    counts = {key: sum(int(suite.get(key, "0")) for suite in junit.iter("testsuite"))
              for key in ("tests", "failures", "errors", "skipped")}
    calls = {(row["case_id"], row["representation"], row["schedule"], row["repetition"])
             for row in rows}
    statuses = dict(Counter(row.get("status") for row in rows))
    schedules = Counter(job.get("schedule") for job in jobs)
    hashes = defaultdict(set)
    for row in rows:
        hashes[row["case_id"]].add(row.get("output_sha256"))
    source_manifest = load(structural / "source-manifest.json")
    snapshots_match = all(hashlib.sha256((structural / "source_snapshot" / path).read_bytes()).hexdigest() == digest_value
                          for path, digest_value in source_manifest.items())
    dependencies = load(output / "DEPENDENCIES.json")
    installed = {name.lower().replace("_", "-"): version for name, version in dependencies.items()}
    locked = {row["name"].lower().replace("_", "-"): row["version"]
              for row in load(controller.base.LOCK_PATH)["packages"]}
    locked_versions_match = all(installed.get(name) == version for name, version in locked.items())
    policy_decisions = sum(row["rows"] for row in summary["policy_counts"])
    verified = (counts == {"tests": 70, "failures": 0, "errors": 0, "skipped": 0}
        and len(list(junit.iter("testcase"))) == 70
        and validation.get("status") == "complete"
        and runtime.get("runpod_pod_id") == record["pod_id"] and runtime.get("source_files") == 65
        and len(jobs) == 240 and schedules == {"cold": 180, "warm": 60}
        and len(rows) == 1560 and len(calls) == 360 and statuses == {"ok": 1560}
        and all(row.get("exact") is True for row in rows)
        and {row.get("k") for row in rows} == EXPECTED_K
        and {row.get("family") for row in rows} == EXPECTED_FAMILIES
        and {row.get("schedule") for row in rows} == {"cold", "warm"}
        and {row.get("context") for row in rows} == {"none"}
        and len(hashes) == 20 and all(len(values) == 1 and None not in values for values in hashes.values())
        and summary.get("rows") == len(rows) and summary.get("statuses") == statuses
        and summary.get("source_unchanged") is True and summary.get("production_estimator_accepted") is False
        and len(source_manifest) == 19 and snapshots_match and len(locked) == 13 and locked_versions_match)
    return {"verified": verified, "archive_sha256": digest, "archive_files": len(infos),
            "junit": counts, "raw_rows": len(rows), "jobs": len(jobs), "calls": len(calls),
            "job_schedules": dict(schedules), "raw_statuses": statuses,
            "all_rows_exact": all(row.get("exact") is True for row in rows),
            "case_hashes_consistent": all(len(values) == 1 for values in hashes.values()),
            "cases": len(hashes), "runtime_pod_id": runtime.get("runpod_pod_id"),
            "source_unchanged": summary.get("source_unchanged"), "snapshot_files": len(source_manifest),
            "snapshot_hashes_match": snapshots_match, "locked_packages": len(locked),
            "locked_versions_match": locked_versions_match, "policy_decisions": policy_decisions,
            "production_estimator_accepted": summary.get("production_estimator_accepted"),
            "real_workload_compatibility": summary.get("real_workload_compatibility")}


def main():
    record = load(RUN / "RUN.json")
    pod_id = record.get("pod_id")
    known = set(preflight.PRIOR_POD_IDS) | ({pod_id} if pod_id else set())
    result = {"checked_utc": preflight.utc_now(), "resource_writes": 0,
              "create_requests_this_authorization": int(record["creation_attempted"]),
              "controller_status": record["status"], "pod_id": pod_id,
              "source_files_uploaded": record["uploaded_source_files"], "automatic_replacement_queued": False}
    with preflight.session() as client:
        checks = {}
        for version, endpoint in (("v1", preflight.V1), ("v2", preflight.V2)):
            details = {}
            for identity in sorted(known):
                response = client.get(endpoint + "/pods/" + identity, timeout=10, allow_redirects=False)
                details[identity] = response.status_code
            checks[version] = {"details_http_status": details, "inventory": preflight.inventory(client, endpoint)}
        result["checks"] = checks
        result["owned_pods_absent_verified"] = all(not row["inventory"]
            and all(status == 404 for status in row["details_http_status"].values()) for row in checks.values())
        params = {"startTime": "2026-08-27T00:00:00Z", "endTime": preflight.utc_now(),
                  "bucketSize": "day", "grouping": "podId"}
        response = client.get(preflight.V2 + "/billing/pods", params=params, timeout=15, allow_redirects=False)
        response.raise_for_status()
        body = response.json()
        billing = preflight.analyze_billing(body["metadata"], body["records"])
        all_rows = billing["attributed_rows"] + billing["unrelated_account_rows"]
        result["billing_metadata"] = billing["metadata"]
        result["billing_campaign_rows"] = [row for row in all_rows if row["podId"] in known]
        result["billing_unrelated_account_rows"] = [row for row in all_rows if row["podId"] not in known]
        result["billing_observed_campaign_cost_usd"] = sum(row["amount"] for row in result["billing_campaign_rows"])
        result["billing_reconciled"] = True
        result["billing_may_lag"] = True
    releases = {}
    for role in ("http-controller", "http-watchdog"):
        path = RUN / ("HOST-AWAKE-RELEASED-" + role + ".json")
        release = load(path) if path.exists() else {"released": False}
        releases[role] = {**release, "pid_still_running": controller.windows_pid_running(release["pid"])} \
                         if release.get("released") is True else release
    result["guard_releases"] = releases
    result["guards_exited"] = all(row.get("released") is True and row.get("pid_still_running") is False
                                  for row in releases.values())
    result["watchdog"] = load(RUN / "WATCHDOG-RESULT.json")
    freeze = load(RUN / "TRANSPORT-FREEZE.json")
    result["frozen_source_preserved"] = all(hashlib.sha256(path.read_bytes()).hexdigest() == freeze[field]
        for path, field in ((Path(controller.__file__), "controller_sha256"),
                            (Path(preflight.__file__), "preflight_sha256"),
                            (controller.BOOTSTRAP_PATH, "bootstrap_sha256")))
    controller.base.make_bundle(load(controller.base.MANIFEST_PATH))
    result["approved_source_hashes_match"] = True
    result["prior_attempts_preserved"] = preflight.prior_attempts()
    result["estimated_compute_cost_usd"] = record.get("estimated_compute_cost_usd")
    result["campaign_cost_bound_usd"] = preflight.PRIOR_HTTP_RESERVE + result["estimated_compute_cost_usd"]
    result["evidence"] = evidence_check(record)
    result["complete"] = bool(record["status"] == "complete" and result["create_requests_this_authorization"] == 1
        and result["owned_pods_absent_verified"] and result["billing_reconciled"] and result["guards_exited"]
        and result["frozen_source_preserved"] and result["approved_source_hashes_match"]
        and result["evidence"]["verified"] and result["watchdog"].get("status") == "controller_cleanup_verified"
        and result["campaign_cost_bound_usd"] <= preflight.CAMPAIGN_CAP)
    output = HERE / ("HTTP-STRUCTURAL-FINAL-VERIFICATION-" +
        datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json")
    controller.write(output, result)
    print(json.dumps(result, indent=2))
    print("evidence_file=" + str(output))
    return int(not result["complete"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}))
        raise SystemExit(2)
