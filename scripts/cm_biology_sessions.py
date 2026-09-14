"""Freeze and execute a local-only development pilot, with no remote actions."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PRIOR = ROOT / "docs/audits/2026-09-14-cm-benchmark-attribution"
from cmbench.benchmark_contracts import SCHEMA, mechanism_attribution, validate_result
from cmbench.biology_sessions import canonical_json
from cmbench.biology_session_supervisor import run_worker
from cmbench.biology_session_analysis import analyze_sessions

SOURCE_FILES = [
    "scripts/cm_biology_sessions.py", "cmbench/biology_sessions.py", "cmbench/biology_session_supervisor.py",
    "cmbench/biology_session_analysis.py", "cmbench/benchmark_contracts.py", "cmbench/biology_bnet.py",
    "cmbench/biology_controls.py", "cmbench/backends/factorized_counts.py", "cmbench/backends/packed_queries.py",
    "cmbench/backends/packed_mask_cache.py", "bitset_backend.py", "cm_ir.py", "cm_exprlib.py",
]
VARIANTS = [
    ("raw_factorized", "retained", "matched"), ("prepared_cm_factorized", "retained", "matched"),
    ("raw_factorized", "rebuild", "matched"), ("prepared_cm_factorized", "rebuild", "matched"),
    ("prepared_cm_factorized", "retained", "cm_canonical"), ("explicit_packed_cm", "retained", "matched"),
    ("bnet_scalar_oracle", "retained", "matched"), ("cadical195_enumeration", "retained", "matched"),
]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare(output):
    output.mkdir(parents=True, exist_ok=False)
    corpus = json.loads((PRIOR / "BIOLOGY_CORPUS_AUDIT.json").read_text())
    schedules = json.loads((PRIOR / "QUERY_SCHEDULES.json").read_text())
    models = {m["model_id"]: m for m in corpus["models"]}
    source = {name: sha(ROOT / name) for name in SOURCE_FILES}
    for name in SOURCE_FILES:
        snapshot = output / "source" / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes((ROOT / name).read_bytes())
    write(output / "SOURCE_MANIFEST.json", {"files": source})
    cells = []
    for schedule in schedules["models"]:
        model = models[schedule["model_id"]]
        if model["recommended_partition"] != "development":
            continue
        path = PRIOR / "control-inputs" / (model["model_id"] + ".bnet")
        if sha(path) != schedule["input_sha256"]:
            raise ValueError("frozen input mismatch")
        if hashlib.sha256(canonical_json(schedule["queries"])).hexdigest() != schedule["query_schedule_sha256"]:
            raise ValueError("frozen query schedule mismatch")
        for q in (1, 8, 64):
            # Rotate the fixed arm order per model/q. Record the exact order;
            # single-repetition pilot is not claimed as fully counterbalanced.
            offset = int(hashlib.sha256(f'{model["model_id"]}:{q}'.encode()).hexdigest(), 16) % len(VARIANTS)
            ordered = VARIANTS[offset:] + VARIANTS[:offset]
            for arm, reuse, representation in ordered:
                cells.append({"cell_id": f'{model["model_id"]}-q{q}-{arm}-{reuse}-{representation}',
                    "instance_id": model["model_id"], "path": str(path), "input_sha256": schedule["input_sha256"],
                    "cluster_id": schedule["cluster_id"], "partition": "development", "repetition": 0,
                    "arm": arm, "reuse_mode": reuse, "representation_mode": representation, "queries": q,
                    "query_schedule": schedule["queries"], "query_schedule_sha256": schedule["query_schedule_sha256"],
                    "perturbation_semantics": "clamp", "max_width": 20, "cache_bytes": 64 << 20})
    plan = {"schema": "cm-biology-local-session-plan/v1", "stage": "development_single_repetition_pilot",
        "authorization": "local only; no paid/cloud/external mutations", "total_wall_budget_seconds": 900,
        "session_deadline_seconds": 10, "process_tree_memory_bytes": 1 << 30, "output_limit_bytes": 1 << 20,
        "source_manifest_sha256": sha(output / "SOURCE_MANIFEST.json"),
        "corpus_sha256": sha(PRIOR / "BIOLOGY_CORPUS_AUDIT.json"), "schedules_sha256": sha(PRIOR / "QUERY_SCHEDULES.json"),
        "corpus_coverage": [{"model_id": s["model_id"], "partition": models[s["model_id"]]["recommended_partition"],
                            "input_sha256": s["input_sha256"], "selected_for_pilot": models[s["model_id"]]["recommended_partition"] == "development"} for s in schedules["models"]],
        "cells": cells, "performance_gate": "not eligible; exposed development pilot"}
    write(output / "PLAN.json", plan)
    print(json.dumps({"plan": str(output / "PLAN.json"), "cells": len(cells)}))


def execute(output):
    if (output / "ledger.jsonl").exists():
        raise ValueError("refuse to overwrite existing run")
    plan = json.loads((output / "PLAN.json").read_text())
    manifest_path = output / "SOURCE_MANIFEST.json"
    if sha(manifest_path) != plan["source_manifest_sha256"]:
        raise ValueError("source manifest mismatch")
    manifest = json.loads(manifest_path.read_text())
    for relative, expected in manifest["files"].items():
        if sha(ROOT / relative) != expected:
            raise ValueError(f"source changed since plan: {relative}")
    if sha(PRIOR / "BIOLOGY_CORPUS_AUDIT.json") != plan["corpus_sha256"] or sha(PRIOR / "QUERY_SCHEDULES.json") != plan["schedules_sha256"]:
        raise ValueError("corpus or schedules changed since plan")
    if plan["total_wall_budget_seconds"] != 900 or plan["session_deadline_seconds"] != 10 or plan["process_tree_memory_bytes"] != 1 << 30:
        raise ValueError("local pilot bounds changed")
    environment = {"platform": platform.platform(), "python": sys.version, "executable": sys.executable,
                   "numpy": importlib.metadata.version("numpy"), "python_sat": importlib.metadata.version("python-sat"),
                   "scope": "local Windows job; single assigned CPU; peak committed memory, not RSS"}
    environment_id = hashlib.sha256(canonical_json(environment)).hexdigest()
    write(output / "ENVIRONMENT.json", environment)
    requests = output / "requests"
    requests.mkdir()
    started = time.perf_counter()
    rows = []
    with (output / "ledger.jsonl").open("x", encoding="utf-8") as ledger:
        for index, cell in enumerate(plan["cells"]):
            remaining = plan["total_wall_budget_seconds"] - (time.perf_counter() - started)
            if remaining <= 0:
                break
            path = requests / (cell["cell_id"] + ".json")
            write(path, cell)
            measured = run_worker([sys.executable, "-m", "cmbench.biology_sessions", "--worker", str(path)],
                cwd=ROOT, timeout_seconds=min(10, remaining), memory_limit_bytes=1 << 30, max_output_bytes=1 << 20)
            payload = {}
            if measured["status"] == "ok":
                try:
                    payload = json.loads(measured["stdout"])
                except (json.JSONDecodeError, TypeError):
                    payload = {"status": "backend_error", "failure_reason": "worker output is not one JSON value"}
            else:
                payload = {"status": measured["status"], "failure_reason": measured.get("reason", "supervisor failure")}
            row = {k: v for k, v in cell.items() if k not in {"path", "query_schedule", "max_width", "cache_bytes"}}
            row.update(schema=SCHEMA, source_manifest_sha256=plan["source_manifest_sha256"],
                environment_id=environment_id, mechanism_attribution=mechanism_attribution(cell["arm"]),
                peak_memory_bytes=measured.get("peak_memory_bytes") or 0,
                memory_scope=measured.get("memory_scope") or "unavailable_supervisor_failure",
                supervisor={k: v for k, v in measured.items() if k not in {"stdout", "stderr"}})
            row.update(payload)
            row["worker_total_seconds"] = payload.get("timing_seconds", {}).get("total_session")
            row["phase_timing_available"] = "timing_seconds" in payload
            row["timing_seconds"] = {**{"cold_construction": 0., "preparation": 0., "warm_queries": 0.},
                                      **payload.get("timing_seconds", {}), "total_session": measured["wall_seconds"]}
            if row["status"] != "ok":
                row["outputs"] = None
                row.setdefault("failure_reason", "worker did not complete")
            row["mechanism_attribution"]["preprocessing"] = payload.get("preprocessing_policy", "not_completed")
            row["mechanism_attribution"]["category"] = "CM-associated but algorithmically general" if cell["arm"] in {"raw_factorized", "prepared_cm_factorized", "explicit_packed_cm"} else "correctness/control evidence"
            validate_result(row)
            rows.append(row)
            ledger.write(json.dumps(row, sort_keys=True) + "\n")
            ledger.flush()
            if not measured.get("cleanup_verified", False):
                raise RuntimeError("worker cleanup not verified; stop pilot")
            if (index + 1) % 12 == 0:
                print(json.dumps({"completed": index + 1, "cells": len(plan["cells"]), "elapsed_seconds": time.perf_counter() - started,
                                  "statuses": dict(Counter(r["status"] for r in rows))}), flush=True)
            # Stop on the first observed disagreement; do not continue ranking.
            if analyze_sessions(rows)["correctness_mismatches"]:
                break
    analysis = analyze_sessions(rows)
    write(output / "ANALYSIS.json", analysis)
    completed = {r["cell_id"] for r in rows}
    write(output / "RUN.json", {"schema": "cm-biology-local-run/v1", "plan_sha256": sha(output / "PLAN.json"),
        "status": "complete" if len(rows) == len(plan["cells"]) else "stopped_incomplete",
        "cells": len(plan["cells"]), "completed_cells": len(rows),
        "status_counts": dict(Counter(r["status"] for r in rows)), "elapsed_seconds": time.perf_counter() - started,
        "not_run": [c["cell_id"] for c in plan["cells"] if c["cell_id"] not in completed],
        "correctness_mismatches": analysis["correctness_mismatches"], "ledger_sha256": sha(output / "ledger.jsonl"),
        "cloud_operations": 0})
    print(json.dumps({"completed": len(rows), "planned": len(plan["cells"]), "correctness_mismatches": len(analysis["correctness_mismatches"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "execute"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    (prepare if args.phase == "prepare" else execute)(args.output.resolve())
