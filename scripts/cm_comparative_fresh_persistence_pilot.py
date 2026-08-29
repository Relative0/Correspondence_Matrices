"""Run or verify fresh-process structural persistence evidence.

The local pilot uses cached-real bounded feature-model slices.  Every executed
cell gets one build process and a different reload/query process under the
platform's owned-process supervisor.  Native arms without reviewed local
adapters are preserved as refusals.  Timings and Windows committed-memory
high-water values are diagnostic only; this script never permits a performance
ranking or launches cloud resources.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import fresh_persistence as fresh
from cmbench.comparative import persistence
from cmbench.comparative.contracts import RESULT_SCHEMA, canonical_bytes, contract_digest
from cmbench.comparative.evidence import append_record, publish_json, read_ledger, reconcile
from cmbench.comparative.schedule import build_plan, validate_plan
from scripts.cm_benchmark_provenance import capture_source_snapshot


SCHEMA = "cm-comparative-fresh-persistence-pilot/v1"
CHECKSUM_SCHEMA = "cm-comparative-fresh-persistence-checksums/v1"
SEED = 2026082905
SOURCES = (
    "scripts/cm_comparative_fresh_persistence_pilot.py",
    "tests/test_cm_comparative_fresh_persistence.py",
    "tests/test_cm_comparative_fresh_persistence_pilot.py",
    "cmbench/comparative/fresh_persistence.py",
    "cmbench/comparative/persistence.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/arms.py",
    "cmbench/comparative/ir.py",
    "cmbench/comparative/evidence.py",
    "cmbench/comparative/schedule.py",
    "cmbench/comparative/linux_supervisor.py",
    "scripts/cm_process_supervisor.py",
    "scripts/cm_comparative_real_task_bridge.py",
    "scripts/cm_comparative_task_pilot.py",
    "scripts/cm_session_contracts.py",
    "scripts/cm_native_contracts.py",
    "scripts/cm_measurement_verify.py",
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
    fresh.sessions.HISTORY,
    fresh.sessions.ADMISSIONS,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def _source_rows(root: Path = ROOT) -> list[dict[str, Any]]:
    return [
        {"path": name, "sha256": sha256_file(root / name), "bytes": (root / name).stat().st_size}
        for name in SOURCES
    ]


def _safe_output(path: Path) -> Path:
    target, root = path.absolute(), ROOT.resolve()
    if target.exists() or not target.parent.exists() or not target.parent.resolve().is_relative_to(root):
        raise ValueError("new project output required")
    parents = (target.parent.resolve(), *target.parent.resolve().parents)
    if any(item.is_symlink() or item.is_junction() for item in parents if item != root.parent):
        raise ValueError("linked output path refused")
    target.mkdir()
    (target / "artifacts").mkdir()
    return target


def _checksums(output: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "checksums.json"):
        rows.append(
            {
                "path": path.relative_to(output).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {"schema": CHECKSUM_SCHEMA, "files": rows}


def build_bundle(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    from scripts import cm_comparative_real_task_bridge as bridge

    scenarios, selection = bridge.cohort(root)
    scenario_lookup: dict[str, dict[str, Any]] = {}
    oracle_rows: dict[str, list[dict[str, Any]]] = {}
    cases = []
    for index, scenario in enumerate(scenarios):
        case_id = f"case-{index:02}"
        scenario_lookup[case_id] = scenario
        digest = hashlib.sha256(canonical_bytes(scenario)).hexdigest()
        cases.append({"case_id": case_id, "cluster_id": scenario["source"]["history"], "input_sha256": digest})
        oracle_rows[case_id] = persistence.scalar_oracle(scenario)
    capabilities = fresh.capability_inventory()
    execution_arms = tuple(arm for arm in fresh.ARMS if capabilities[arm]["status"] == "available")
    refused_arms = tuple(arm for arm in fresh.ARMS if capabilities[arm]["status"] == "refused")
    if not execution_arms or set(execution_arms) | set(refused_arms) != set(fresh.ARMS):
        raise ValueError("capability partition")
    # ``balanced_orders`` contains one forward and one reverse rotation per
    # arm, so 2*n blocks are one complete counterbalance cycle.
    blocks = 2 * len(execution_arms)
    contracts = {
        arm: fresh.fresh_contract(
            contract_id=f"fresh-persistence-{arm}", arm=arm, k=8, queries=2
        )
        for arm in execution_arms
    }
    schedule = build_plan(
        campaign_id="fresh-process-persistence-v1",
        cases=cases,
        arms=execution_arms,
        contracts=contracts,
        blocks=blocks,
        locality="round_robin",
        seed=SEED,
        shard_cells=32,
    )
    plan = {
        "schema": SCHEMA,
        "schedule": schedule,
        "scenarios": scenario_lookup,
        "selection": selection,
        "capabilities": capabilities,
        "execution_arms": list(execution_arms),
        "refused_arms": list(refused_arms),
        "admission_contracts": {
            arm: fresh.fresh_contract(
                contract_id=f"fresh-persistence-admission-{arm}", arm=arm, k=8, queries=2
            )
            for arm in refused_arms
        },
        "admissions": {},
        "cloud_run": False,
        "network_used": False,
        "performance_claim_permitted": False,
        "timings_for_contract_diagnostics_only": True,
    }
    plan["admissions"] = {
        arm: fresh.refused_result(
            arm=arm,
            case_id="capability-gate",
            contract=plan["admission_contracts"][arm],
            capability=capabilities[arm],
        )
        for arm in refused_arms
    }
    return plan, {"schema": SCHEMA, "cases": oracle_rows}


def _supervised(command: list[str], *, payload: bytes, cwd: Path):
    if os.name == "nt":
        from scripts import cm_process_supervisor as supervisor

        return supervisor.run(
            command,
            input=payload,
            cwd=cwd,
            limits=supervisor.Limits(
                timeout_seconds=30,
                memory_bytes=1024 << 20,
                processes=4,
                input_bytes=fresh.MAX_REQUEST_BYTES,
                stdout_bytes=1 << 20,
                stderr_bytes=64 << 10,
            ),
        )
    from cmbench.comparative import linux_supervisor

    return linux_supervisor.run(
        command,
        input=payload,
        cwd=cwd,
        limits=linux_supervisor.Limits(
            timeout_seconds=30,
            rss_stop_bytes=1024 << 20,
            processes=4,
            input_bytes=fresh.MAX_REQUEST_BYTES,
            stdout_bytes=1 << 20,
            stderr_bytes=64 << 10,
        ),
    )


def _observed_pids(resources: dict[str, Any]) -> list[int]:
    rows = resources.get("observed_job_pids", resources.get("observed_group_pids", []))
    if not isinstance(rows, list) or not all(type(item) is int for item in rows):
        raise ValueError("supervisor PID evidence")
    return rows


def _run_worker(frozen_script: Path, request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], int]:
    payload = canonical_bytes(request)
    result = _supervised(
        [str(Path(sys.executable).resolve()), "-B", str(frozen_script.resolve()), "--worker"],
        payload=payload,
        cwd=frozen_script.parents[1],
    )
    if result.status != "ok":
        excerpt = result.stderr[:4096].decode("utf-8", errors="replace") if result.stderr else ""
        raise RuntimeError(f"fresh persistence worker {result.reason}: {excerpt}")
    resources = result.resources
    if not resources.get("cleanup_verified") or not resources.get("streams_closed"):
        raise RuntimeError("fresh persistence worker cleanup")
    value = fresh._strict_json(result.stdout)
    if not isinstance(value, dict) or value.get("schema") != fresh.WORKER_SCHEMA:
        raise RuntimeError("fresh persistence worker result")
    if value.get("pid") not in _observed_pids(resources):
        raise RuntimeError("worker PID missing from owned supervisor scope")
    return value, resources, result.wall_ns


def execute_cell(
    *,
    cell: dict[str, Any],
    scenario: dict[str, Any],
    contract: dict[str, Any],
    capability: dict[str, Any],
    output: Path,
    frozen_script: Path,
) -> tuple[dict[str, Any], Path | None]:
    arm = cell["arm"]
    if capability["status"] == "refused":
        return fresh.refused_result(
            arm=arm, case_id=cell["case_id"], contract=contract, capability=capability
        ), None
    if capability["status"] != "available":
        raise ValueError("unknown capability state")
    artifact_path = (output / "artifacts" / f"cell-{cell['cell_id']}.json").resolve()
    build_request = {
        "schema": fresh.REQUEST_SCHEMA,
        "mode": "build",
        "arm": arm,
        "scenario": scenario,
        "artifact_path": str(artifact_path),
    }
    build, build_resources, build_wall = _run_worker(frozen_script, build_request)
    reload_request = {
        "schema": fresh.REQUEST_SCHEMA,
        "mode": "reload_query",
        "arm": arm,
        "scenario": scenario,
        "artifact_path": str(artifact_path),
        "artifact_sha256": build["artifact"]["sha256"],
    }
    reload, reload_resources, reload_wall = _run_worker(frozen_script, reload_request)
    if build["pid"] == reload["pid"]:
        raise RuntimeError("fresh worker PID reuse prevents independent-process proof")
    task_total = build_wall + reload_wall
    result = {
        "schema": RESULT_SCHEMA,
        "contract_sha256": contract_digest(contract),
        "case_id": cell["case_id"],
        "arm": arm,
        "status": "ok",
        "reason": "completed",
        "timings_ns": {
            "build_controller_wall_ns": build_wall,
            "reload_controller_wall_ns": reload_wall,
            "build_worker_task_ns": build["timings_ns"]["task_total_ns"],
            "reload_worker_task_ns": reload["timings_ns"]["task_total_ns"],
            "task_total_ns": task_total,
        },
        "artifact": {
            "kind": "serialized_structure",
            "output_scope": "not_applicable",
            "output_order": [],
            "bytes": build["artifact"]["bytes"],
            "sha256": build["artifact"]["sha256"],
        },
        "resources": {
            "launched": True,
            "fresh_processes_verified": True,
            "build": build_resources,
            "reload": reload_resources,
            "memory_metrics": [build_resources.get("memory_metric"), reload_resources.get("memory_metric")],
            "whole_tree_rss_measured": bool(
                build_resources.get("whole_tree_rss_measured")
                and reload_resources.get("whole_tree_rss_measured")
            ),
            "memory_ranking_permitted": False,
            "memory_ranking_reason": "single functional pilot; Windows committed memory is not RSS",
        },
        "identity": {
            "schema": fresh.RESULT_IDENTITY_SCHEMA,
            "capability": capability,
            "build_worker": build,
            "reload_worker": reload,
            "native_execution": capability["native_execution"],
            "portability_control": capability["portability_control"],
            "substitution_used": False,
            "answer_cache_included": False,
            "performance_claim_permitted": False,
        },
    }
    return result, artifact_path


def run(output: Path) -> dict[str, Any]:
    output = _safe_output(output)
    before = _source_rows()
    snapshot = capture_source_snapshot(ROOT, output / "source_snapshot", SOURCES)
    frozen_script = output / "source_snapshot/scripts/cm_comparative_fresh_persistence_pilot.py"
    plan, oracles = build_bundle(ROOT)
    publish_json(output / "plan.json", {**plan, "source_manifest_sha256": snapshot["manifest_sha256"]})
    publish_json(output / "oracles.json", oracles)

    ledger = output / "ledger.jsonl"
    status_counts: Counter[str] = Counter()
    arm_statuses: dict[str, Counter[str]] = defaultdict(Counter)
    artifact_hashes: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for cell in plan["schedule"]["cells"]:
        scenario = plan["scenarios"][cell["case_id"]]
        contract = plan["schedule"]["contracts"][cell["arm"]]
        capability = plan["capabilities"][cell["arm"]]
        request_sha = hashlib.sha256(
            canonical_bytes({"cell": cell, "scenario_sha256": cell["input_sha256"], "capability": capability})
        ).hexdigest()
        append_record(ledger, {"cell_id": cell["cell_id"], "status": "running", "request_sha256": request_sha})
        result, artifact_path = execute_cell(
            cell=cell,
            scenario=scenario,
            contract=contract,
            capability=capability,
            output=output,
            frozen_script=frozen_script,
        )
        fresh.validate_fresh_result(
            result,
            contract,
            scenario=scenario,
            expected_rows=oracles["cases"][cell["case_id"]],
            capability=capability,
            artifact_path=artifact_path,
        )
        append_record(
            ledger,
            {"cell_id": cell["cell_id"], "status": result["status"], "request_sha256": request_sha, "result": result},
        )
        status_counts[result["status"]] += 1
        arm_statuses[cell["arm"]][result["status"]] += 1
        if artifact_path is not None:
            artifact_hashes[cell["case_id"]][cell["arm"]].add(result["artifact"]["sha256"])

    state = read_ledger(ledger)
    reconciliation = reconcile(plan["schedule"], state)
    if not reconciliation["complete"]:
        raise ValueError("fresh-persistence ledger did not reconcile")
    deterministic = all(len(hashes) == 1 for arms in artifact_hashes.values() for hashes in arms.values())
    after = _source_rows()
    live_changes = [
        {"path": old["path"], "before": old["sha256"], "after": new["sha256"]}
        for old, new in zip(before, after)
        if old != new
    ]
    summary = {
        "schema": SCHEMA,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "case_count": len(plan["scenarios"]),
        "arm_count": len(fresh.ARMS),
        "executed_arm_count": len(plan["execution_arms"]),
        "refused_arm_count": len(plan["refused_arms"]),
        "refused_arms": plan["refused_arms"],
        "blocks": plan["schedule"]["blocks"],
        "planned_cells": len(plan["schedule"]["cells"]),
        "cell_statuses": dict(sorted(status_counts.items())),
        "arm_statuses": {arm: dict(sorted(counts.items())) for arm, counts in sorted(arm_statuses.items())},
        "executed_build_processes": status_counts["ok"],
        "executed_reload_processes": status_counts["ok"],
        "exact_relation_rows": status_counts["ok"] * 2,
        "serialized_artifact_deterministic_across_blocks": deterministic,
        "reconciliation": reconciliation,
        "source_manifest_frozen": True,
        "concurrent_source_changes": live_changes,
        "cloud_run": False,
        "network_used": False,
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "limitations": [
            "conditioned k=8 cached-real feature-model slices rather than full models",
            "dd.autoref is a portable ROBDD control and is not native CUDD",
            "native CUDD BDD executes only if its extension is installed and identified",
            "CUDD ZDD and d4 d-DNNF persistence remain explicit refusals without reviewed adapters",
            "Windows Job Object committed-memory high-water is not process-tree RSS",
            "one complete local counterbalance cycle is insufficient for performance ranking",
        ],
    }
    publish_json(output / "summary.json", summary)
    publish_json(output / "checksums.json", _checksums(output))
    return summary


def verify(output: Path) -> dict[str, Any]:
    output = output.resolve()
    checksums = json.loads((output / "checksums.json").read_text(encoding="utf-8"))
    if checksums.get("schema") != CHECKSUM_SCHEMA:
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
    actual = sorted(
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file() and path.name != "checksums.json"
    )
    if listed != actual:
        raise ValueError("checksum membership")

    manifest = json.loads((output / "source_snapshot/source_manifest.json").read_text(encoding="utf-8"))
    for row in manifest["files"]:
        path = output / "source_snapshot" / row["path"]
        if path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError("source snapshot identity")
    plan = json.loads((output / "plan.json").read_text(encoding="utf-8"))
    validate_plan(plan["schedule"])
    if (
        set(plan["execution_arms"]) != set(plan["schedule"]["contracts"])
        or set(plan["refused_arms"]) != set(plan["admissions"])
        or set(plan["execution_arms"]) | set(plan["refused_arms"]) != set(fresh.ARMS)
    ):
        raise ValueError("capability partition")
    for arm in plan["refused_arms"]:
        fresh.validate_fresh_result(
            plan["admissions"][arm],
            plan["admission_contracts"][arm],
            scenario=next(iter(plan["scenarios"].values())),
            expected_rows=[],
            capability=plan["capabilities"][arm],
            artifact_path=None,
        )
    oracles = json.loads((output / "oracles.json").read_text(encoding="utf-8"))
    state = read_ledger(output / "ledger.jsonl")
    reconciliation = reconcile(plan["schedule"], state)
    if not reconciliation["complete"]:
        raise ValueError("ledger reconciliation")
    cells = {cell["cell_id"]: cell for cell in plan["schedule"]["cells"]}
    artifact_hashes: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for cell_id, terminal in state["states"].items():
        cell = cells[cell_id]
        result = terminal["result"]
        artifact_path = output / "artifacts" / f"cell-{cell_id}.json" if result["status"] == "ok" else None
        fresh.validate_fresh_result(
            result,
            plan["schedule"]["contracts"][cell["arm"]],
            scenario=plan["scenarios"][cell["case_id"]],
            expected_rows=oracles["cases"][cell["case_id"]],
            capability=plan["capabilities"][cell["arm"]],
            artifact_path=artifact_path,
        )
        if artifact_path is not None:
            artifact_hashes[cell["case_id"]][cell["arm"]].add(result["artifact"]["sha256"])
    deterministic = all(len(hashes) == 1 for arms in artifact_hashes.values() for hashes in arms.values())
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    if (
        summary.get("status") != "passed"
        or summary.get("performance_claim_permitted") is not False
        or summary.get("planned_cells") != len(cells)
        or summary.get("serialized_artifact_deterministic_across_blocks") is not deterministic
    ):
        raise ValueError("summary boundary")
    return {
        "status": "passed",
        "files": len(listed) + 1,
        "cells": len(cells),
        "ok": summary["cell_statuses"].get("ok", 0),
        "refused": summary["cell_statuses"].get("refused", 0),
        "mutated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        payload = sys.stdin.buffer.read(fresh.MAX_REQUEST_BYTES + 1)
        result = fresh.execute_worker(payload)
    elif args.command == "run":
        result = run(args.output)
    elif args.command == "verify":
        result = verify(args.output)
    else:
        parser.error("a command or --worker is required")
    sys.stdout.buffer.write(canonical_bytes(result) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
