"""Cached-real functional bridge for all matched comparative task contracts.

Seven outcome-independent conditioned feature-model slices and one separately
named known-change control execute once per backend/lifecycle/task.  Contexts
are generated controls, not natural user sessions.  No timings may be ranked.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import tasks
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.evidence import append_record, publish_json, read_ledger, reconcile
from scripts import cm_comparative_task_pilot as task_pilot
from scripts import cm_session_contracts as sessions
from scripts.cm_benchmark_provenance import capture_source_snapshot


SCHEMA = "cm-comparative-real-task-bridge/v1"
SOURCES = tuple(dict.fromkeys((
    *task_pilot.SOURCES,
    "scripts/cm_comparative_real_task_bridge.py",
    "tests/test_cm_comparative_real_task_bridge.py",
    sessions.HISTORY,
    sessions.ADMISSIONS,
)))


def bridge_traces() -> dict[str, list[dict[str, Any]]]:
    query = [
        {"version": 0, "assumptions": []},
        {"version": 0, "assumptions": [1]},
        {"version": 0, "assumptions": [-1]},
        {"version": 1, "assumptions": []},
        {"version": 1, "assumptions": [1]},
        {"version": 1, "assumptions": [-1]},
    ]
    return {
        "exact_count": [{"version": 0}, {"version": 1}],
        "sat_status": query,
        "witness": [query[0], query[1], query[3], query[5]],
        "partial_context": [*query, {"version": 1, "assumptions": []}, {"version": 0, "assumptions": []}],
        "version_history": [query[0], query[1], query[4], query[3], query[5], query[0]],
        "equivalence_delta": [
            {"before": 0, "after": 0},
            {"before": 0, "after": 1},
            {"before": 1, "after": 0},
        ],
    }


def cohort(root: Path = ROOT) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    default, default_ledger = sessions.historical_scenarios(root)
    known, known_ledger = sessions.historical_scenarios(root, known_change_control=True)
    scenarios = [*default, *known]
    if len(scenarios) != 8 or len({row["id"] for row in scenarios}) != 8:
        raise ValueError("real bridge cohort changed")
    selection = {
        "schema": SCHEMA,
        "selection": "seven first eligible k8 cases by history plus separate named known-change diagnostic",
        "performance_or_output_used_for_default_selection": False,
        "known_change_control_output_selected": True,
        "default_candidate_ledger": default_ledger,
        "known_change_candidate_ledger": known_ledger,
        "original_transition_admissions": sessions.original_admissions(root),
    }
    return scenarios, selection


def _safe_id(index: int, scenario: dict[str, Any]) -> str:
    return f"real-{index:02}-{scenario['source']['history']}"


def build_bundle(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    scenarios, selection = cohort(root)
    trace_map = bridge_traces()
    case_rows, oracle_rows, cells = [], {}, []
    contracts: dict[str, dict[str, Any]] = {}
    for index, scenario in enumerate(scenarios):
        case_id = _safe_id(index, scenario)
        scenario_sha = hashlib.sha256(canonical_bytes(scenario)).hexdigest()
        case_rows.append({"case_id": case_id, "scenario": scenario, "scenario_sha256": scenario_sha,
                          "selection_role": scenario["source"].get("selection_role", "outcome_independent_default")})
        oracle_rows[case_id] = {}
        for task in tasks.TASKS:
            expected = tasks.scalar_oracle(scenario, task, trace_map[task])
            expected_sha = tasks.semantic_digest(task, expected)
            oracle_rows[case_id][task] = {"rows": expected, "sha256": expected_sha}
            for backend in tasks.BACKENDS:
                for lifecycle in tasks.LIFECYCLES:
                    key = f"{case_id}/{task}/{backend}/{lifecycle}"
                    contract = tasks.task_contract(
                        contract_id=f"bridge-{index}-{task}-{backend}-{lifecycle}", task=task, backend=backend,
                        lifecycle=lifecycle, k=scenario["k"], queries=len(trace_map[task]),
                        expected_sha256=expected_sha,
                    )
                    contracts[key] = contract
                    identity = {"case_id": case_id, "scenario_sha256": scenario_sha, "task": task,
                                "backend": backend, "lifecycle": lifecycle,
                                "contract_sha256": hashlib.sha256(canonical_bytes(contract)).hexdigest()}
                    cells.append({**identity, "cell_id": hashlib.sha256(canonical_bytes(identity)).hexdigest()})
    if len(cells) != 384 or len({row["cell_id"] for row in cells}) != 384:
        raise ValueError("real bridge cell cardinality")
    plan = {
        "schema": SCHEMA,
        "schedule": "fixed functional coverage; one cell per case/task/backend/lifecycle; timings prohibited",
        "performance_claim_permitted": False,
        "contexts": "generated controls over cached conditioned relations; not natural user traces",
        "traces": trace_map,
        "cases": case_rows,
        "contracts": contracts,
        "cells": cells,
        "selection": selection,
    }
    return plan, {"schema": SCHEMA, "cases": oracle_rows}, selection


def sha256_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            value.update(block)
    return value.hexdigest()


def _source_rows() -> list[dict[str, Any]]:
    return [{"path": name, "sha256": sha256_file(ROOT / name), "bytes": (ROOT / name).stat().st_size}
            for name in SOURCES]


def _checksums(output: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "checksums.json"):
        rows.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size,
                     "sha256": sha256_file(path)})
    return {"schema": "cm-comparative-real-task-checksums/v1", "files": rows}


def _safe_output(path: Path) -> Path:
    target, root = path.absolute(), ROOT.resolve()
    if target.exists() or not target.parent.exists() or not target.parent.resolve().is_relative_to(root):
        raise ValueError("new project output required")
    if any(item.is_symlink() or item.is_junction() for item in (target.parent.resolve(), *target.parent.resolve().parents)
           if item != root.parent):
        raise ValueError("linked output path refused")
    target.mkdir()
    return target


def run(output: Path) -> dict[str, Any]:
    output = _safe_output(output)
    before = _source_rows()
    snapshot = capture_source_snapshot(ROOT, output / "source_snapshot", SOURCES)
    plan, oracles, _selection = build_bundle(ROOT)
    publish_json(output / "plan.json", {**plan, "source_manifest_sha256": snapshot["manifest_sha256"]})
    publish_json(output / "oracles.json", oracles)
    ledger = output / "ledger.jsonl"
    cases = {row["case_id"]: row for row in plan["cases"]}
    counters: Counter[str] = Counter()
    semantic_rows = native_solves = 0
    for cell in plan["cells"]:
        if _source_rows() != before:
            raise ValueError("working source changed during real bridge")
        case = cases[cell["case_id"]]
        trace = plan["traces"][cell["task"]]
        contract = plan["contracts"][f'{cell["case_id"]}/{cell["task"]}/{cell["backend"]}/{cell["lifecycle"]}']
        request_sha = hashlib.sha256(canonical_bytes({"cell": cell, "trace": trace})).hexdigest()
        append_record(ledger, {"cell_id": cell["cell_id"], "status": "running", "request_sha256": request_sha})
        result = tasks.execute_task(
            scenario=case["scenario"], task=cell["task"], trace=trace, backend=cell["backend"],
            lifecycle=cell["lifecycle"], contract=contract, case_id=cell["case_id"],
        )
        expected = oracles["cases"][cell["case_id"]][cell["task"]]["rows"]
        tasks.validate_task_result(result, contract, expected, expected_backend=cell["backend"],
                                   expected_case_id=cell["case_id"])
        append_record(ledger, {"cell_id": cell["cell_id"], "status": "ok", "request_sha256": request_sha,
                               "result": result})
        counters[cell["task"]] += 1
        semantic_rows += len(expected)
        native_solves += result["identity"]["counters"]["solve_calls"]
    if _source_rows() != before:
        raise ValueError("working source changed during real bridge")
    state = read_ledger(ledger)
    reconciliation = reconcile(plan, state)
    if not reconciliation["complete"] or reconciliation["statuses"] != {"ok": 384}:
        raise ValueError("real bridge reconciliation")
    default_delta = [oracles["cases"][_safe_id(i, row)]["equivalence_delta"]["rows"][1]["changed_assignments"]
                     for i, row in enumerate([item["scenario"] for item in plan["cases"][:7]])]
    control_delta = oracles["cases"][plan["cases"][7]["case_id"]]["equivalence_delta"]["rows"][1]
    summary = {
        "schema": SCHEMA,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "scenario_count": 8,
        "default_scenario_count": 7,
        "known_change_control_count": 1,
        "planned_cells": 384,
        "accepted_semantic_rows": semantic_rows,
        "native_sat_solve_calls": native_solves,
        "cells_by_task": dict(sorted(counters.items())),
        "default_forward_delta_counts": default_delta,
        "known_change_forward_delta": control_delta,
        "reconciliation": reconciliation,
        "source_unchanged": True,
        "cloud_run": False,
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "natural_user_trace": False,
        "limitations": [
            "cached conditioned k8 relations, not whole-model equivalence or existential projection",
            "generated contexts, not captured configurator sessions",
            "one functional cell per case/task/backend/lifecycle; no performance repetitions",
            "known-change control is outcome-selected and kept separate from the default cohort",
            "CUDD, ZDD and d4 are outside this bridge",
        ],
    }
    publish_json(output / "summary.json", summary)
    publish_json(output / "checksums.json", _checksums(output))
    return summary


def verify(output: Path) -> dict[str, Any]:
    output = output.resolve()
    checksums = json.loads((output / "checksums.json").read_text(encoding="utf-8"))
    if checksums.get("schema") != "cm-comparative-real-task-checksums/v1":
        raise ValueError("checksum schema")
    listed = []
    for row in checksums["files"]:
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
        if path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError("source snapshot")
    plan = json.loads((output / "plan.json").read_text(encoding="utf-8"))
    oracles = json.loads((output / "oracles.json").read_text(encoding="utf-8"))
    if plan.get("schema") != SCHEMA or len(plan.get("cells", [])) != 384 or len({row["cell_id"] for row in plan["cells"]}) != 384:
        raise ValueError("plan identity")
    cells = {row["cell_id"]: row for row in plan["cells"]}
    state = read_ledger(output / "ledger.jsonl")
    if not reconcile(plan, state)["complete"]:
        raise ValueError("ledger reconciliation")
    for cell_id, terminal in state["states"].items():
        cell = cells[cell_id]
        key = f'{cell["case_id"]}/{cell["task"]}/{cell["backend"]}/{cell["lifecycle"]}'
        contract = plan["contracts"][key]
        tasks.validate_task_result(
            terminal["result"], contract, oracles["cases"][cell["case_id"]][cell["task"]]["rows"],
            expected_backend=cell["backend"], expected_case_id=cell["case_id"],
        )
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "passed" or summary.get("performance_claim_permitted") is not False or \
            summary.get("natural_user_trace") is not False:
        raise ValueError("summary boundary")
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
