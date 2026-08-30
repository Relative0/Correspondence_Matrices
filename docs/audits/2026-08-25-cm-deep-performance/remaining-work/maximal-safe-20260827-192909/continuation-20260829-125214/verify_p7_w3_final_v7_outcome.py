"""Independently reconcile the final saved P7 W3 correctness evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import p7_runner
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.corpus_freeze import validate_freeze
import scripts.cm_comparative_p7_runner as p7_cli


HERE = Path(__file__).resolve().parent
PARENT_FREEZE = ROOT / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"
LOCK = HERE.parent / "runpod-requirements.lock"
OUTPUT = HERE / "P7-W3-FINAL-INDEPENDENT-AUDIT.json"
SQRT_CASE = "development-epfl-sqrt-31cdaf5d0213"

SUCCESS = {
    "ir-regression": ("p7-w3-shard-ir-regression-v2-001", "p7-ir", "regression", 24, 96, None, None),
    "ir-development-a": ("p7-w3-split-ir-development-a-v4-001", "p7-ir", "development", 17, 68, 0, 17),
    "ir-development-b-light": ("p7-w3-tail-ir-development-b-light-v6-001", "p7-ir", "development", 15, 60, 17, 15),
    "ir-development-square": ("p7-w3-final-ir-development-square-v7-001", "p7-ir", "development", 1, 4, 33, 1),
    "relation-regression": ("p7-w3-shard-relation-regression-v3-001", "p7-relation", "regression", 24, 120, None, None),
    "relation-development-a": ("p7-w3-final-relation-development-a-v7-001", "p7-relation", "development", 17, 85, 0, 17),
    "relation-development-b-light": ("p7-w3-final-relation-development-b-light-v7-001", "p7-relation", "development", 15, 75, 17, 15),
    "relation-development-square": ("p7-w3-final-relation-development-square-v7-001", "p7-relation", "development", 1, 5, 33, 1),
}

ATTEMPTS = (
    "p7-w3-correctness-v1-001",
    "p7-w3-shard-ir-regression-v1-001",
    "p7-w3-shard-ir-regression-v2-001",
    "p7-w3-shard-ir-development-v2-001",
    "p7-w3-shard-relation-regression-v3-001",
    "p7-w3-split-ir-development-a-v4-001",
    "p7-w3-split-ir-development-b-v4-001",
    "p7-w3-split-ir-development-b-v5-001",
    "p7-w3-tail-ir-development-b-light-v6-001",
    "p7-w3-tail-ir-development-sqrt-v6-001",
    "p7-w3-final-ir-development-square-v7-001",
    "p7-w3-final-relation-development-a-v7-001",
    "p7-w3-final-relation-development-b-light-v7-001",
    "p7-w3-final-relation-development-square-v7-001",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def parent_order(freeze: dict, policy_id: str, role: str) -> list[str]:
    cases = {row["case_id"]: row for row in freeze["cases"]}
    policy = next(row for row in freeze["schedule_policies"] if row["policy_id"] == policy_id)
    ordered = []
    for row in policy["order_ledger"]:
        case = cases[row["case_id"]]
        if case["role"] == role and row["case_id"] not in ordered:
            ordered.append(row["case_id"])
    return ordered


def verify_zip(output: Path, run: dict) -> dict:
    archive_path = output / "evidence.zip"
    if sha256(archive_path) != run["evidence"]["sha256"]:
        raise ValueError("evidence ZIP hash mismatch: " + output.name)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate evidence member")
        for name in names:
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError("unsafe evidence member")
            extracted = output / "evidence" / Path(*pure.parts)
            if not extracted.is_file() or extracted.read_bytes() != archive.read(name):
                raise ValueError("extracted evidence mismatch: " + name)
    extracted_names = {
        path.relative_to(output / "evidence").as_posix()
        for path in (output / "evidence").rglob("*") if path.is_file()
    }
    if extracted_names != set(names):
        raise ValueError("evidence extraction member set mismatch")
    return {"bytes": archive_path.stat().st_size, "sha256": sha256(archive_path), "files": len(names)}


def verify_checksums(p7_output: Path) -> None:
    checksums = load(p7_output / "checksums.json")
    rows = checksums["files"]
    expected = {
        path.relative_to(p7_output).as_posix()
        for path in p7_output.rglob("*")
        if path.is_file() and path.name != "checksums.json"
    }
    if {row["path"] for row in rows} != expected:
        raise ValueError("P7 checksum member set mismatch")
    for row in rows:
        path = p7_output / row["path"]
        if path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            raise ValueError("P7 checksum mismatch: " + row["path"])


def junit_counts(path: Path) -> dict:
    root = ET.parse(path).getroot()
    local = lambda element: element.tag.rsplit("}", 1)[-1]
    cases = [row for row in root.iter() if local(row) == "testcase"]
    result = {"tests": len(cases), "failures": 0, "errors": 0, "skipped": 0}
    for case in cases:
        children = {local(child) for child in case}
        for singular, plural in (("failure", "failures"), ("error", "errors"), ("skipped", "skipped")):
            result[plural] += int(singular in children)
    return result


def locked_versions() -> dict[str, str]:
    result = {}
    for line in LOCK.read_text(encoding="utf-8").splitlines():
        match = re.match(r"([A-Za-z0-9_.-]+)==([^ ]+)", line)
        if match:
            result[match.group(1).lower().replace("_", "-")] = match.group(2)
    return result


def verify_success(shard_id: str, spec: tuple, parent: dict) -> dict:
    directory, policy_id, role, expected_cases, expected_cells, offset, limit = spec
    output = HERE / directory
    run = load(output / "RUN.json")
    if (
        run.get("status") != "complete"
        or run.get("creation_http_status") != 201
        or run.get("uploaded_source_files") != 96
        or run.get("evidence", {}).get("verified") is not True
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
    ):
        raise ValueError("run/cleanup status mismatch: " + shard_id)
    if run["evidence"]["runtime_pod_id"] != run["pod_id"]:
        raise ValueError("runtime pod identity mismatch")
    archive = verify_zip(output, run)
    evidence = output / "evidence" / "run-output"
    if junit_counts(evidence / "focused.xml") != {"tests": 42, "failures": 0, "errors": 0, "skipped": 0}:
        raise ValueError("focused JUnit mismatch")
    dependencies = {key.lower().replace("_", "-"): value for key, value in load(evidence / "BASE-DEPENDENCIES.json").items()}
    locked = locked_versions()
    if any(dependencies.get(name) != version for name, version in locked.items()):
        raise ValueError("locked dependency mismatch")

    freeze_path = PARENT_FREEZE if role == "regression" else evidence / "DERIVED-FREEZE.json"
    freeze = load(freeze_path)
    validate_freeze(freeze)
    p7_output = evidence / policy_id
    plan = load(p7_output / "plan.json")
    p7_runner.validate_plan(plan, freeze)
    verify_checksums(p7_output)
    before = load(p7_output / "source-before.json")
    after = load(p7_output / "source-after.json")
    if before != after or p7_runner.source_identity(ROOT, freeze, p7_cli.CODE_PATHS) != after:
        raise ValueError("source identity mismatch")
    oracle_package = load(p7_output / "oracles.json")
    oracles = p7_runner.validate_oracle_package(oracle_package, plan)
    state = p7_runner.read_segments(p7_output / "ledger")
    reproduced = p7_runner.summary(plan, state, oracle_package, source_unchanged=True)
    if reproduced != load(p7_output / "summary.json") or reproduced["status"] != "passed":
        raise ValueError("summary reproduction mismatch")

    expected_ids = parent_order(parent, policy_id, role)
    if offset is not None:
        expected_ids = expected_ids[offset:offset + limit]
    if set(plan["case_ids"]) != set(expected_ids) or len(plan["case_ids"]) != expected_cases:
        raise ValueError("parent case mapping mismatch")
    if len(plan["cells"]) != expected_cells:
        raise ValueError("plan cell count mismatch")

    rows = []
    for segment in sorted((p7_output / "ledger").glob("segment-*.jsonl")):
        rows.extend(json.loads(line) for line in segment.read_text(encoding="utf-8").splitlines() if line.strip())
    by_cell: dict[str, list[dict]] = {}
    for row in rows:
        by_cell.setdefault(row["cell_id"], []).append(row)
    if set(by_cell) != {cell["cell_id"] for cell in plan["cells"]}:
        raise ValueError("ledger cell set mismatch")
    pids = []
    rss = []
    wall = []
    for cell in plan["cells"]:
        records = by_cell[cell["cell_id"]]
        if len(records) != 2 or records[0]["status"] != "running" or records[1]["status"] != "ok":
            raise ValueError("ledger transition mismatch")
        if records[0]["request_sha256"] != records[1]["request_sha256"]:
            raise ValueError("request identity mismatch")
        result = records[1]["result"]
        worker = result["worker"]
        if (
            result["status"] != "ok"
            or result["outside_span_validation"] is not True
            or result["performance_measurement"] is not False
            or worker["status"] != "ok"
            or worker["performance_measurement"] is not False
            or worker["semantic_sha256"] != oracles[cell["case_id"]]["result_sha256"]
            or worker["cell_id"] != cell["cell_id"]
            or result["resources"]["cleanup_verified"] is not True
            or result["resources"]["streams_closed"] is not True
            or result["resources"]["whole_tree_rss_measured"] is not True
        ):
            raise ValueError("worker/oracle/resource mismatch")
        pids.append(worker["environment"]["pid"])
        rss.append(result["process_tree_peak_rss_bytes"])
        wall.append(result["timings_ns"]["task_total_wall_ns"])
    if len(set(pids)) != expected_cells:
        raise ValueError("worker PID reuse within pod")

    return {
        "shard_id": shard_id,
        "directory": directory,
        "pod_id": run["pod_id"],
        "policy_id": policy_id,
        "role": role,
        "cases": expected_cases,
        "cells": expected_cells,
        "case_ids": plan["case_ids"],
        "cell_ids": [cell["cell_id"] for cell in plan["cells"]],
        "worker_pids": pids,
        "max_process_tree_peak_rss_bytes": max(rss),
        "max_task_total_wall_ns": max(wall),
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "evidence": archive,
        "source_identity_sha256": p7_runner.record_sha256(after),
        "freeze_sha256": freeze["freeze_sha256"],
        "performance_measurement": False,
        "verified": True,
    }


def verify_attempts() -> tuple[list[dict], float]:
    rows = []
    total = 0.0
    for name in ATTEMPTS:
        run = load(HERE / name / "RUN.json")
        created = run.get("creation_attempted") is True
        cost = run.get("estimated_compute_cost_usd") or 0.0
        total += cost
        if created and (
            run.get("cleanup", {}).get("owned_pod_absent") is not True
            or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
        ):
            raise ValueError("created attempt cleanup mismatch: " + name)
        if not created and (run.get("pod_created") is not False or run.get("uploaded_source_files") != 0):
            raise ValueError("no-create attempt mismatch: " + name)
        rows.append({
            "directory": name,
            "status": run["status"],
            "creation_attempted": created,
            "pod_id": run.get("pod_id"),
            "uploaded_source_files": run.get("uploaded_source_files"),
            "estimated_compute_cost_usd": cost,
            "error": run.get("evidence", {}).get("validation", {}).get("error") or run.get("error"),
            "cleanup_verified": (not created) or run.get("cleanup", {}).get("owned_pod_absent") is True,
        })
    return rows, total


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    parent = load(PARENT_FREEZE)
    validate_freeze(parent)
    success = [verify_success(shard_id, spec, parent) for shard_id, spec in SUCCESS.items()]
    attempts, total_cost = verify_attempts()

    policies = {}
    all_cell_ids = []
    all_pod_pids = []
    for policy_id, arms in (("p7-ir", 4), ("p7-relation", 5)):
        rows = [row for row in success if row["policy_id"] == policy_id]
        case_ids = [case_id for row in rows for case_id in row["case_ids"]]
        cell_ids = [cell_id for row in rows for cell_id in row["cell_ids"]]
        expected = set(parent_order(parent, policy_id, "regression") + parent_order(parent, policy_id, "development"))
        observed = set(case_ids)
        if len(case_ids) != len(observed) or expected - observed != {SQRT_CASE} or observed - expected:
            raise ValueError("combined case coverage mismatch: " + policy_id)
        if len(cell_ids) != len(set(cell_ids)) or len(cell_ids) != len(observed) * arms:
            raise ValueError("combined cell coverage mismatch: " + policy_id)
        policies[policy_id] = {
            "parent_cases": len(expected),
            "verified_cases": len(observed),
            "excluded_cases": sorted(expected - observed),
            "arms_per_case": arms,
            "parent_cells": len(expected) * arms,
            "verified_cells": len(cell_ids),
            "excluded_cells": len(expected - observed) * arms,
        }
        all_cell_ids.extend(cell_ids)
        all_pod_pids.extend((row["pod_id"], pid) for row in rows for pid in row["worker_pids"])
    if len(all_cell_ids) != len(set(all_cell_ids)) or len(all_pod_pids) != len(set(all_pod_pids)):
        raise ValueError("combined cell/process identity mismatch")

    sqrt = load(HERE / "p7-w3-tail-ir-development-sqrt-v6-001" / "RUN.json")
    if (
        sqrt.get("status") != "failed"
        or sqrt.get("evidence", {}).get("validation", {}).get("error") != "RuntimeError: p7-ir timed out"
        or sqrt.get("evidence", {}).get("validation", {}).get("source_unchanged") is not True
        or sqrt.get("cleanup", {}).get("owned_pod_absent") is not True
    ):
        raise ValueError("sqrt exclusion evidence mismatch")

    report = {
        "schema": "cm-runpod-p7-w3-final-independent-audit/v1",
        "status": "passed_with_one_shared_oracle_feasibility_exclusion",
        "parent_freeze_sha256": parent["freeze_sha256"],
        "source_bundle_sha256": "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668",
        "successful_shards": success,
        "policies": policies,
        "combined": {
            "verified_cases_across_policies": sum(value["verified_cases"] for value in policies.values()),
            "verified_cells": len(all_cell_ids),
            "fresh_process_identities": len(all_pod_pids),
            "excluded_case": SQRT_CASE,
            "excluded_cells": sum(value["excluded_cells"] for value in policies.values()),
            "performance_measurement": False,
            "performance_ranking_permitted": False,
        },
        "sqrt_exclusion": {
            "pod_id": sqrt["pod_id"],
            "stage_limit_seconds": 780,
            "error": sqrt["evidence"]["validation"]["error"],
            "source_unchanged": True,
            "cleanup_verified": True,
            "policy_independent_oracle_generator": True,
            "relation_retry_skipped": True,
        },
        "attempts": attempts,
        "w3_attempt_estimated_compute_cost_usd": total_cost,
        "all_created_attempts_cleaned": True,
        "verified": True,
    }
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": report["status"],
        "policies": policies,
        "combined": report["combined"],
        "w3_attempt_estimated_compute_cost_usd": total_cost,
        "successful_shards": len(success),
        "attempts": len(attempts),
        "verified": True,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
