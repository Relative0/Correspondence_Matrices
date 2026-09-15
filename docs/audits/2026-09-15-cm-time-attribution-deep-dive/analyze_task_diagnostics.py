"""Recompute task summaries from immutable new diagnostic records."""
from pathlib import Path
import hashlib
import json
import statistics
import task_diagnostics as td

AUDIT = Path(__file__).resolve().parent
SOURCE = AUDIT / "task-run-001" / "TASK_RESULTS.json"


def main():
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = []
    for record in doc["cells"]:
        out = {"cell": record["cell"], "status": record["status"]}
        if record["status"] != "ok":
            rows.append(out)
            continue
        samples = record["uninstrumented"]
        phases = record["phase_pass"]
        mean_total = statistics.mean(sample["wall_ns"] for sample in phases)
        mean_cpu_total = statistics.mean(sample["cpu_ns"] for sample in phases)
        keys = {key for sample in phases for key in sample["phases"]}
        out.update({
            "wall_median_ns": statistics.median(sample["wall_ns"] for sample in samples),
            "cpu_median_ns": statistics.median(sample["cpu_ns"] for sample in samples),
            "phase_mean_caller_ns": mean_total,
            "phase_mean_caller_cpu_ns": mean_cpu_total,
            "phase_dilation": statistics.median(sample["wall_ns"] for sample in phases) / statistics.median(sample["wall_ns"] for sample in samples),
            "phases": {key: {"mean_wall_ns": statistics.mean(sample["phases"].get(key, {}).get("wall_ns", 0) for sample in phases),
                              "mean_cpu_ns": statistics.mean(sample["phases"].get(key, {}).get("cpu_ns", 0) for sample in phases),
                              "percent_mean_caller_cpu": None if not mean_cpu_total else 100 * statistics.mean(sample["phases"].get(key, {}).get("cpu_ns", 0) for sample in phases) / mean_cpu_total,
                              "percent_mean_caller": 100 * statistics.mean(sample["phases"].get(key, {}).get("wall_ns", 0) for sample in phases) / mean_total}
                       for key in sorted(keys)},
            "traced_peak_bytes": record["memory_pass"]["peak_traced_bytes"],
            "traced_retained_bytes": record["memory_pass"]["current_traced_bytes"],
            "output_bytes": samples[0]["result"]["output_bytes"],
            "structure": record["structure"],
            "correct": record["correctness"]["every_sample_exact"],
            "profile_reference": "task-run-001/TASK_RESULTS.json#cells/"+str(len(rows))+"/profile",
            "memory_reference": "task-run-001/TASK_RESULTS.json#cells/"+str(len(rows))+"/memory_pass",
        })
        if "cache_counts" in phases[0]["result"]:
            out["cache_counts_in_separate_phase_pass"] = phases[0]["result"]["cache_counts"]
            out["uninstrumented_cache_hits"] = None
            out["uninstrumented_cache_misses"] = None
        if "legacy_fields" in samples[0]["result"]:
            prefix = "family_cm_cache" if record["cell"]["arm"].endswith("cache_on") else "family_cm_no_cache"
            raw = [sample["result"]["legacy_fields"] for sample in samples]
            out["public_family_legacy_medians_s"] = {
                "total": statistics.median(row[prefix+"_total_time_s"] for row in raw),
                "compile": statistics.median(row[prefix+"_compile_total_s"] for row in raw),
                "eval": statistics.median(row[prefix+"_eval_total_s"] for row in raw),
                "residual_conversion_guard_bookkeeping": statistics.median(
                    row[prefix+"_total_time_s"]-row[prefix+"_compile_total_s"]-row[prefix+"_eval_total_s"] for row in raw),
            }
            if prefix == "family_cm_cache":
                out["public_cache_counts"] = {key: raw[0][key] for key in (
                    "family_cm_cache_persistent_hits_total", "family_cm_cache_persistent_misses_total", "family_cm_cache_cache_size_final")}
        rows.append(out)
    family_context = {}
    _, _, cm, *_ = td.runtime()
    for case in {row["cell"]["case"] for row in rows if row["cell"]["task"] == "family"}:
        td.reset_caches()
        contexts = []
        for expr in td.family_for(case)["variants"]:
            _, shared = cm.CMIRBuilder._shared_assoc_uids(expr)
            key = "s1:"+cm._persistent_digest(expr, {}).hex()
            prior_root = key in cm._PERSISTENT_IR_CACHE
            diagnostic = {}
            cm.compile_expr_to_cm_ir(expr, diagnostics=diagnostic, reuse_cache=False, persistent_cache=True)
            contexts.append({"mode": "root_only" if shared else "subtree", "shared_associative_classes": len(shared),
                             "root_hit_before_compile": prior_root, "hits": diagnostic["ir_persistent_cache_hits"],
                             "misses": diagnostic["ir_persistent_cache_misses"], "cache_entries": diagnostic["ir_persistent_cache_size"]})
        family_context[case] = {"treatment": "separate untimed count/reuse-context reconstruction from disclosed fixture",
                                "variants": contexts, "root_hits": sum(row["root_hit_before_compile"] for row in contexts),
                                "root_only_variants": sum(row["mode"] == "root_only" for row in contexts)}
    result = {"schema": "cm-time-attribution-task-summary/v1", "source": str(SOURCE),
              "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              "corrections": ["Uninstrumented custom-family hit/miss zeros in task-run-001 are placeholders because diagnostics is None; only separate phase counts are measured, normalized here to null for uninstrumented counts.",
                              "CPU time resolution is coarse (observed nonzero increments include 15,625,000 ns); zero samples mean below observable process-time resolution, not no CPU work.",
                              "Public-family legacy medians are nested annotations and not added to exclusive phases; separate medians need not add exactly."],
              "elapsed_s": doc["elapsed_s"], "family_cache_context": family_context, "cells": rows}
    (AUDIT / "TASK_SUMMARY.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    lines = ["# Task diagnostic ledger", "", "Measured from `task-run-001/TASK_RESULTS.json`; uninstrumented medians, five repeats. Phases use their own separate pass denominator. See `TASK_METHODS.md` for contract and resolution limits.", "", "| Task / case | Arm / q | Wall median (ms) | CPU median (ms) | Output bytes | Traced peak bytes |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for row in rows:
        cell = row["cell"]
        lines.append(f"| {cell['task']} / {cell['case']} | {cell['arm']} / {cell['q']} | {row['wall_median_ns']/1e6:.4f} | {row['cpu_median_ns']/1e6:.4f} | {row['output_bytes']} | {row['traced_peak_bytes']} |")
    lines.extend(["", "## Public family measured subspans", "", "These are nested inside the public-family arm. Residual is computed per observation before taking its median, so the displayed independent medians need not add exactly. The surrounding diagnostic caller additionally includes disclosed fixture generation, reference creation and structural family diagnostics.", "", "| Case / persistence | Family total (ms) | Compile (ms) | Evaluate (ms) | Conversion/guard/bookkeeping residual (ms) |", "| --- | ---: | ---: | ---: | ---: |"])
    for row in rows:
        if "public_family_legacy_medians_s" in row:
            v = row["public_family_legacy_medians_s"]
            lines.append(f"| {row['cell']['case']} / {row['cell']['arm']} | {v['total']*1e3:.4f} | {v['compile']*1e3:.4f} | {v['eval']*1e3:.4f} | {v['residual_conversion_guard_bookkeeping']*1e3:.4f} |")
    (AUDIT / "TASK_LEDGER.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({"elapsed_s": doc["elapsed_s"], "cells": len(rows), "statuses": {status: sum(row['status']==status for row in rows) for status in {row['status'] for row in rows}}}))


if __name__ == "__main__":
    main()
