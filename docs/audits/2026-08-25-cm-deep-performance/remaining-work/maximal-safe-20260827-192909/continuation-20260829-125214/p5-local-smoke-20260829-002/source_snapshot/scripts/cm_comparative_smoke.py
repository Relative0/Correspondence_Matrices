"""Create or verify the bounded, non-performance comparative P5 smoke bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cmbench.comparative.arms import execute_arm, scalar_relation, semantic_sha256
from cmbench.comparative.contracts import CONTRACT_SCHEMA, canonical_bytes, validate_result
from cmbench.comparative.evidence import append_record, publish_json, read_ledger, reconcile
from cmbench.comparative.readiness import environment_record
from cmbench.comparative.schedule import build_plan, validate_plan


SMOKE_SCHEMA = "cm-comparative-local-smoke/v1"
ARMS = ("cm_dense", "cm_flat_bigint", "cm_flat_words", "cm_no_reinflate", "cse_flat", "raw_flat")
KINDS = {
    "cm_dense": "dense_cm",
    "cm_flat_bigint": "packed_bigint",
    "cm_flat_words": "packed_words",
    "cm_no_reinflate": "packed_bigint",
    "cse_flat": "packed_bigint",
    "raw_flat": "packed_bigint",
}
SOURCES = (
    "scripts/cm_comparative_smoke.py",
    "cmbench/comparative/__init__.py",
    "cmbench/comparative/arms.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/evidence.py",
    "cmbench/comparative/ir.py",
    "cmbench/comparative/readiness.py",
    "cmbench/comparative/schedule.py",
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cm_normalize.py",
    "cmbench/output_budget.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _contract(arm: str, variables: tuple[str, ...]) -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA,
        "contract_id": f"p5-{arm}",
        "task": "complete_relation",
        "artifact": {
            "kind": KINDS[arm],
            "variable_order": list(variables),
            "output_order": list(variables),
            "fixed": [],
            "output_scope": "full",
            "restoration": "none",
            "stream": None,
        },
        "lifecycle": "resident_engine",
        "queries": 1,
        "validation": {
            "oracle": "independent_scalar_assignment/v1",
            "validation_in_timed_span": False,
            "required_output_sha256": None,
        },
    }


def smoke_cases() -> list[dict[str, Any]]:
    shared = Xor(Var(0), Var(1))
    expressions = (
        ("sharing-unused-k8", "synthetic-sharing", Eqv(And(shared, shared), Imp(Var(4), Or(Var(2), Var(5)))), 8),
        ("mixed-k8", "synthetic-mixed", And(Or(Var(0), Not(Var(7))), Xor(Eqv(Var(1), Var(6)), Imp(Var(2), And(Var(3), Var(5))))), 8),
    )
    cases = []
    for case_id, cluster_id, expr, k in expressions:
        document = expr_to_json_dag(expr)
        payload = canonical_bytes(document)
        variables = tuple(f"x{index}" for index in range(k))
        bits = scalar_relation(expr, variables, {})
        cases.append({
            "case_id": case_id,
            "cluster_id": cluster_id,
            "k": k,
            "variables": list(variables),
            "expression_v2": document,
            "input_sha256": hashlib.sha256(payload).hexdigest(),
            "oracle_sha256": semantic_sha256(bits, k),
            "oracle": "independent_scalar_assignment/v1",
        })
    return cases


def _source_rows(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for name in SOURCES:
        path = source_root / name
        payload = path.read_bytes()
        rows.append({"path": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    return rows


def _safe_new_output(output: Path, source_root: Path) -> Path:
    output = output.absolute()
    source_root = source_root.resolve()
    if output.exists() or not output.parent.exists():
        raise ValueError("output must be a new path under an existing project directory")
    resolved_parent = output.parent.resolve()
    if not resolved_parent.is_relative_to(source_root):
        raise ValueError("output must remain under the project root")
    for parent in (resolved_parent, *resolved_parent.parents):
        if parent == source_root.parent:
            break
        if parent.is_symlink() or parent.is_junction():
            raise ValueError("linked output path refused")
    output.mkdir()
    return output


def _copy_snapshot(output: Path, rows: list[dict[str, Any]], source_root: Path) -> dict[str, Any]:
    destination = output / "source_snapshot"
    destination.mkdir()
    for row in rows:
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = (source_root / row["path"]).read_bytes()
        if hashlib.sha256(payload).hexdigest() != row["sha256"]:
            raise ValueError("source changed during snapshot")
        target.write_bytes(payload)
    manifest = {
        "schema": "cm-comparative-source-manifest/v1",
        "secrets_included": False,
        "files": rows,
    }
    publish_json(destination / "source-manifest.json", manifest)
    return manifest


def _checksums(output: Path) -> dict[str, Any]:
    files = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "checksums.json"):
        files.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"schema": "cm-comparative-checksums/v1", "files": files}


def run_smoke(output: Path, *, source_root: Path = ROOT) -> dict[str, Any]:
    output = _safe_new_output(output, source_root)
    before = _source_rows(source_root)
    _copy_snapshot(output, before, source_root)
    cases = smoke_cases()
    # Every case has a declared full 8-axis contract. The sharing case leaves
    # two axes unused so the output contract's unused-variable rule is tested.
    variables = tuple(f"x{index}" for index in range(8))
    contracts = {arm: _contract(arm, variables) for arm in ARMS}
    plan_cases = [
        {"case_id": row["case_id"], "cluster_id": row["cluster_id"], "input_sha256": row["input_sha256"]}
        for row in cases
    ]
    plan = build_plan(
        campaign_id="p5-local-smoke-v1",
        cases=plan_cases,
        arms=ARMS,
        contracts=contracts,
        blocks=12,
        locality="round_robin",
        seed=29082026,
        shard_cells=36,
    )
    publish_json(output / "cases.json", {"schema": SMOKE_SCHEMA, "cases": cases})
    publish_json(output / "plan.json", plan)
    publish_json(output / "environment.json", environment_record())
    case_map = {row["case_id"]: row for row in cases}
    ledger = output / "ledger.jsonl"
    for cell in plan["cells"]:
        case = case_map[cell["case_id"]]
        request_sha256 = hashlib.sha256(canonical_bytes({"cell": cell, "input": case["input_sha256"]})).hexdigest()
        append_record(ledger, {"cell_id": cell["cell_id"], "status": "running", "request_sha256": request_sha256})
        expr = expr_from_json(case["expression_v2"])
        result = execute_arm(
            expr=expr,
            contract=contracts[cell["arm"]],
            case_id=cell["case_id"],
            arm=cell["arm"],
            smoke_bound=8,
        )
        expected = semantic_sha256(scalar_relation(expr, variables, {}), len(variables))
        if expected != result["artifact"]["sha256"]:
            result = {**result, "status": "mismatch", "reason": "external_scalar_digest_mismatch", "artifact": None}
        validate_result(result, contracts[cell["arm"]])
        append_record(ledger, {
            "cell_id": cell["cell_id"],
            "status": result["status"],
            "request_sha256": request_sha256,
            "result": result,
            "validation": {"outside_timed_span": True, "expected_sha256": expected},
        })
    after = _source_rows(source_root)
    if before != after:
        raise ValueError("working sources changed during smoke")
    state = read_ledger(ledger)
    reconciliation = reconcile(plan, state)
    if not reconciliation["complete"] or reconciliation["statuses"] != {"ok": len(plan["cells"])}:
        raise ValueError("local smoke did not reconcile cleanly")
    summary = {
        "schema": SMOKE_SCHEMA,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "maximum_k": 8,
        "cases": len(cases),
        "arms": len(ARMS),
        "planned_cells": len(plan["cells"]),
        "reconciliation": reconciliation,
        "source_unchanged": True,
        "cleanup": "in_process_no_descendants",
        "limitations": [
            "timings are schema/accounting smoke data only",
            "native adapters were inventoried but not executed",
            "Linux cgroup and process-tree controls require the Runpod readiness scout",
        ],
    }
    publish_json(output / "summary.json", summary)
    publish_json(output / "checksums.json", _checksums(output))
    return summary


def verify_smoke(output: Path) -> dict[str, Any]:
    output = output.resolve()
    checksums = json.loads((output / "checksums.json").read_text(encoding="utf-8"))
    if checksums.get("schema") != "cm-comparative-checksums/v1" or not isinstance(checksums.get("files"), list):
        raise ValueError("checksum manifest")
    expected_paths = []
    for row in checksums["files"]:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise ValueError("checksum row")
        path = output.joinpath(*Path(row["path"]).parts)
        if not path.resolve().is_relative_to(output) or not path.is_file():
            raise ValueError("checksum path")
        if path.stat().st_size != row["bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError("checksum mismatch")
        expected_paths.append(row["path"])
    actual_paths = sorted(path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file() and path.name != "checksums.json")
    if expected_paths != actual_paths:
        raise ValueError("checksum coverage")
    source_manifest = json.loads((output / "source_snapshot" / "source-manifest.json").read_text(encoding="utf-8"))
    if source_manifest.get("secrets_included") is not False:
        raise ValueError("source secret boundary")
    for row in source_manifest["files"]:
        path = output / "source_snapshot" / row["path"]
        if path.stat().st_size != row["bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError("source snapshot mismatch")
    plan = json.loads((output / "plan.json").read_text(encoding="utf-8"))
    validate_plan(plan)
    cases_doc = json.loads((output / "cases.json").read_text(encoding="utf-8"))
    cases = {row["case_id"]: row for row in cases_doc["cases"]}
    state = read_ledger(output / "ledger.jsonl")
    result = reconcile(plan, state)
    if not result["complete"]:
        raise ValueError("ledger reconciliation")
    for cell_id, terminal in state["states"].items():
        cell = next(row for row in plan["cells"] if row["cell_id"] == cell_id)
        validate_result(terminal["result"], plan["contracts"][cell["arm"]])
        if terminal["result"]["artifact"]["sha256"] != terminal["validation"]["expected_sha256"]:
            raise ValueError("oracle mismatch")
        if cell["case_id"] not in cases:
            raise ValueError("case coverage")
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "passed" or summary.get("performance_claim_permitted") is not False:
        raise ValueError("smoke summary")
    return {"status": "passed", "files": len(expected_paths) + 1, "cells": len(plan["cells"]), "mutated": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_smoke(args.output) if args.command == "run" else verify_smoke(args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
