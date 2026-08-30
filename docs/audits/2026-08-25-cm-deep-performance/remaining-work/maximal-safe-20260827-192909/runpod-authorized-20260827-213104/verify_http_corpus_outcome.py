"""Independent postflight and saved-evidence verification for the corpus/RSS study."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET
import zipfile

import http_corpus_preflight_v4 as preflight
import runpod_corpus_controller_v5 as controller

HERE = Path(__file__).resolve().parent
RUN = HERE / "http-corpus-execute-001"
EXPECTED_CORPORA = {"bx1", "b2", "epfl"}
EXPECTED_ROLES = {"calibration-corpus", "heldout-corpus"}
EXPECTED_REPRESENTATIONS = {"dense", "bigint", "words"}


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
    corpus = output / "corpus-memory"
    runtime = load(output / "RUNTIME.json")
    validation = load(output / "REMOTE-VALIDATION.json")
    summary = load(corpus / "summary.json")
    selection = load(corpus / "selection-manifest.json")
    oracles = load(corpus / "oracles.json")
    raw_text = (corpus / "raw.jsonl").read_text(encoding="utf-8")
    rss_text = (corpus / "rss-jobs.jsonl").read_text(encoding="utf-8")
    if not raw_text.endswith("\n"):
        raise ValueError("incomplete final raw row")
    if not rss_text.endswith("\n"):
        raise ValueError("incomplete final RSS row")
    rows = [json.loads(line) for line in raw_text.splitlines()]
    rss_jobs = [json.loads(line) for line in rss_text.splitlines()]
    junit = ET.parse(output / "focused.xml").getroot()
    counts = {key: sum(int(suite.get(key, "0")) for suite in junit.iter("testsuite"))
              for key in ("tests", "failures", "errors", "skipped")}
    calls = {(row["case_id"], row["representation"], row["schedule"], row["repetition"])
             for row in rows}
    cases = selection.get("cases", [])
    case_ids = {case["case_id"] for case in cases}
    expected_calls = {(case_id, representation, schedule, repetition)
                      for case_id in case_ids for representation in EXPECTED_REPRESENTATIONS
                      for schedule in ("cold", "warm") for repetition in range(3)}
    expected_jobs = {f"{case_id}-{representation}-cold-r{repetition}"
                     for case_id in case_ids for representation in EXPECTED_REPRESENTATIONS
                     for repetition in range(3)}
    expected_jobs.update(f"{case_id}-{representation}-warm"
                         for case_id in case_ids for representation in EXPECTED_REPRESENTATIONS)
    statuses = dict(Counter(row.get("status") for row in rows))
    hashes = defaultdict(set)
    for row in rows:
        hashes[row["case_id"]].add(row.get("output_sha256"))
    source_manifest = load(corpus / "source-manifest.json")
    snapshots_match = all(hashlib.sha256((corpus / "source_snapshot" / path).read_bytes()).hexdigest() == digest_value
                          for path, digest_value in source_manifest.items())
    dependencies = load(output / "DEPENDENCIES.json")
    installed = {name.lower().replace("_", "-"): version for name, version in dependencies.items()}
    locked = {row["name"].lower().replace("_", "-"): row["version"]
              for row in load(controller.base.LOCK_PATH)["packages"]}
    locked_versions_match = all(installed.get(name) == version for name, version in locked.items())
    truth_by_case = {case["case_id"]: case["truth_sha256"] for case in cases}
    oracle_exact = (set(oracles) == case_ids and all(
        oracle.get("frozen_truth_sha256") == truth_by_case[case_id]
        for case_id, oracle in oracles.items()))
    dead_axis = [case for case in cases if case["syntactic_k"] > case["k"]]
    dead_axis_verified = (len(dead_axis) == 1
        and oracles[dead_axis[0]["case_id"]]["live_output_sha256"]
            != oracles[dead_axis[0]["case_id"]]["frozen_truth_sha256"]
        and bool(oracles[dead_axis[0]["case_id"]].get("fixed")))
    rss_ids = {row.get("job_id") for row in rss_jobs}
    rss_complete = (rss_ids == expected_jobs and len(rss_jobs) == len(expected_jobs)
        and all(type(row.get("sample_count")) is int and row["sample_count"] > 0
                and type(row.get("sampled_rss_peak_bytes")) is int
                and type(row.get("kernel_hwm_peak_bytes_observed")) is int
                and row["sampled_rss_peak_bytes"] <= row["kernel_hwm_peak_bytes_observed"]
                and row.get("returncode") == 0 and row.get("timed_out") is False
                for row in rss_jobs))
    verified = (counts == {"tests": 79, "failures": 0, "errors": 0, "skipped": 0}
        and len(list(junit.iter("testcase"))) == 79
        and validation.get("status") == "complete"
        and runtime.get("runpod_pod_id") == record["pod_id"] and runtime.get("source_files") == 71
        and len(cases) == 35 and len(rows) == 630 and calls == expected_calls and statuses == {"ok": 630}
        and all(row.get("exact") is True for row in rows)
        and {row.get("corpus") for row in rows} == EXPECTED_CORPORA
        and {row.get("role") for row in rows} == EXPECTED_ROLES
        and {row.get("representation") for row in rows} == EXPECTED_REPRESENTATIONS
        and {row.get("schedule") for row in rows} == {"cold", "warm"}
        and all(row.get("output_sha256") == row.get("independent_oracle_sha256") for row in rows)
        and len(hashes) == 35 and all(len(values) == 1 and None not in values for values in hashes.values())
        and oracle_exact and dead_axis_verified and rss_complete
        and summary.get("rows") == len(rows) and summary.get("statuses") == statuses
        and summary.get("source_unchanged") is True and summary.get("production_estimator_accepted") is False
        and summary.get("calibration_performed") is False
        and summary.get("rss", {}).get("jobs_with_samples") == 420
        and summary.get("rss", {}).get("jobs_with_kernel_hwm") == 420
        and len(source_manifest) == 13 and snapshots_match and len(locked) == 13 and locked_versions_match)
    return {"verified": verified, "archive_sha256": digest, "archive_files": len(infos),
            "junit": counts, "raw_rows": len(rows), "jobs": len(rss_jobs), "calls": len(calls),
            "raw_statuses": statuses, "rss_complete": rss_complete,
            "all_rows_exact": all(row.get("exact") is True for row in rows),
            "case_hashes_consistent": all(len(values) == 1 for values in hashes.values()),
            "cases": len(hashes), "runtime_pod_id": runtime.get("runpod_pod_id"),
            "independent_oracles_verified": oracle_exact, "dead_axis_verified": dead_axis_verified,
            "source_unchanged": summary.get("source_unchanged"), "snapshot_files": len(source_manifest),
            "snapshot_hashes_match": snapshots_match, "locked_packages": len(locked),
            "locked_versions_match": locked_versions_match,
            "rss": summary.get("rss"),
            "production_estimator_accepted": summary.get("production_estimator_accepted"),
            "calibration_performed": summary.get("calibration_performed"),
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
                            (controller.BOOTSTRAP_PATH, "bootstrap_sha256"),
                            (controller.AUTHORIZATION_PATH, "authorization_sha256"),
                            (controller.PROPOSAL_PATH, "proposal_sha256")))
    controller.require_authorization()
    controller.base.make_bundle(load(controller.MANIFEST_PATH))
    result["approved_source_hashes_match"] = True
    result["prior_attempts_preserved"] = preflight.prior_attempts()
    result["estimated_compute_cost_usd"] = record.get("estimated_compute_cost_usd")
    result["campaign_cost_bound_usd"] = max(
        preflight.PRIOR_HTTP_RESERVE + result["estimated_compute_cost_usd"],
        result["billing_observed_campaign_cost_usd"],
    )
    result["evidence"] = evidence_check(record)
    result["complete"] = bool(record["status"] == "complete" and result["create_requests_this_authorization"] == 1
        and result["owned_pods_absent_verified"] and result["billing_reconciled"] and result["guards_exited"]
        and result["frozen_source_preserved"] and result["approved_source_hashes_match"]
        and result["evidence"]["verified"] and result["watchdog"].get("status") == "controller_cleanup_verified"
        and result["campaign_cost_bound_usd"] <= preflight.CAMPAIGN_CAP)
    output = HERE / ("HTTP-CORPUS-FINAL-VERIFICATION-" +
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
