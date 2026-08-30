"""Independent saved-evidence verifier for the successful exact-96 P7 scout."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


HERE = Path(__file__).resolve().parent
OUT = HERE / "p7-functional-scout-v6-exact96-001"
EVIDENCE = OUT / "evidence" / "run-output"
AUDIT = OUT / "INDEPENDENT-RESULT-AUDIT.json"
EXPECTED_ZIP_SHA256 = "df17e17cf5788a7985feae109afe120739ad64053297c975aa6e6a06fbccb519"
EXPECTED_BUNDLE_SHA256 = "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_policy(name: str, expected_cells: int, expected_arms: set[str]) -> dict:
    root = EVIDENCE / name
    plan = load(root / "plan.json")
    summary = load(root / "summary.json")
    verification_command = load(EVIDENCE / f"{name}-verify.json")
    verification = load(EVIDENCE / f"{name}-verify.stdout.txt")
    oracles = {row["case_id"]: row for row in load(root / "oracles.json")["cases"]}
    before = load(root / "source-before.json")
    after = load(root / "source-after.json")
    require(before == after, f"{name}: source snapshot changed")

    checksums = load(root / "checksums.json")
    for row in checksums["files"]:
        path = root / row["path"]
        require(path.stat().st_size == row["bytes"], f"{name}: byte count mismatch for {row['path']}")
        require(digest(path) == row["sha256"], f"{name}: checksum mismatch for {row['path']}")

    cells = plan["cells"]
    require(len(cells) == expected_cells, f"{name}: wrong planned-cell count")
    require({row["arm"] for row in cells} == expected_arms, f"{name}: wrong arm set")
    require({row["block"] for row in cells} == {0, 1}, f"{name}: wrong block set")
    require(all(row["lifecycle"] == "fresh_process" for row in cells), f"{name}: non-fresh lifecycle")
    planned_ids = {row["cell_id"] for row in cells}
    require(len(planned_ids) == expected_cells, f"{name}: duplicate planned cell")

    rows = [json.loads(line) for line in (root / "ledger/segment-000000.jsonl").read_text(
        encoding="utf-8"
    ).splitlines() if line]
    require(len(rows) == expected_cells * 2, f"{name}: unexpected ledger row count")
    running = [row for row in rows if row["status"] == "running"]
    terminal = [row for row in rows if row["status"] == "ok"]
    require(len(running) == len(terminal) == expected_cells, f"{name}: incomplete ledger")
    require({row["cell_id"] for row in running} == planned_ids, f"{name}: running-cell mismatch")
    require({row["cell_id"] for row in terminal} == planned_ids, f"{name}: terminal-cell mismatch")

    pids = []
    peak_rss = []
    for row in terminal:
        result = row["result"]
        worker = result["worker"]
        resources = result["resources"]
        oracle = oracles[worker["case_id"]]
        require(result["status"] == "ok" and worker["status"] == "ok", f"{name}: non-ok result")
        require(result["outside_span_validation"] is True, f"{name}: validation inside span")
        require(result["performance_measurement"] is False, f"{name}: performance flag set")
        require(worker["performance_measurement"] is False, f"{name}: worker performance flag set")
        require(worker["validation_in_timed_span"] is False, f"{name}: timed validation")
        require(worker["semantic_sha256"] == oracle["result_sha256"], f"{name}: oracle mismatch")
        require(resources["cleanup_verified"] is True, f"{name}: cleanup not verified")
        require(resources["streams_closed"] is True, f"{name}: streams not closed")
        require(resources["whole_tree_rss_measured"] is True, f"{name}: incomplete RSS measurement")
        require(result["process_tree_peak_rss_bytes"] > 0, f"{name}: missing RSS")
        require(result["timings_ns"]["task_total_wall_ns"] > 0, f"{name}: missing task span")
        pids.append(worker["environment"]["pid"])
        peak_rss.append(result["process_tree_peak_rss_bytes"])
    require(len(set(pids)) == expected_cells, f"{name}: worker process was reused")

    reconciliation = summary["reconciliation"]
    require(summary["status"] == "passed", f"{name}: summary did not pass")
    require(summary["performance_measurement"] is False, f"{name}: summary performance flag set")
    require(summary["performance_claim_permitted"] is False, f"{name}: performance claim permitted")
    require(reconciliation["complete"] is True, f"{name}: reconciliation incomplete")
    require(reconciliation["observed_cells"] == expected_cells, f"{name}: observed-cell mismatch")
    require(reconciliation["statuses"] == {"ok": expected_cells}, f"{name}: wrong statuses")
    require(verification_command["returncode"] == 0, f"{name}: verifier command failed")
    require(verification["verified"] is True and verification["status"] == "passed",
            f"{name}: verification did not pass")
    return {
        "planned_cells": expected_cells,
        "terminal_cells": len(terminal),
        "unique_worker_pids": len(set(pids)),
        "case_ids": sorted(oracles),
        "arms": sorted(expected_arms),
        "peak_rss_min_bytes": min(peak_rss),
        "peak_rss_max_bytes": max(peak_rss),
        "source_unchanged": True,
        "oracle_matches": len(terminal),
    }


def main() -> int:
    run = load(OUT / "RUN.json")
    require(run["status"] == "complete" and run["evidence"]["verified"] is True,
            "controller outcome is not complete and verified")
    require(run["pod_id"] == "6mlqn19hnco1b0", "unexpected pod identity")
    require(run["uploaded_source_files"] == 96, "wrong uploaded file count")
    require(run["cleanup"]["owned_pod_absent"] is True, "owned pod is not absent")
    require(run["cleanup"]["inventories"] == {"v1": [], "v2": []}, "nonempty cleanup inventory")
    require(run["estimated_compute_cost_usd"] < 0.10, "phase cost exceeds cap")

    resource = load(OUT / "POD-RESOURCE-CHECK.json")["pod"]
    require(resource["id"] == run["pod_id"] and resource["vcpuCount"] == 2, "pod CPU identity mismatch")
    require(resource["memoryInGb"] >= 4 and resource["costPerHr"] == 0.06, "pod RAM/rate mismatch")
    require(resource["containerDiskInGb"] == 12 and resource["volumeInGb"] == 0,
            "pod storage mismatch")
    require(resource["verified_v2_cloud"] == "SECURE", "pod cloud was not Secure")

    archive_path = OUT / "evidence.zip"
    require(digest(archive_path) == EXPECTED_ZIP_SHA256, "evidence ZIP checksum mismatch")
    extracted = {
        path.relative_to(OUT / "evidence").as_posix(): path
        for path in (OUT / "evidence").rglob("*") if path.is_file()
    }
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == 46, "unexpected or duplicate ZIP members")
        require(set(names) == set(extracted), "ZIP/extracted member mismatch")
        for name in names:
            require(not name.startswith(("/", "\\")) and ".." not in Path(name).parts,
                    "unsafe ZIP member")
            require(hashlib.sha256(archive.read(name)).hexdigest() == digest(extracted[name]),
                    f"ZIP/extracted byte mismatch: {name}")

    junit = ET.parse(EVIDENCE / "focused.xml").getroot()
    suites = [junit] if junit.tag == "testsuite" else list(junit.findall("testsuite"))
    testcase_count = sum(len(suite.findall("testcase")) for suite in suites)
    failures = sum(int(suite.get("failures", 0)) for suite in suites)
    errors = sum(int(suite.get("errors", 0)) for suite in suites)
    skipped = sum(int(suite.get("skipped", 0)) for suite in suites)
    require((testcase_count, failures, errors, skipped) == (42, 0, 0, 0), "focused JUnit mismatch")

    runtime = load(EVIDENCE / "RUNTIME.json")
    require(runtime["runpod_pod_id"] == run["pod_id"], "runtime pod mismatch")
    require(runtime["bundle_sha256"] == EXPECTED_BUNDLE_SHA256, "runtime bundle mismatch")
    require(runtime["source_files"] == 96 and len(runtime["affinity"]) == 2,
            "runtime source/affinity mismatch")

    policies = {
        "p7-ir": verify_policy("p7-ir", 16, {
            "cm-ir-current", "cm-ir-two-memo", "cm-cse-flat", "cm-raw-flat"
        }),
        "p7-relation": verify_policy("p7-relation", 20, {
            "cm-cse-flat", "cm-dense", "cm-no-reinflate", "cm-packed-bigint", "cm-packed-words"
        }),
    }
    all_pids = set()
    for name in policies:
        rows = [json.loads(line) for line in (EVIDENCE / name / "ledger/segment-000000.jsonl").read_text(
            encoding="utf-8"
        ).splitlines() if line]
        all_pids.update(row["result"]["worker"]["environment"]["pid"] for row in rows if row["status"] == "ok")
    require(len(all_pids) == 36, "worker PID reused across policies")

    result = {
        "schema": "cm-runpod-p7-functional-scout-v6-independent-audit/v1",
        "status": "passed",
        "run_sha256": digest(OUT / "RUN.json"),
        "evidence_zip_sha256": EXPECTED_ZIP_SHA256,
        "pod_id": run["pod_id"],
        "focused_tests": {"tests": testcase_count, "failures": failures, "errors": errors, "skipped": skipped},
        "policies": policies,
        "total_cells": 36,
        "unique_worker_pids": len(all_pids),
        "source_unchanged": True,
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "owned_pod_absent": True,
        "inventories_at_cleanup": {"v1": [], "v2": []},
        "runtime_affinity": runtime["affinity"],
        "host_visible_logical_cpus": runtime["logical_cpus_host_visible"],
    }
    temporary = AUDIT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, AUDIT)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
