"""Create or verify the bounded P3 task-matched functional evidence bundle.

No cloud, network, installs or performance ranking.  CM, structural CSE,
direct CNF and installed CaDiCaL execute balanced fresh/resident cells against
an independent scalar CNF oracle.  Timings exist only to exercise accounting.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import tasks
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.evidence import append_record, publish_json, read_ledger, reconcile
from cmbench.comparative.schedule import build_plan, validate_plan
from scripts.cm_benchmark_provenance import capture_source_snapshot
from scripts.cm_native_contracts import sat_identity


SCHEMA = "cm-comparative-task-pilot/v1"
SEED = 2026082903
SOURCES = (
    "scripts/cm_comparative_task_pilot.py",
    "cmbench/comparative/__init__.py",
    "cmbench/comparative/tasks.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/arms.py",
    "cmbench/comparative/ir.py",
    "cmbench/comparative/evidence.py",
    "cmbench/comparative/schedule.py",
    "tests/test_cm_comparative_tasks.py",
    "tests/test_cm_comparative_task_pilot.py",
    "scripts/cm_session_contracts.py",
    "scripts/cm_measurement_verify.py",
    "scripts/cm_native_contracts.py",
    "scripts/cm_benchmark_provenance.py",
    "bitset_backend.py",
    "cm_ir.py",
    "cm_exprlib.py",
    "cm_expr_serde.py",
    "cm_normalize.py",
    "cmbench/__init__.py",
    "cmbench/output_budget.py",
    "cmbench/reporting/__init__.py",
    "cmbench/reporting/provenance.py",
    "cmbench/reporting/summary_tables.py",
)


def scenario() -> dict[str, Any]:
    return {
        "id": "matched-k6-p3",
        "k": 6,
        "feature_names": [f"x{i}" for i in range(6)],
        "versions": [
            {"id": "base", "clauses": [[1, -6], [-1, 6]]},
            {"id": "duplicate", "clauses": [[1, -6], [-1, 6], [1, -6]]},
            {"id": "restricted", "clauses": [[1, -6], [-1, 6], [-1]]},
        ],
        "source": {"kind": "synthetic", "purpose": "balanced_task_contract_control"},
    }


def traces() -> dict[str, list[dict[str, Any]]]:
    query = [
        {"version": 0, "assumptions": []},
        {"version": 0, "assumptions": [1]},
        {"version": 1, "assumptions": [-1, -6]},
        {"version": 2, "assumptions": [1]},
        {"version": 2, "assumptions": [-1]},
        {"version": 0, "assumptions": []},
    ]
    return {
        "exact_count": [{"version": 0}, {"version": 1}, {"version": 2}],
        "sat_status": query,
        "witness": [query[0], query[3], query[4]],
        "partial_context": [*query, {"version": 2, "assumptions": []}, {"version": 0, "assumptions": [-1]}],
        "version_history": query,
        "equivalence_delta": [
            {"before": 0, "after": 1},
            {"before": 1, "after": 2},
            {"before": 2, "after": 0},
        ],
    }


def sha256_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            value.update(block)
    return value.hexdigest()


def _safe_output(output: Path) -> Path:
    target = output.absolute()
    root = ROOT.resolve()
    if target.exists() or not target.parent.exists() or not target.parent.resolve().is_relative_to(root):
        raise ValueError("new output under an existing project directory required")
    for item in (target.parent.resolve(), *target.parent.resolve().parents):
        if item == root.parent:
            break
        if item.is_symlink() or item.is_junction():
            raise ValueError("linked output path refused")
    target.mkdir()
    return target


def _source_rows() -> list[dict[str, Any]]:
    return [{"path": name, "sha256": sha256_file(ROOT / name), "bytes": (ROOT / name).stat().st_size}
            for name in SOURCES]


def _checksums(output: Path) -> dict[str, Any]:
    files = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "checksums.json"):
        files.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size,
                      "sha256": sha256_file(path)})
    return {"schema": "cm-comparative-task-checksums/v1", "files": files}


def _environment() -> dict[str, Any]:
    native = sat_identity()
    if native.get("status") != "available":
        raise ValueError("installed native CaDiCaL is required for this pilot")
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "python-sat")},
        "native_sat": native,
        "network_used": False,
        "cloud_used": False,
    }


def _plans(case: dict[str, Any], trace_map: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    input_sha = hashlib.sha256(canonical_bytes(case)).hexdigest()
    plan_case = [{"case_id": case["id"], "cluster_id": "synthetic-task-control", "input_sha256": input_sha}]
    expected: dict[str, Any] = {}
    plans = []
    for task in tasks.TASKS:
        rows = tasks.scalar_oracle(case, task, trace_map[task])
        expected[task] = {"rows": rows, "sha256": tasks.semantic_digest(task, rows)}
        for lifecycle in tasks.LIFECYCLES:
            contracts = {
                backend: tasks.task_contract(
                    contract_id=f"p3-{task}-{lifecycle}-{backend}", task=task, backend=backend,
                    lifecycle=lifecycle, k=case["k"], queries=len(trace_map[task]),
                    expected_sha256=expected[task]["sha256"],
                )
                for backend in tasks.BACKENDS
            }
            plans.append(build_plan(
                campaign_id=f"p3-{task}-{lifecycle}-v1", cases=plan_case, arms=tasks.BACKENDS,
                contracts=contracts, blocks=8, locality="round_robin", seed=SEED, shard_cells=32,
            ))
    return plans, expected


def run(output: Path) -> dict[str, Any]:
    output = _safe_output(output)
    before = _source_rows()
    snapshot = capture_source_snapshot(ROOT, output / "source_snapshot", SOURCES)
    case, trace_map = scenario(), traces()
    plans, expected = _plans(case, trace_map)
    environment = _environment()
    publish_json(output / "case.json", {"schema": SCHEMA, "scenario": case, "traces": trace_map})
    publish_json(output / "oracles.json", {"schema": SCHEMA, "tasks": expected})
    publish_json(output / "plans.json", {"schema": SCHEMA, "plans": plans,
                                         "source_manifest_sha256": snapshot["manifest_sha256"]})
    publish_json(output / "environment.json", environment)

    ledger = output / "ledger.jsonl"
    all_cells = []
    task_counts: Counter[str] = Counter()
    accepted_queries = 0
    native_solves = 0
    engine_counts: Counter[str] = Counter()
    for plan in plans:
        for cell in plan["cells"]:
            if _source_rows() != before:
                raise ValueError("working source changed during task pilot")
            trace = trace_map[plan["task"]]
            request = {"cell": cell, "scenario": case, "trace": trace}
            request_sha = hashlib.sha256(canonical_bytes(request)).hexdigest()
            append_record(ledger, {"cell_id": cell["cell_id"], "status": "running", "request_sha256": request_sha})
            result = tasks.execute_task(
                scenario=case, task=plan["task"], trace=trace, backend=cell["arm"],
                lifecycle=plan["contracts"][cell["arm"]]["lifecycle"],
                contract=plan["contracts"][cell["arm"]], case_id=case["id"],
            )
            tasks.validate_task_result(
                result, plan["contracts"][cell["arm"]], expected[plan["task"]]["rows"],
                expected_backend=cell["arm"], expected_case_id=case["id"],
            )
            append_record(ledger, {"cell_id": cell["cell_id"], "status": "ok", "request_sha256": request_sha,
                                   "task": plan["task"], "lifecycle": plan["contracts"][cell["arm"]]["lifecycle"],
                                   "result": result, "oracle_sha256": expected[plan["task"]]["sha256"]})
            all_cells.append(cell)
            task_counts[plan["task"]] += 1
            accepted_queries += len(result["identity"]["semantic_output"]["rows"])
            native_solves += result["identity"]["counters"]["solve_calls"]
            engine_counts[f'{cell["arm"]}/{plan["contracts"][cell["arm"]]["lifecycle"]}'] += \
                result["identity"]["counters"]["engine_instances"]

    after = _source_rows()
    if before != after:
        raise ValueError("working source changed during task pilot")
    state = read_ledger(ledger)
    combined_plan = {"cells": all_cells}
    reconciliation = reconcile(combined_plan, state)
    if not reconciliation["complete"] or reconciliation["statuses"] != {"ok": len(all_cells)}:
        raise ValueError("task pilot did not reconcile")
    summary = {
        "schema": SCHEMA,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "case_count": 1,
        "task_count": len(tasks.TASKS),
        "backend_count": len(tasks.BACKENDS),
        "lifecycle_count": len(tasks.LIFECYCLES),
        "planned_cells": len(all_cells),
        "accepted_semantic_rows": accepted_queries,
        "native_sat_solve_calls": native_solves,
        "cells_by_task": dict(sorted(task_counts.items())),
        "engine_instances_by_backend_lifecycle": dict(sorted(engine_counts.items())),
        "reconciliation": reconciliation,
        "source_unchanged": True,
        "output_cache_used": False,
        "cloud_run": False,
        "limitations": [
            "single synthetic k=6 scenario with repeated counterbalance blocks",
            "in-process functional cells; no fresh-process or RSS comparison",
            "timings are diagnostic and fixed-order aggregates are prohibited",
            "CUDD, ZDD and d4 are outside this local task pilot",
            "canonical witness extraction deliberately charges complete bounded-vector enumeration",
        ],
    }
    publish_json(output / "summary.json", summary)
    publish_json(output / "checksums.json", _checksums(output))
    return summary


def verify(output: Path) -> dict[str, Any]:
    output = output.resolve()
    checksums = json.loads((output / "checksums.json").read_text(encoding="utf-8"))
    if checksums.get("schema") != "cm-comparative-task-checksums/v1":
        raise ValueError("checksum schema")
    listed = []
    for row in checksums.get("files", []):
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise ValueError("checksum row")
        path = output.joinpath(*Path(row["path"]).parts)
        if not path.resolve().is_relative_to(output) or not path.is_file() or path.stat().st_size != row["bytes"] or \
                sha256_file(path) != row["sha256"]:
            raise ValueError("checksum identity")
        listed.append(row["path"])
    actual = sorted(path.relative_to(output).as_posix() for path in output.rglob("*")
                    if path.is_file() and path.name != "checksums.json")
    if listed != actual:
        raise ValueError("checksum membership")
    source_manifest = json.loads((output / "source_snapshot/source_manifest.json").read_text(encoding="utf-8"))
    for row in source_manifest["files"]:
        path = output / "source_snapshot" / row["path"]
        if sha256_file(path) != row["sha256"] or path.stat().st_size != row["size_bytes"]:
            raise ValueError("source snapshot")
    plans = json.loads((output / "plans.json").read_text(encoding="utf-8"))["plans"]
    for plan in plans:
        validate_plan(plan)
    case_doc = json.loads((output / "case.json").read_text(encoding="utf-8"))
    oracle_doc = json.loads((output / "oracles.json").read_text(encoding="utf-8"))
    state = read_ledger(output / "ledger.jsonl")
    cells = {cell["cell_id"]: (plan, cell) for plan in plans for cell in plan["cells"]}
    if not reconcile({"cells": [item[1] for item in cells.values()]}, state)["complete"]:
        raise ValueError("ledger reconciliation")
    for cell_id, terminal in state["states"].items():
        plan, cell = cells[cell_id]
        expected = oracle_doc["tasks"][plan["task"]]["rows"]
        tasks.validate_task_result(
            terminal["result"], plan["contracts"][cell["arm"]], expected,
            expected_backend=cell["arm"], expected_case_id=case_doc["scenario"]["id"],
        )
        if terminal["task"] != plan["task"] or terminal["oracle_sha256"] != oracle_doc["tasks"][plan["task"]]["sha256"]:
            raise ValueError("ledger task/oracle identity")
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "passed" or summary.get("performance_claim_permitted") is not False or \
            case_doc.get("scenario") != scenario():
        raise ValueError("summary/case boundary")
    return {"status": "passed", "files": len(listed) + 1, "cells": len(cells), "mutated": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output) if args.command == "run" else verify(args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
