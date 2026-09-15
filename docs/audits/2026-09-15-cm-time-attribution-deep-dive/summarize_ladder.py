"""Recompute summaries from corrected frozen ladder records; performs no timings."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
COMMIT = "e334de594262059cc18cf37eaab56b0f79e94843"
TREATMENTS = (("cold_q1", "cold", 1), ("resident_q64", "resident_q64", 64))


def distribution(values):
    values = list(values)
    return {"samples": len(values), "median": statistics.median(values),
            "min": min(values), "max": max(values), "mean": statistics.mean(values),
            "zero_samples": sum(value == 0 for value in values)}


def aggregate_phases(passes, *, queries):
    totals = {clock: sum(row["total"][clock] for row in passes) for clock in ("wall_s", "cpu_s")}
    phases = defaultdict(lambda: {"wall_s": 0., "cpu_s": 0., "calls": 0, "calls_known": True})
    helpers = defaultdict(lambda: {"self_wall_s": 0., "self_cpu_s": 0., "inclusive_wall_s": 0., "calls": 0})
    for row in passes:
        for name, value in row["exclusive_phases"].items():
            phases[name]["wall_s"] += value["wall_s"]
            phases[name]["cpu_s"] += value["cpu_s"]
            if value["calls"] is None:
                phases[name]["calls_known"] = False
            else:
                phases[name]["calls"] += value["calls"]
        for value in row["helpers"]:
            for key in ("self_wall_s", "self_cpu_s", "inclusive_wall_s", "calls"):
                helpers[value["helper"]][key] += value[key]
    for phase in phases.values():
        phase["percent_of_own_phase_pass_wall"] = 100 * phase["wall_s"] / totals["wall_s"]
        phase["mean_wall_s_per_operation"] = phase["wall_s"] / len(passes) / queries
        phase["mean_cpu_s_per_operation"] = phase["cpu_s"] / len(passes) / queries
        if not phase.pop("calls_known"):
            phase["calls"] = None
    for name, helper in helpers.items():
        helper["helper"] = name
        helper["mean_self_wall_s"] = helper["self_wall_s"] / helper["calls"]
        helper["inclusive_is_not_additive"] = True
    assert math.isclose(sum(p["wall_s"] for p in phases.values()), totals["wall_s"], abs_tol=1e-10)
    assert math.isclose(sum(p["cpu_s"] for p in phases.values()), totals["cpu_s"], abs_tol=1e-10)
    return {"phase_passes": len(passes), "queries_per_pass": queries,
            "sum_caller_wall_s": totals["wall_s"], "sum_caller_cpu_s": totals["cpu_s"],
            "exclusive_phases": dict(sorted(phases.items(), key=lambda item: -item[1]["wall_s"])),
            "helpers": sorted(helpers.values(), key=lambda row: -row["self_wall_s"])}


def timing_median(row, treatment, clock="wall_s"):
    return row["timing"][treatment]["per_operation"][clock]["median"]


def build_summary(data, source_sha256):
    assert data["baseline_commit"] == COMMIT
    records = data["records"]
    assert len(records) == 137
    assert len({(r["case"], r["arm"]) for r in records}) == len(records)
    cells, index = [], {}
    case_order = list(dict.fromkeys(record["case"] for record in records))
    arm_order = list(dict.fromkeys(record["arm"] for record in records))
    for record in records:
        assert record["status"] == "exact_complete_output_match"
        row = {"case": record["case"], "arm": record["arm"], "status": record["status"],
               "source": record["source"], "comparison_class": record["comparison_class"],
               "output_sha256": record["output_sha256"], "output_bytes": record["output_bytes"],
               "metrics": record["metrics"], "memory": record["memory_separate_pass"], "timing": {}, "phase": {}}
        for label, phase_label, queries in TREATMENTS:
            raw = record["uninstrumented"][label]
            assert len(raw) == 7
            row["timing"][label] = {"queries": queries,
                "whole_pass": {clock: distribution(sample[clock] for sample in raw) for clock in ("wall_s", "cpu_s")},
                "per_operation": {clock: distribution(sample[clock] / queries for sample in raw) for clock in ("wall_s", "cpu_s")}}
            passes = [sample for sample in record["phase_passes"] if sample["treatment"] == phase_label]
            assert len(passes) == 3
            phase = aggregate_phases(passes, queries=queries)
            phase["median_instrumented_caller_wall_s"] = statistics.median(sample["total"]["wall_s"] for sample in passes)
            phase["instrumentation_dilation_ratio"] = phase["median_instrumented_caller_wall_s"] / row["timing"][label]["whole_pass"]["wall_s"]["median"]
            phase["dilation_is_different_pass_ratio_not_probe_cost_estimate"] = True
            row["phase"][label] = phase
        row["cprofile_hot_helpers"] = record["cprofile_separate_pass"]["hot_helpers"][:10]
        cells.append(row)
        index[(row["case"], row["arm"])] = row
    packed_digests = defaultdict(set)
    for row in cells:
        if row["arm"] != "dense_cm":
            packed_digests[row["case"]].add((row["output_sha256"], row["output_bytes"]))
    assert all(len(digests) == 1 for digests in packed_digests.values())
    comparisons = []
    for case in case_order:
        cse, cm = index[(case, "cse_flat")], index[(case, "cm_common_flat")]
        bare, public = index[(case, "bare_cm_flat")], index[(case, "public_cm")]
        comparison = {"case": case, "source": cse["metrics"]["source"],
                      "cse_flat": cse["metrics"]["flat"], "cm_flat": cm["metrics"]["flat"],
                      "cm_ir": cm["metrics"]["cm"], "treatments": {}}
        for treatment, _, _ in TREATMENTS:
            cse_t, cm_t = timing_median(cse, treatment), timing_median(cm, treatment)
            bare_t, public_t = timing_median(bare, treatment), timing_median(public, treatment)
            comparison["treatments"][treatment] = {
                "common_cm_minus_cse_s": cm_t - cse_t, "common_cm_over_cse": cm_t / cse_t,
                "public_minus_bare_s": public_t - bare_t, "public_over_bare": public_t / bare_t,
                "public_increment_percent_of_public": 100 * (public_t - bare_t) / public_t,
                "increment_interpretation": "difference of whole-call medians, descriptive; not exclusive measured wrapper time",
                "cse_retained_traced_bytes": cse["memory"]["traced_current_bytes_delta"],
                "cm_retained_traced_bytes": cm["memory"]["traced_current_bytes_delta"],
            }
        cold, resident = comparison["treatments"]["cold_q1"], comparison["treatments"]["resident_q64"]
        comparison["representation_by_residency_interaction"] = {
            "common_cm_cse_difference_of_differences_s": cold["common_cm_minus_cse_s"] - resident["common_cm_minus_cse_s"],
            "common_cm_cse_ratio_of_ratios": cold["common_cm_over_cse"] / resident["common_cm_over_cse"],
            "public_bare_difference_of_differences_s": cold["public_minus_bare_s"] - resident["public_minus_bare_s"],
            "interpretation": "(CM minus CSE at cold q1) minus (CM minus CSE at resident q64 per operation); setup-amortization interaction, not pure compile time",
        }
        comparisons.append(comparison)
    weighted = {}
    for arm in arm_order:
        group = [record for record in records if record["arm"] == arm]
        weighted[arm] = {"cases": len(group), "weighting": "sum phase wall / sum own caller wall; time-weighted across measured cells, no catalog weighting"}
        for label, phase_label, queries in TREATMENTS:
            passes = [p for r in group for p in r["phase_passes"] if p["treatment"] == phase_label]
            weighted[arm][label] = aggregate_phases(passes, queries=queries)
    cpu_samples = [sample["cpu_s"] for record in records for samples in record["uninstrumented"].values() for sample in samples]
    positive_cpu = [sample for sample in cpu_samples if sample > 0]
    scaling = {arm: [index[(f"fixed-structure-output-k{width}", arm)] for width in (4, 8, 16, 18)
                     if (f"fixed-structure-output-k{width}", arm) in index]
               for arm in arm_order if arm != "dense_cm"}
    score = {
        "same_executor_cm_cold_lower_median_cases": sum(row["treatments"]["cold_q1"]["common_cm_over_cse"] < 1 for row in comparisons),
        "same_executor_cm_resident_lower_median_cases": sum(row["treatments"]["resident_q64"]["common_cm_over_cse"] < 1 for row in comparisons),
        "same_executor_cm_resident_within_10pct_cases": sum(.9 <= row["treatments"]["resident_q64"]["common_cm_over_cse"] <= 1.1 for row in comparisons),
        "cm_has_fewer_flat_instructions_cases": sum(row["cm_flat"]["flat_instructions"] < row["cse_flat"]["flat_instructions"] for row in comparisons),
        "cm_has_fewer_bigint_primitives_cases": sum(row["cm_flat"]["executed_bigint_ops"] < row["cse_flat"]["executed_bigint_ops"] for row in comparisons),
        "cm_common_traced_retention_exceeds_cse_cases": sum(row["treatments"]["cold_q1"]["cm_retained_traced_bytes"] > row["treatments"]["cold_q1"]["cse_retained_traced_bytes"] for row in comparisons),
        "cases": len(comparisons), "score_is_descriptive_not_statistical_gate": True,
    }
    return {"schema": "cm-time-attribution-ladder-summary/v1", "classification": "measured diagnostic summaries, no scientific disposition change",
            "source": {"path": "ladder-run-002.json", "sha256": source_sha256, "baseline_commit": COMMIT,
                       "superseded": ["ladder-run-001.json", "ladder-smoke-001.json"],
                       "supersession_reason": "early diagnostic tracer did not patch imported evaluator aliases; retained files are not used for any table or conclusion here"},
            "records": len(cells), "cases": case_order, "arms": arm_order,
            "cpu_granularity": {"reported_resolution_s": data["cpu_timer_resolution_s"],
                                "whole_pass_samples": len(cpu_samples), "zero_whole_pass_samples": sum(v == 0 for v in cpu_samples),
                                "smallest_positive_observed_whole_pass_s": min(positive_cpu) if positive_cpu else None,
                                "note": "zero/quantized process CPU observations are retained; do not interpret zero as free execution; per-operation CPU is the q64 aggregate divided by64"},
            "startup": data["startup_separate_process_pass"], "score": score,
            "cells": cells, "comparisons": comparisons, "time_weighted_phases_by_arm": weighted,
            "fixed_expression_output_scaling": {arm: [{"case": row["case"], "basis_width": row["metrics"]["basis_width"],
                "output_bytes": row["output_bytes"], "source": row["metrics"]["source"], "cm": row["metrics"].get("cm"),
                "timing": row["timing"], "memory": row["memory"]} for row in rows] for arm, rows in scaling.items()}}


def us(value):
    return f"{value * 1e6:.3f}"


def observed_range(value):
    return f"{us(value['median'])} [{us(value['min'])}, {us(value['max'])}]"


def render(summary):
    by_key = {(row["case"], row["arm"]): row for row in summary["cells"]}
    score = summary["score"]
    lines = ["# Corrected packed-ladder findings", "",
        f"Source: `ladder-run-002.json`, SHA-256 `{summary['source']['sha256']}`; exact baseline `{COMMIT}`. This is diagnostic evidence on 13 disclosed cases, 137 cells and seven uninstrumented repeats per cell. No held-out input or scientific disposition changed.", "",
        "**Measured** means a statistic recomputed from this frozen run. **Code-supported inference** identifies a mechanism demonstrated by the audited implementation. **Hypothesis** names an unisolated explanation. **Unknown** marks absent or inadequate evidence. All reported wins are descriptive local medians, not confirmation results or statistical superiority claims.", "",
        "## 1. Main findings", "",
        f"* **Measured:** common-executor CM has a lower cold median in {score['same_executor_cm_cold_lower_median_cases']}/13 cases and a lower resident median in {score['same_executor_cm_resident_lower_median_cases']}/13; {score['same_executor_cm_resident_within_10pct_cases']}/13 resident ratios lie within 10% of parity. These use the identical prepared bigint executor and common complete packed-byte delivery/check contract.",
        f"* **Measured:** CM has fewer flat instructions in {score['cm_has_fewer_flat_instructions_cases']}/13 cases and fewer counted bigint primitives in {score['cm_has_fewer_bigint_primitives_cases']}/13. A resident CM win where work was rewritten away is not evidence of faster implementation of an identical instruction stream.",
        f"* **Measured:** traced retained bytes for the common CM session exceed CSE-flat in {score['cm_common_traced_retention_exceeds_cse_cases']}/13 cases. This includes session/source/program/output/module-cache retention, not isolated CMNode bytes; the retained-object attribution is **code-supported inference**, supported by node/support metadata but not a complete graph-byte census.",
        "* **Code-supported inference:** CSE-flat retains sharing and a flat program without constructing the canonical CMNode graph, deep node keys or per-node support tuples. The cold-vs-resident interaction isolates the practical difference between paying this setup and reusing it. It does not separately identify each construction cost.",
        "* **Unknown:** exact cumulative allocation traffic, native/process RSS, isolated cache validation/eviction time, asymptotic slopes, or whether a broad workload population prefers one representation. The small cases have correlated sharing, support and program length.", "",
        "## 2. Boundary and instrumentation cautions", "",
        "Cold q1 starts with a supplied serialized payload, parses/decodes it, constructs required IR/program/masks, evaluates and delivers/checks complete output bytes. File loading and process startup are absent from that caller. Resident q64 uses an already-set-up session and reports its 64-call total divided by64. A warm-up call is outside these resident timings. Setup is not recharged in resident per-call values.", "",
        "Phase shares below divide sums of exclusive instrumented phase spans by sums of their own instrumented caller totals. They are time-weighted across these cells. They must not be applied to uninstrumented totals: nested Python probes strongly dilate tiny operations. `public_cm_diag` also intentionally uses the generic diagnostic wrapper, whereas `public_cm` preserves the diagnostics-free branch. Allocation inside bigint arithmetic and word conversion inside `_eval_words` remain grouped.", "",
        f"Earlier run001 and smoke evidence remain unchanged but are superseded for this analysis because imported evaluator aliases were initially missing from phase tracing. Only run002 is read by `summarize_ladder.py`. The script performs no timing and refuses existing output paths.", "",
        f"**Measured CPU limitation:** {summary['cpu_granularity']['zero_whole_pass_samples']}/{summary['cpu_granularity']['whole_pass_samples']} whole-pass CPU observations are zero. Smallest positive observed whole-pass CPU was {summary['cpu_granularity']['smallest_positive_observed_whole_pass_s']:.6f} s although the API reports {summary['cpu_granularity']['reported_resolution_s']:.1e} s resolution. Preserve the quantized CPU ranges; zero does not establish that a phase uses no CPU.", "",
        "## 3. Common-executor CM versus CSE-flat", "",
        "Ratios are CM/CSE from uninstrumented wall medians; resident time is per operation. `Ops` means counted bigint primitives, not flat instructions. Sharing is unfolded occurrences divided by structural DAG nodes; it includes structurally equal separately allocated subtrees and is not an identity-sharing ratio. Delta-delta = (cold CM−CSE) − (resident CM−CSE), a descriptive 2×2 representation/residency interaction in microseconds. A positive interaction says that relative CM cost shrinks after setup is resident; it is not an exclusive compile timer.", "",
        "| Case | Source nodes/edges; sharing | CSE instr/ops | CM nodes; support entries; instr/ops | Cold ratio | Resident ratio | Delta-delta µs | CSE/CM retained bytes |",
        "|---|---|---|---|---:|---:|---:|---:|"]
    for row in summary["comparisons"]:
        cold, resident = row["treatments"]["cold_q1"], row["treatments"]["resident_q64"]
        src, cse, cm, node = row["source"], row["cse_flat"], row["cm_flat"], row["cm_ir"]
        lines.append(f"| {row['case']} | {src['object_dag_nodes']}/{src['object_dag_edges']}; {src['sharing_factor']:.2f} | {cse['flat_instructions']}/{cse['executed_bigint_ops']} | {node['cm_ir_nodes']}; {node['support_entries_sum']}; {cm['flat_instructions']}/{cm['executed_bigint_ops']} | {cold['common_cm_over_cse']:.3f} | {resident['common_cm_over_cse']:.3f} | {us(row['representation_by_residency_interaction']['common_cm_cse_difference_of_differences_s'])} | {cold['cse_retained_traced_bytes']}/{cold['cm_retained_traced_bytes']} |")
    lines += ["", "## 4. Public versus bare CM", "",
        "Both arms start from the same source fixture in cold treatment and from existing CMNodes in resident treatment; both deliver/check the same packed bytes. The delta is public median minus bare median, and its share is delta/public median. It is an incremental whole-call comparison, **not** a measured exclusive wrapper fraction: order, cache/first-use behavior and run noise interact. Negative values are retained. Public no-reinflate guard/result work is **code-supported inference**; the exclusive phase pass independently observes those helpers.", "",
        "| Case | Cold public/bare | Cold delta µs; share % | Resident public/bare | Resident delta µs; share % | Interaction µs |",
        "|---|---:|---:|---:|---:|---:|"]
    for row in summary["comparisons"]:
        cold, resident = row["treatments"]["cold_q1"], row["treatments"]["resident_q64"]
        lines.append(f"| {row['case']} | {cold['public_over_bare']:.3f} | {us(cold['public_minus_bare_s'])}; {cold['public_increment_percent_of_public']:.1f} | {resident['public_over_bare']:.3f} | {us(resident['public_minus_bare_s'])}; {resident['public_increment_percent_of_public']:.1f} | {us(row['representation_by_residency_interaction']['public_bare_difference_of_differences_s'])} |")
    lines += ["", "## 5. Fixed expression, growing requested output", "",
        "The disclosed implication expression retains four variables while the requested complete basis grows from k4 to k18. The packed byte counts are 2, 32, 8192 and 32768. This holds logical/source structure fixed and exposes width-dependent mask, execution and output work. It does not distinguish unavoidable output emission from all intermediate operations over the same width. Dense CM cells are separate contracts and are listed in the complete ledger.", "",
        "| Arm | k4 cold/resident µs | k8 cold/resident µs | k16 cold/resident µs | k18 cold/resident µs | First measured width→k18 retained/peak bytes |", "|---|---:|---:|---:|---:|---:|"]
    for arm, values in summary["fixed_expression_output_scaling"].items():
        by_width = {row["basis_width"]: row for row in values}
        entries = []
        for width in (4, 8, 16, 18):
            row = by_width.get(width)
            entries.append("not run" if row is None else f"{us(row['timing']['cold_q1']['per_operation']['wall_s']['median'])}/{us(row['timing']['resident_q64']['per_operation']['wall_s']['median'])}")
        first, last = values[0]["memory"], values[-1]["memory"]
        lines.append(f"| {arm} | " + " | ".join(entries) + f" | {first['traced_current_bytes_delta']}→{last['traced_current_bytes_delta']} / {first['traced_peak_bytes_delta']}→{last['traced_peak_bytes_delta']} |")
    lines += ["", "## 6. Exclusive phase totals on their own denominators", "",
        "Each row aggregates the three phase passes of every available cell for that arm/treatment. Total and top phases are mean microseconds per call across the cells; percentages use summed observed elapsed time. All phases and call/mean-helper costs for every cell are retained in `ladder_summary.json`. The unresolved/probe remainder is reported explicitly; it is not redistributed.", "",
        "| Arm | Treatment; cells | Mean instrumented caller µs/call | Top exclusive phases (share; mean µs/call) | Unresolved/probe % |", "|---|---|---:|---|---:|"]
    for arm, aggregate in summary["time_weighted_phases_by_arm"].items():
        for label, _, queries in TREATMENTS:
            value = aggregate[label]
            phases = value["exclusive_phases"]
            top = [f"{name}: {phase['percent_of_own_phase_pass_wall']:.1f}%; {us(phase['mean_wall_s_per_operation'])}" for name, phase in phases.items() if name != "unresolved_harness_and_probe_remainder"][:4]
            remainder = phases.get("unresolved_harness_and_probe_remainder", {}).get("percent_of_own_phase_pass_wall", 0)
            lines.append(f"| {arm} | {label}; {aggregate['cases']} | {us(value['sum_caller_wall_s']/value['phase_passes']/queries)} | {'; '.join(top)} | {remainder:.1f} |")
    dilations = [row["phase"][label]["instrumentation_dilation_ratio"] for row in summary["cells"] for label, _, _ in TREATMENTS]
    lines += ["", f"**Measured instrumentation dilation:** median {statistics.median(dilations):.2f}×, range {min(dilations):.2f}×–{max(dilations):.2f}× across 274 cell/treatment ratios. This is a cross-pass diagnostic ratio, not a correction factor. The 137-cell ledger below includes each treatment's own dilation.", "",
        "## 7. Memory, caches and unresolved mechanisms", "",
        "Tracemalloc was a separate cold pass. Current bytes retain result, session Expr/CM/program and module caches; peak bytes describe the traced peak over that call. These are not cumulative allocation traffic or process RSS. Node shallow+dict bytes omit descendant tuples/strings and shared ownership. `metrics.cm.support_entries_sum`, source edges/sharing, flat instructions/primitives and live-buffer counts permit structural comparison, but they cannot uniquely distribute retained bytes among mechanisms.", "",
        "The integer/word paths retain different execution state. Word scratch arrays may persist with a program; bigint operations allocate results, and these small programs generally do not trigger the width-and-slot release policy together. Cache entry counters are observed after the memory pass, not a dedicated hit/miss/eviction campaign. This ladder has no persistent family cache reuse. Relevant family evidence is separate. Allocation/release and execution remain a measured joint phase; isolated allocation time is unknown.", "",
        "The full relation is required by this ladder's output contract. SAT/count/equivalence/batch tasks are not represented by these complete-output times; their smaller requested answers and task-matched controls require separate ledgers. This run cannot attribute an entire public regression to a single mechanism or establish independent scaling laws. No optimization or routing recommendation follows from it.", "",
        "## 8. Complete 137-cell uninstrumented ledger", "",
        "Times are microseconds per operation; brackets give the full seven-repeat min/max range, not a confidence interval. CPU for resident q64 is total CPU divided by64. Dilation is cold/resident phase-pass median caller time divided by the matching uninstrumented median. All 137 records are included, including diagnostic-wrapper and dense-contract arms.", "",
        "| Case | Arm | Cold wall median [min,max] µs | Cold CPU median [min,max] µs | Resident wall median [min,max] µs/call | Resident CPU median [min,max] µs/call | Dilation cold/resident | Retained/peak traced bytes |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in summary["cells"]:
        cold, resident = row["timing"]["cold_q1"]["per_operation"], row["timing"]["resident_q64"]["per_operation"]
        memory = row["memory"]
        lines.append(f"| {row['case']} | {row['arm']} | {observed_range(cold['wall_s'])} | {observed_range(cold['cpu_s'])} | {observed_range(resident['wall_s'])} | {observed_range(resident['cpu_s'])} | {row['phase']['cold_q1']['instrumentation_dilation_ratio']:.2f}/{row['phase']['resident_q64']['instrumentation_dilation_ratio']:.2f} | {memory['traced_current_bytes_delta']}/{memory['traced_peak_bytes_delta']} |")
    lines += ["", "## 9. Reproduction and disposition", "",
        "Run `python -B summarize_ladder.py --summary <new-audit-json> --report <new-audit-md>` from this audit directory. Inputs are `ladder-run-002.json` only; output files must be new and remain in this audit directory. The source hash is checked into the resulting summary. No profiling, fixture execution or timings occur during this analysis.", "",
        "No scientific disposition changed. Remaining attribution gaps require matching exclusive phase/CPU/allocation evidence on the same caller contract; current data must retain them as unresolved. No further timing is requested by this summary.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, default=HERE / "ladder_summary.json")
    parser.add_argument("--report", type=Path, default=HERE / "LADDER_FINDINGS.md")
    options = parser.parse_args()
    for path in (options.summary, options.report):
        if path.exists() or not path.resolve().is_relative_to(HERE):
            raise ValueError("outputs must be new files inside this audit")
    raw = (HERE / "ladder-run-002.json").read_bytes()
    summary = build_summary(json.loads(raw), hashlib.sha256(raw).hexdigest())
    with options.summary.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2)
    with options.report.open("x", encoding="utf-8") as stream:
        stream.write(render(summary))
    print(json.dumps({"records": summary["records"], "score": summary["score"], "source_sha256": summary["source"]["sha256"]}))


if __name__ == "__main__":
    main()
