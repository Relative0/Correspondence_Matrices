"""Run or verify cached-real structural persistence and trace-provenance evidence.

Eight already selected conditioned k=8 feature-model cases are used only for
bounded functional verification.  CM, structural CSE and the direct-CNF
control serialize, decode, reconstruct and query every version under a balanced
six-block plan.  The associated task traces are saved as generated controls
and explicitly do not satisfy the natural-session evidence gate.  Timings are
diagnostic only.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import persistence, traces
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.evidence import append_record, publish_json, read_ledger, reconcile
from cmbench.comparative.schedule import build_plan, validate_plan
from scripts import cm_comparative_real_task_bridge as bridge
from scripts.cm_benchmark_provenance import capture_source_snapshot


SCHEMA = "cm-comparative-persistence-pilot/v2"
CHECKSUM_SCHEMA = "cm-comparative-persistence-checksums/v2"
SEED = 2026082904
SOURCES = (
    "scripts/cm_comparative_persistence_pilot.py",
    "tests/test_cm_comparative_persistence_pilot.py",
    "cmbench/comparative/persistence.py",
    "cmbench/comparative/traces.py",
    "tests/test_cm_comparative_persistence.py",
    "tests/test_cm_comparative_traces.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/tasks.py",
    "cmbench/comparative/arms.py",
    "cmbench/comparative/evidence.py",
    "cmbench/comparative/schedule.py",
    "scripts/cm_comparative_real_task_bridge.py",
    "scripts/cm_comparative_task_pilot.py",
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
    bridge.sessions.HISTORY,
    bridge.sessions.ADMISSIONS,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def _source_rows() -> list[dict[str, Any]]:
    return [
        {"path": name, "sha256": sha256_file(ROOT / name), "bytes": (ROOT / name).stat().st_size}
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


def build_bundle(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    scenarios, selection = bridge.cohort(root)
    cases = []
    scenario_lookup: dict[str, dict[str, Any]] = {}
    oracle_rows: dict[str, list[dict[str, Any]]] = {}
    for index, scenario in enumerate(scenarios):
        case_id = f"case-{index:02}"
        scenario_lookup[case_id] = scenario
        scenario_sha = hashlib.sha256(canonical_bytes(scenario)).hexdigest()
        cases.append(
            {
                "case_id": case_id,
                "cluster_id": scenario["source"]["history"],
                "input_sha256": scenario_sha,
            }
        )
        oracle_rows[case_id] = persistence.scalar_oracle(scenario)
    contracts = {
        backend: persistence.persistence_contract(
            contract_id=f"real-persistence-{backend}",
            backend=backend,
            k=8,
            queries=2,
        )
        for backend in persistence.BACKENDS
    }
    schedule = build_plan(
        campaign_id="real-persistence-v2",
        cases=cases,
        arms=persistence.BACKENDS,
        contracts=contracts,
        blocks=6,
        locality="round_robin",
        seed=SEED,
        shard_cells=32,
    )
    trace_corpus = traces.generated_control_corpus(
        corpus_id="cached-real-generated-context-controls-v1",
        scenarios=scenario_lookup,
        trace_map=bridge.bridge_traces(),
    )
    trace_audit = traces.validate_corpus(trace_corpus, scenario_lookup)
    if trace_audit["natural_claim_permitted"] or trace_audit["natural_trace_count"]:
        raise ValueError("generated bridge traces mislabeled as natural")
    plan = {
        "schema": SCHEMA,
        "schedule": schedule,
        "scenarios": scenario_lookup,
        "selection": selection,
        "performance_claim_permitted": False,
        "timings_for_contract_diagnostics_only": True,
    }
    return plan, {"schema": SCHEMA, "cases": oracle_rows}, {
        "corpus": trace_corpus,
        "audit": trace_audit,
        "acquisition_status": "no observed natural configurator trace supplied or found locally",
    }


def run(output: Path) -> dict[str, Any]:
    output = _safe_output(output)
    before = _source_rows()
    snapshot = capture_source_snapshot(ROOT, output / "source_snapshot", SOURCES)
    plan, oracles, trace_document = build_bundle(ROOT)
    publish_json(output / "plan.json", {**plan, "source_manifest_sha256": snapshot["manifest_sha256"]})
    publish_json(output / "oracles.json", oracles)
    publish_json(output / "trace-provenance.json", trace_document)

    ledger = output / "ledger.jsonl"
    artifact_hashes: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    result_counts: Counter[str] = Counter()
    for cell in plan["schedule"]["cells"]:
        if _source_rows() != before:
            raise ValueError("working source changed during persistence pilot")
        scenario = plan["scenarios"][cell["case_id"]]
        contract = plan["schedule"]["contracts"][cell["arm"]]
        request = {"cell": cell, "scenario_sha256": cell["input_sha256"]}
        request_sha = hashlib.sha256(canonical_bytes(request)).hexdigest()
        append_record(ledger, {"cell_id": cell["cell_id"], "status": "running", "request_sha256": request_sha})
        result = persistence.execute_persistence(
            scenario=scenario,
            backend=cell["arm"],
            contract=contract,
            case_id=cell["case_id"],
        )
        persistence.validate_persistence_result(
            result,
            contract,
            scenario=scenario,
            expected_rows=oracles["cases"][cell["case_id"]],
            expected_backend=cell["arm"],
            expected_case_id=cell["case_id"],
        )
        append_record(
            ledger,
            {
                "cell_id": cell["cell_id"],
                "status": "ok",
                "request_sha256": request_sha,
                "result": result,
            },
        )
        artifact_hashes[cell["case_id"]][cell["arm"]].add(result["artifact"]["sha256"])
        result_counts[cell["arm"]] += 1

    after = _source_rows()
    if before != after:
        raise ValueError("working source changed during persistence pilot")
    state = read_ledger(ledger)
    reconciliation = reconcile(plan["schedule"], state)
    if not reconciliation["complete"] or reconciliation["statuses"] != {"ok": len(plan["schedule"]["cells"])}:
        raise ValueError("persistence pilot did not reconcile")
    if any(len(hashes) != 1 for arms in artifact_hashes.values() for hashes in arms.values()):
        raise ValueError("serialized artifact changed across repeated blocks")
    summary = {
        "schema": SCHEMA,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "case_count": len(plan["scenarios"]),
        "backend_count": len(persistence.BACKENDS),
        "blocks": plan["schedule"]["blocks"],
        "planned_cells": len(plan["schedule"]["cells"]),
        "cells_by_backend": dict(sorted(result_counts.items())),
        "versions_reloaded_per_cell": 2,
        "exact_relation_rows": len(plan["schedule"]["cells"]) * 2,
        "serialized_artifact_deterministic_across_blocks": True,
        "trace_audit": trace_document["audit"],
        "natural_trace_acquisition_status": trace_document["acquisition_status"],
        "reconciliation": reconciliation,
        "source_unchanged": True,
        "cloud_run": False,
        "network_used": False,
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "limitations": [
            "conditioned k=8 feature-model slices rather than full models",
            "CM, CSE and direct CNF only; native CUDD/ZDD/d4 persistence remains gated",
            "in-process functional checks without comparable RSS or fresh-process timing",
            "associated contexts are generated controls, not observed natural sessions",
            "artifact hashes establish deterministic bytes within a backend/case, not cross-backend identity",
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

    source_manifest = json.loads((output / "source_snapshot/source_manifest.json").read_text(encoding="utf-8"))
    for row in source_manifest["files"]:
        path = output / "source_snapshot" / row["path"]
        if path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError("source snapshot identity")
    plan = json.loads((output / "plan.json").read_text(encoding="utf-8"))
    validate_plan(plan["schedule"])
    oracles = json.loads((output / "oracles.json").read_text(encoding="utf-8"))
    trace_document = json.loads((output / "trace-provenance.json").read_text(encoding="utf-8"))
    trace_audit = traces.validate_corpus(trace_document["corpus"], plan["scenarios"])
    if trace_audit != trace_document["audit"] or trace_audit["natural_claim_permitted"]:
        raise ValueError("trace provenance audit")
    state = read_ledger(output / "ledger.jsonl")
    if not reconcile(plan["schedule"], state)["complete"]:
        raise ValueError("ledger reconciliation")
    cells = {cell["cell_id"]: cell for cell in plan["schedule"]["cells"]}
    for cell_id, terminal in state["states"].items():
        cell = cells[cell_id]
        persistence.validate_persistence_result(
            terminal["result"],
            plan["schedule"]["contracts"][cell["arm"]],
            scenario=plan["scenarios"][cell["case_id"]],
            expected_rows=oracles["cases"][cell["case_id"]],
            expected_backend=cell["arm"],
            expected_case_id=cell["case_id"],
        )
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "passed" or summary.get("performance_claim_permitted") is not False or \
            summary.get("planned_cells") != len(cells):
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
