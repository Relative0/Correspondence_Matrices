"""Derive an additive reporting correction and a deferred local-only plan."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cmbench.biology_session_analysis import analyze_sessions
from cmbench.benchmark_contracts import mechanism_attribution, validate_result

OUT = ROOT / "docs/audits/2026-09-15-cm-biology-sessions"
PILOT = OUT / "pilot-002"
PRIOR = ROOT / "docs/audits/2026-09-14-cm-benchmark-attribution"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    original = [json.loads(s) for s in (PILOT / "ledger.jsonl").read_text().splitlines()]
    run = json.loads((PILOT / "RUN.json").read_text())
    assert run["status"] == "complete" and run["completed_cells"] == 288
    assert sha(PILOT / "ledger.jsonl") == run["ledger_sha256"]
    executed = json.loads((PILOT / "SOURCE_MANIFEST.json").read_text())
    for name, digest in executed["files"].items():
        assert sha(PILOT / "source" / name) == digest
    rows, amendments = [], []
    for old in original:
        row = json.loads(json.dumps(old))
        if row["status"] == "ok" and row["arm"] in {"bnet_scalar_oracle", "cadical195_enumeration"}:
            actual = mechanism_attribution(row["arm"])["preprocessing"]
            amendments.append({"cell_id": row["cell_id"], "before": row["preprocessing_policy"], "after": actual})
            row["preprocessing_policy"] = actual
            row["mechanism_attribution"]["preprocessing"] = actual
        validate_result(row)
        # Outputs, resources, timings, identities and all other fields untouched.
        for key in old.keys() - {"preprocessing_policy", "mechanism_attribution"}:
            assert row[key] == old[key]
        rows.append(row)
    corrected = OUT / "REPORTING_CORRECTED_LEDGER.jsonl"
    corrected.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    write("REPORTING_ADDENDUM.json", {"scope": "preprocessing label correction only; no timing or exact output changes",
        "original_ledger_sha256": sha(PILOT / "ledger.jsonl"), "corrected_ledger_sha256": sha(corrected),
        "amendments": amendments, "executed_source_snapshot": "pilot-002/source",
        "future_worker_fix": "control rows no longer report the factorized normalization policy"})
    analysis = analyze_sessions(rows)
    assert not analysis["correctness_mismatches"]
    write("ANALYSIS.json", analysis)
    summaries = []
    for comparison in analysis["comparisons"]:
        q, reuse, representation = (comparison[k] for k in ("queries", "reuse_mode", "representation_mode"))
        ids = {r["instance_id"] for r in rows if r["status"] == "ok" and r["queries"] == q
               and r["arm"] == "prepared_cm_factorized" and r["reuse_mode"] == reuse and r["representation_mode"] == representation}
        pairs = [r for r in rows if r["status"] == "ok" and r["queries"] == q and r["instance_id"] in ids
                 and r["reuse_mode"] == reuse and (r["arm"] == "raw_factorized" or
                 r["arm"] == "prepared_cm_factorized" and r["representation_mode"] == representation)]
        worker = {arm: sum(r["worker_total_seconds"] for r in pairs if r["arm"] == arm)
                  for arm in ("raw_factorized", "prepared_cm_factorized")}
        summaries.append({"queries": q, "reuse_mode": reuse, "representation_mode": representation,
            "paired_instances": comparison["summary"]["paired_instances"],
            "clusters": comparison["summary"]["independent_cluster_count_assumption"],
            "family_ratio": comparison["summary"]["equal_family_geometric_mean_ratio"],
            "sum_total_ratio": comparison["summary"]["ratio_sum_instance_mean_total_cost"],
            "worker_only_sum_ratio": worker["prepared_cm_factorized"] / worker["raw_factorized"],
            "plan_attribution_counts": comparison["plan_attribution_counts"]})
    write("SUMMARY.json", {"cells": len(rows), "status_counts": dict(Counter(r["status"] for r in rows)),
        "elapsed_seconds": run["elapsed_seconds"], "comparisons": summaries,
        "timeouts": [r["cell_id"] for r in rows if r["status"] == "timeout"],
        "unsupported": [{"cell_id": r["cell_id"], "reason": r["failure_reason"]} for r in rows if r["status"] == "unsupported"],
        "checked_witnesses": sum(bool(o["satisfiable"]) for r in rows if r["status"] == "ok" for o in r["outputs"]),
        "successful_query_outputs": sum(len(r["outputs"]) for r in rows if r["status"] == "ok"),
        "maximum_peak_committed_bytes": max(r["peak_memory_bytes"] for r in rows),
        "cleanup_verified_every_session": all(r["supervisor"]["cleanup_verified"] for r in rows),
        "heldout_gate": "not eligible and not passed; no 5-percent development total-cost signal"})
    sources = dict(executed["files"])
    sources.update({name: sha(ROOT / name) for name in sources})
    for name in ("scripts/cm_biology_sessions_finalize.py", "tests/test_cm_biology_sessions.py",
                 "tests/test_cm_biology_supervisor.py", "tests/test_cm_biology_session_analysis.py", "tests/test_cm_biology_session_runner.py",
                 "tests/test_cm_biology_session_evidence.py"):
        sources[name] = sha(ROOT / name)
    write("SOURCE_MANIFEST.json", {"status": "future_corrected_reporting_source", "files": sources})
    corpus = json.loads((PRIOR / "BIOLOGY_CORPUS_AUDIT.json").read_text())
    models = {m["model_id"]: m for m in corpus["models"]}
    schedules = json.loads((PRIOR / "QUERY_SCHEDULES.json").read_text())
    cells = []
    for repetition in range(3):
        for model in schedules["models"]:
            for q in (1, 8, 64):
                arms = ["raw_factorized", "prepared_cm_factorized"]
                if (int(model["model_id"]) + repetition + q) % 2: arms.reverse()
                for arm in arms:
                    cells.append({"cell_id": f'{model["model_id"]}-q{q}-{arm}-r{repetition}',
                        "instance_id": model["model_id"], "input_sha256": model["input_sha256"],
                        "query_schedule_sha256": model["query_schedule_sha256"], "cluster_id": model["cluster_id"],
                        "partition": models[model["model_id"]]["recommended_partition"],
                        "queries": q, "arm": arm, "reuse_mode": "retained", "representation_mode": "matched", "repetition": repetition})
    # This is a frozen design, not an executable continuation or new authority.
    write("NEXT_LOCAL_PLAN.json", {"schema": "cm-biology-prospective-local-replication/v1",
        "status": "deferred_no_development_signal", "execution_authorized_by_this_file": False,
        "reason": "Matched q64 family ratio is at parity rather than a 5% gain; no distinct warm algorithm mechanism. Revisit only after a justified change or explicit replication request.",
        "source_manifest_sha256": sha(OUT / "SOURCE_MANIFEST.json"), "prior_pilot_plan_sha256": sha(PILOT / "PLAN.json"),
        "query_schedules_sha256": sha(PRIOR / "QUERY_SCHEDULES.json"), "corpus_sha256": sha(PRIOR / "BIOLOGY_CORPUS_AUDIT.json"),
        "cells": cells, "total_cells": len(cells), "closed_models": 22, "repetitions": 3,
        "session_deadline_seconds": 10, "total_wall_budget_seconds": 900, "process_tree_memory_bytes": 1 << 30,
        "feasibility": "396 matched retained sessions; 15-minute global ceiling with explicit not-run rows if exhausted. Pilot total 288 mixed sessions took about 190 seconds; extrapolation to unmeasured models is uncertain.",
        "paid_compute": False, "heldout_acceptance": "ineligible: existing exposed corpus; partitions do not create pristine heldout evidence"})
    print(json.dumps({"statuses": dict(Counter(r["status"] for r in rows)), "label_corrections": len(amendments), "future_cells": len(cells), "summary": summaries}))


if __name__ == "__main__": main()
