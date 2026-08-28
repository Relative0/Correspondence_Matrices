"""Independent read-only postflight and bounded saved-evidence verification."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET
import zipfile

import http_transport_preflight_v2 as preflight
import runpod_http_smoke_controller_v3 as controller

HERE = Path(__file__).resolve().parent
RUN = HERE / "http-ephemeral-execute-001"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_check(record):
    if not record.get("evidence"):
        return {"verified": False, "reason": "controller did not accept complete evidence"}
    archive = RUN / "evidence.zip"
    if archive.stat().st_size > controller.CAP:
        raise ValueError("saved archive exceeds cap")
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
    runtime = load(output / "RUNTIME.json")
    summary = load(output / "memory/summary.json")
    raw_text = (output / "memory/raw.jsonl").read_text(encoding="utf-8")
    if not raw_text.endswith("\n"):
        raise ValueError("incomplete final raw row")
    rows = [json.loads(line) for line in raw_text.splitlines()]
    junit = ET.parse(output / "focused.xml").getroot()
    counts = {key: sum(int(suite.get(key, "0")) for suite in junit.iter("testsuite"))
              for key in ("tests", "failures", "errors", "skipped")}
    calls = len({(row.get("job_index"), row.get("repetition")) for row in rows})
    statuses = dict(Counter(row.get("status") for row in rows))
    verified = (counts == {"tests": 70, "failures": 0, "errors": 0, "skipped": 0}
        and len(list(junit.iter("testcase"))) == 70
        and runtime.get("runpod_pod_id") == record["pod_id"] and runtime.get("source_files") == 65
        and len(rows) == 312 and calls == 72 and statuses == {"ok": 312}
        and all(row.get("exact") is True for row in rows)
        and {row.get("k") for row in rows} == {6, 8}
        and {row.get("family") for row in rows} == {"mixed-chain", "alternating-tree"}
        and {row.get("schedule") for row in rows} == {"cold", "warm"}
        and {row.get("context") for row in rows} == {"none"}
        and summary.get("rows") == len(rows) and summary.get("statuses") == statuses
        and summary.get("source_unchanged") is True and summary.get("production_estimator_accepted") is False)
    return {"verified": verified, "archive_sha256": digest, "archive_files": len(infos),
            "junit": counts, "raw_rows": len(rows), "recorded_representation_calls": calls,
            "raw_statuses": statuses, "all_rows_exact": all(row.get("exact") is True for row in rows),
            "runtime_pod_id": runtime.get("runpod_pod_id"), "source_unchanged": summary.get("source_unchanged"),
            "production_estimator_accepted": summary.get("production_estimator_accepted"),
            "real_workload_compatibility": summary.get("real_workload_compatibility")}


def main():
    record = load(RUN / "RUN.json")
    pod_id = record.get("pod_id")
    known = {preflight.PRIOR_POD_ID} | ({pod_id} if pod_id else set())
    result = {"checked_utc": preflight.utc_now(), "resource_writes": 0,
              "create_requests_this_amendment": int(record["creation_attempted"]),
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
        metadata = response.json()["metadata"]
        result["billing_metadata"] = {key: metadata.get(key) for key in ("query", "recordCount", "uniquePodCount", "totals")}
        detail = []
        if metadata.get("recordCount") != 0:
            response = client.get(preflight.V1 + "/billing/pods", params=params, timeout=15, allow_redirects=False)
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, list) or len(body) > 10000:
                raise ValueError("unbounded or invalid billing detail")
            detail = [{"podId": row.get("podId"), "amount": preflight.amount(row["amount"]), "time": row.get("time")}
                      for row in body]
        total = preflight.amount(metadata["totals"]["totalAmount"])
        result["billing_attributed_rows"] = detail
        result["billing_reconciled"] = (metadata["recordCount"] == len(detail)
            and metadata["uniquePodCount"] == len({row["podId"] for row in detail})
            and all(row["podId"] in known for row in detail)
            and math.isclose(sum(row["amount"] for row in detail), total, rel_tol=0, abs_tol=1e-9))
        result["billing_may_lag"] = True
    releases = {}
    for role in ("http-controller", "http-watchdog"):
        path = RUN / ("HOST-AWAKE-RELEASED-" + role + ".json")
        if path.exists():
            release = load(path)
            releases[role] = {**release, "pid_still_running": controller.windows_pid_running(release["pid"])}
        else:
            releases[role] = {"released": False}
    result["guard_releases"] = releases
    result["guards_exited"] = all(row.get("released") is True and row.get("pid_still_running") is False for row in releases.values())
    watchdog_path = RUN / "WATCHDOG-RESULT.json"
    result["watchdog"] = load(watchdog_path) if watchdog_path.exists() else {"status": "pending"}
    if (RUN / "TRANSPORT-FREEZE.json").exists():
        freeze = load(RUN / "TRANSPORT-FREEZE.json")
        result["frozen_source_preserved"] = all(hashlib.sha256(path.read_bytes()).hexdigest() == freeze[field]
            for path, field in ((Path(controller.__file__), "controller_sha256"),
                                (Path(preflight.__file__), "preflight_sha256"),
                                (controller.BOOTSTRAP_PATH, "bootstrap_sha256")))
    controller.base.make_bundle(load(controller.base.MANIFEST_PATH))
    result["approved_source_hashes_match"] = True
    result["prior_attempt_preserved"] = preflight.prior_attempt()
    result["estimated_compute_cost_usd"] = record.get("estimated_compute_cost_usd")
    result["evidence"] = evidence_check(record)
    result["complete"] = bool(record["status"] == "complete" and result["owned_pods_absent_verified"]
        and result["billing_reconciled"] and result["guards_exited"] and result.get("frozen_source_preserved")
        and result["evidence"]["verified"] and result["watchdog"].get("status") == "controller_cleanup_verified")
    output = HERE / ("HTTP-EPHEMERAL-FINAL-VERIFICATION-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json")
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
