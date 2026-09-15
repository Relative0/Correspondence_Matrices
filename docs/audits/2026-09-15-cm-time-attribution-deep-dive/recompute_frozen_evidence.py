"""Read-only arithmetic over measured predecessor records; never loads fixtures.

Run with the existing project interpreter. Output is confined to this audit.
No benchmark modules are imported and no timed work or new cases are run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = OUT.parents[2]
ROOT = Path("C:/Users/brian/Documents/CM_Computation")
SOURCES: dict[str, dict] = {}


def read(relative: str, *, root: bool = False):
    path = (ROOT if root else BASE) / relative
    data = path.read_bytes()
    SOURCES[str(path)] = {
        "path": str(path), "repository_relative_path": relative,
        "origin": "dirty_root_read_only_predecessor" if root else "exact_commit_worktree",
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
    }
    return data.decode("utf-8-sig")


def obj(relative: str, *, root: bool = False):
    text = read(relative, root=root)
    return [json.loads(line) for line in text.splitlines() if line] if relative.endswith(".jsonl") else json.loads(text)


def stats(values):
    return {"count": len(values), "sum": sum(values), "median": statistics.median(values),
            "mean": statistics.mean(values), "min": min(values), "max": max(values)} if values else None


def summarize(rows, keys, fields):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(key) for key in keys)].append(row)
    result = []
    for key, group in sorted(grouped.items(), key=lambda item: repr(item[0])):
        summary = dict(zip(keys, key))
        summary["rows"] = len(group)
        summary["metrics"] = {field: stats([r[field] for r in group if isinstance(r.get(field), (int, float))]) for field in fields}
        result.append(summary)
    return result


def phase_summary(rows, keys, total, stage_names):
    summaries = summarize(rows, keys, [total, *stage_names])
    for summary in summaries:
        aggregate = summary["metrics"][total]["sum"]
        summary["aggregate_phase_percent"] = {
            name: 100 * summary["metrics"][name]["sum"] / aggregate if aggregate else None
            for name in stage_names if summary["metrics"][name] is not None
        }
    return summaries


def geometric(values):
    return math.exp(statistics.mean(math.log(value) for value in values))


def publish_result(result, output_path, *, verify=False):
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").replace("\n", os.linesep).encode("utf-8")
    if verify:
        existing = output_path.read_bytes()
        if existing != payload:
            raise AssertionError("Recomputed frozen evidence differs; existing file preserved")
        return "verified_without_writing"
    # Exclusive creation prevents accidental rewriting of this audit's evidence.
    with output_path.open("xb") as stream:
        stream.write(payload)
    return "created"


def main(*, verify=False):
    output_path = OUT / "frozen_evidence.json"
    if output_path.exists() and not verify:
        raise FileExistsError("frozen_evidence.json already exists; use --verify for a read-only comparison")
    report_paths = [
        ("docs/AGENTS.md", False),
        ("docs/audits/2026-09-11-cm-performance/REPORT.md", True),
        ("docs/audits/2026-09-11-cm-continuation/REPORT.md", False),
        ("docs/audits/2026-09-15-cm-sympy-development-gate/NO_GO.md", True),
        ("docs/audits/2026-09-15-cm-sympy-development-gate/REVIEW.json", True),
        ("docs/research/cm-benchmark-research-2026-09-13/REPORT.md", False),
        ("docs/recognition/architecture_comparison_execution_retry_20260903/VERIFIED_INTERPRETATION.md", False),
        ("docs/recognition/architecture_query_ladder_cross_machine_execution_20260904/VERIFIED_CROSS_MACHINE_INTERPRETATION.md", False),
        ("cmbench/comparative/architecture_comparison_campaign.py", False),
        ("cmbench/comparative/architecture_query_ladder_followup.py", False),
        ("cmbench/comparative/sympy_cm_claim_cleanup.py", True),
        ("scripts/cm_sympy_claim_cleanup.py", True),
        ("scripts/cm_packed_queries_campaign.py", True),
    ]
    for path, origin in report_paths:
        read(path, root=origin)

    result = {
        "schema": "cm-time-attribution-frozen-evidence/v1",
        "base_commit": "e334de594262059cc18cf37eaab56b0f79e94843",
        "scope": "arithmetic of already measured records; no input fixtures loaded; no timings run",
        "statistics": "Per-cell medians describe repetitions. Aggregate phase percentages divide phase sums by same-row total sums; medians of phases need not sum to median total. No overlapping parent and child spans are added.",
        "unavailable_fields": ["process CPU time", "exclusive helper timing", "helper calls except truncated cProfile", "general per-phase allocations", "independently identified import versus transport versus shutdown"],
    }

    gate = "docs/audits/2026-09-15-cm-sympy-development-gate/"
    review = obj(gate + "REVIEW.json", root=True)
    binding = obj(gate + "SOURCE_BINDING.json", root=True)
    obj(gate + "REVIEW_PLAN.json", root=True)
    ledger = obj("docs/audits/2026-09-15-cm-sympy-claim-cleanup/LEDGER.jsonl", root=True)
    gate_rows = []
    all_stages = set()
    for row in ledger:
        stages = {key: value for key, value in row["timings_ns"].items() if key != "task_total_ns"}
        all_stages.update(stages)
        flat = {key: row[key] for key in ("family", "task", "case_id", "arm", "contract_sha256")}
        flat.update(stages)
        flat["caller_total_ns"] = row["caller_total_ns"]
        flat["task_total_ns"] = row["timings_ns"]["task_total_ns"]
        flat["outside_task_ns"] = flat["caller_total_ns"] - flat["task_total_ns"]
        flat["task_unattributed_ns"] = flat["task_total_ns"] - sum(stages.values())
        flat["output_bytes"] = row["artifact"]["bytes"]
        assert flat["outside_task_ns"] >= 0 and flat["task_unattributed_ns"] >= 0
        gate_rows.append(flat)
    recomputed_ratios = []
    for lane in review["lanes"]:
        for comparison in lane["comparisons"]:
            paired = defaultdict(dict)
            for arm in (comparison["candidate"], comparison["incumbent"]):
                group = defaultdict(list)
                for row in ledger:
                    if row["family"] == lane["family"] and row["task"] == lane["task"] and row["arm"] == arm:
                        group[row["contract_sha256"]].append(row["caller_total_ns"])
                for contract, totals in group.items():
                    paired[contract][arm] = statistics.median(totals)
            ratios = [values[comparison["candidate"]] / values[comparison["incumbent"]] for values in paired.values()]
            recomputed = geometric(ratios)
            assert math.isclose(recomputed, comparison["geometric_mean_candidate_over_incumbent"], rel_tol=1e-12)
            recomputed_ratios.append({"family": lane["family"], "task": lane["task"], "candidate": comparison["candidate"],
                                      "incumbent": comparison["incumbent"], "instances": len(ratios),
                                      "recomputed_geometric_candidate_over_incumbent": recomputed,
                                      "matches_review": True})
    result["sympy_gate"] = {
        "rows": len(ledger), "status_counts": dict(Counter(r["status"] for r in ledger)),
        "all_oracle_flags_true": all(r["validation"]["matches_oracle"] for r in ledger),
        "case_arm_statistics": phase_summary(gate_rows, ["family", "task", "case_id", "contract_sha256", "arm"], "caller_total_ns", ["task_total_ns", "outside_task_ns", "task_unattributed_ns", *sorted(all_stages)]),
        "arm_statistics": phase_summary(gate_rows, ["family", "task", "arm"], "caller_total_ns", ["task_total_ns", "outside_task_ns", "task_unattributed_ns", *sorted(all_stages)]),
        "recomputed_gate_ratios": recomputed_ratios,
        "caution": "task_total is a parent span. outside_task + task_total partitions caller_total. Named stages + task_unattributed partitions task_total. Never sum all these fields together. task_unattributed includes harness semantic validation, assignment generation, hashes, minterms and uninstrumented delivery; it is not pure wrapper time.",
    }

    perf = "docs/audits/2026-09-11-cm-performance/"
    manifest = obj(perf + "FINAL-MANIFEST.json")
    read(perf + "harness_development.py", root=True)
    read(perf + "lifecycle_diagnostic.py", root=True)
    stages = obj(perf + "stages.json", root=True)
    for row in stages:
        row["accounted_stage_sum_ns"] = sum(row["stages_ns"].values())
        row["stage_share_of_accounted_sum_percent"] = {k: 100 * v / row["accounted_stage_sum_ns"] for k, v in row["stages_ns"].items()}
    raw = obj(perf + "development_raw.jsonl", root=True)
    strong = obj(perf + "development_strong_raw.jsonl", root=True)
    controls = obj(perf + "query_controls.json", root=True)
    fresh = obj(perf + "fresh_process_timing.json", root=True)
    profiles = []
    for path in sorted((ROOT / perf).glob("profile-development-*.txt")):
        text = read(perf + path.name, root=True)
        profiles.append({"path": str(path), "header": text.splitlines()[0], "resolution": "printed 0.001 second, top 25 cumulative only; cannot reconstruct exclusive all-helper ledger"})
    result["performance_development"] = {
        "staged_observations": stages, "staged_scope": "single diagnostic pass; sum is accounted stages, not separately observed caller span",
        "raw_rows": len(raw), "all_raw_exact": all(r["exact"] for r in raw),
        "session_statistics": summarize(raw, ["case", "backend", "q", "restricted", "arm"], ["total_ns", "warm_ns"]),
        "strong_cse_statistics": summarize(strong, ["case", "backend", "q", "restricted", "arm"], ["total_ns", "warm_ns"]),
        "count_statistics": summarize([r for r in controls["rows"] if "total_ns" in r], ["case", "backend", "q"], ["total_ns"]),
        "count_memory_separate_pass": [r for r in controls["rows"] if "total_ns" not in r],
        "fresh_process_statistics": summarize(fresh, ["n", "arm"], ["lifecycle_ns", "import_ns", "operation_ns"]),
        "old_profiles": profiles,
        "limitations": ["harness_development cse does not pass flatten=True; use development_strong separately", "fresh_process.json intentionally not used because allocation pass contaminates lifecycle", "no CPU timing", "warm_ns is separate prepared execution, not additive to cold total"],
    }

    continuation = "docs/audits/2026-09-11-cm-continuation/packed-panels/"
    raw = obj(continuation + "development-RAW.jsonl", root=True)
    memory = obj(continuation + "development-MEMORY.json", root=True)
    lifecycle = obj(continuation + "LIFECYCLE.json", root=True)
    for row in raw + lifecycle:
        assert row["total_ns"] == sum(row[key] for key in ("setup_ns", "query_delivery_ns", "cleanup_ns"))
    result["continuation_development"] = {
        "rows": len(raw), "all_exact": all(r["exact"] for r in raw),
        "session_statistics": phase_summary(raw, ["case", "method", "q"], "total_ns", ["setup_ns", "query_delivery_ns", "cleanup_ns", "warm_ns"]),
        "cache_records": [{key: row[key] for key in ("case", "method", "q", "repeat", "cache")} for row in raw],
        "memory_separate_pass": memory,
        "already_measured_lifecycle_statistics": phase_summary(lifecycle, ["case", "method", "q"], "process_lifecycle_ns", ["total_ns", "setup_ns", "query_delivery_ns", "cleanup_ns"]),
        "lifecycle_case_policy": "Some saved lifecycle rows refer to already consumed confirmation cases; only their frozen measured records were read. No fixture or query input was read or executed.",
        "caution": "total_ns is the sum of disjoint spans, excludes warm pass and bookkeeping; cleanup occurs after optional warm pass. Cache counters cover both cold and warm consumption. first_chunk_ns overlaps setup and query. warm_ns does not belong in cold phase shares.",
    }
    for summary in result["continuation_development"]["session_statistics"]:
        # warm_ns is a separate pass; retain its statistics but never a cold phase share.
        summary["aggregate_phase_percent"].pop("warm_ns", None)

    arch_paths = {
        "retry002_gcc": "docs/recognition/architecture_comparison_execution_retry_20260903/runpod-architecture-comparison-retry-002/evidence/run-output/architecture-comparison-linux-gcc-20260903-002/raw_measurements.jsonl",
        "query_ladder_clang": "docs/recognition/architecture_query_ladder_cross_machine_execution_20260904/runpod-architecture-query-ladder-cross-machine-execute-001/evidence/run-output/architecture-query-ladder-linux-clang-20260904-003/raw_measurements.jsonl",
    }
    result["architecture"] = {}
    for label, path in arch_paths.items():
        rows = obj(path)
        good = [r for r in rows if r["status"] == "ok"]
        flat = [{**{k: r.get(k) for k in ("lane", "sublane", "arm", "query_count")}, **r["timings_ns"]} for r in good]
        stages = sorted(k for k in good[0]["timings_ns"] if k != "accounted_total_ns")
        assert all(r["accounted_total_ns"] == sum(r[k] for k in stages) for r in flat)
        result["architecture"][label] = {
            "rows": len(rows), "status_counts": dict(Counter(r["status"] for r in rows)),
            "exact_ok_rows": sum(bool(r.get("exact_check_passed")) for r in good),
            "arm_phase_statistics": phase_summary(flat, ["lane", "sublane", "arm", "query_count"], "accounted_total_ns", stages),
            "zero_incremental_memory_rows": sum(r.get("memory_measurement", {}).get("incremental_peak_rss_bytes") == 0 for r in good),
            "caution": "Accounted stage sum is not caller wall time. compilation_ns is hardcoded zero; compile and lowering are in representation_construction. Lazy bindings live inside evaluation. Lane D evaluation_ns is whole nested task, not kernel. Retry A/B/C gc.collect does not explicitly release still-referenced locals. Ladder excludes isolated process lifecycle.",
        }

    # Verify saved bindings for evidence actually read; never consume fixture payloads.
    expected = {str(ROOT / (perf + name)): digest for name, digest in manifest["artifacts"].items()}
    for source in binding["sources"]:
        expected[str(ROOT / source["path"])] = source["sha256"]
    verification = []
    for path, source in sorted(SOURCES.items()):
        if path in expected:
            match = source["sha256"] == expected[path]
            verification.append({"path": path, "expected_sha256": expected[path], "actual_sha256": source["sha256"], "matches": match})
    result["predecessor_binding_checks"] = verification
    result["sources"] = list(SOURCES.values())
    result["source_count"] = len(SOURCES)
    output_action = publish_result(result, output_path, verify=verify)
    print(json.dumps({"sources": len(SOURCES), "binding_checks": len(verification), "binding_mismatches": sum(not row["matches"] for row in verification),
                      "sympy_rows": len(ledger), "recomputed_gate_comparisons": len(recomputed_ratios), "output": str(output_path), "output_action": output_action}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="recompute and byte-compare the existing output without writing")
    main(verify=parser.parse_args().verify)
