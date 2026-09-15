"""Build combined time ledger from frozen summaries only; no timing or execution."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent


def phase_table(lines, title, rows, total_wall_us, total_cpu_us):
    lines.extend(["", f"### {title}", "", f"Separate phase-pass caller: **{total_wall_us:.3f} µs wall**, **{total_cpu_us:.3f} µs process CPU** (mean per stated operation). Percentages use this phase pass only.", "",
                  "| Exclusive phase | Mean wall µs | Mean CPU µs | Own caller wall % |", "|---|---:|---:|---:|"])
    for name, wall, cpu, pct in rows:
        lines.append(f"| {name} | {wall:.3f} | {cpu:.3f} | {pct:.2f} |")
    assert math.isclose(sum(r[1] for r in rows), total_wall_us, rel_tol=1e-8, abs_tol=1e-6)
    assert math.isclose(sum(r[3] for r in rows), 100., rel_tol=1e-8, abs_tol=1e-6)


def render(ladder, task, frozen, hashes):
    assert ladder["records"] == len(ladder["cells"]) == 137
    assert len(task["cells"]) == 70
    lines = ["# Time ledger — caller boundaries, exclusive phases and delivery", "",
             "All new observations are local diagnostics on disclosed development fixtures at `e334de594262059cc18cf37eaab56b0f79e94843`. This ledger includes **all 137 corrected ladder cells and all 70 task cells**. Nothing is pooled into a benchmark claim. No scientific disposition changed.", "",
             "## 1. Sources, units and denominator rules", "",
             "| Source | Records | Used for |", "|---|---:|---|",
             "| [ladder_summary.json](ladder_summary.json) → `ladder-run-002.json` | 137 | Seven-repeat uninstrumented cold and resident timings; separate three-pass exclusive phases, cProfile and tracemalloc |",
             "| [TASK_SUMMARY.json](TASK_SUMMARY.json) → `task-run-001/TASK_RESULTS.json` | 70 | Five-repeat task caller timings; separate phases and memory |",
             "| [frozen_evidence.json](frozen_evidence.json) | predecessor records | Arithmetic-only reinterpretation; no fixture replay |", "",
             "The structured [PROFILE_RESULTS.json](PROFILE_RESULTS.json) ties these sources together. Every cell's absolute phase wall/CPU time, percentage of its own instrumented caller, counts/helpers and memory details are in the linked summaries. Full seven-repeat min/max ranges and instrument dilation for all137 ladder cells also appear in [LADDER_FINDINGS.md](LADDER_FINDINGS.md). [TASK_LEDGER.md](TASK_LEDGER.md) includes nested public-family subspans; those are annotations inside a caller and must not be added again.", "",
             "**Uninstrumented ladder units:** µs per operation. Cold q1 includes supplied JSON parse/decode, setup, execution, packed delivery and exact guard; it excludes process launch and disk loading. Resident q64 is an already-initialized 64-operation session divided by64; warm-up/setup is outside it. **Task units:** ms for the whole requested task, including all q contexts or variants, not per query. Task fixture loading/generation, adapters, output and checks are charged according to [TASK_METHODS.md](TASK_METHODS.md). Dense output arms have a different output contract and remain labelled.", "",
             "**Phase denominator:** each table divides exclusive phase sums by its own phase-pass caller sum. Instrumented phase percentages are not percentages of the faster uninstrumented caller. Parent/cumulative spans are never added to children. Separate medians do not form an additive partition. Allocation inside arithmetic and word conversion inside grouped evaluators remain grouped; absent exclusive evidence is unknown.", "",
             f"**CPU limitation:** {ladder['cpu_granularity']['zero_whole_pass_samples']}/{ladder['cpu_granularity']['whole_pass_samples']} ladder whole-pass CPU samples are zero; smallest observed positive value is {ladder['cpu_granularity']['smallest_positive_observed_whole_pass_s']*1000:.3f} ms. Task observations are likewise quantized. API-reported resolution does not make submillisecond CPU shares reliable. A zero CPU median means no resolved median CPU increment, not zero work.", "",
             "Only corrected `ladder-run-002.json` supports this ledger. `ladder-run-001.json` and `ladder-smoke-001.json` are preserved but superseded because the original tracer missed imported evaluator aliases. No corrected totals are inferred by editing those records.", "",
             "## 2. Process startup, imports and unresolved outside-script cost", "",
             "Separate fresh-process pass; already-imported library cells above incur no analogous per-call startup phase. Parent wall includes process launch, script work, stdout delivery and shutdown. Import span begins at script entry after importing `time`. Residual is parent wall minus script entry-to-payload wall; it cannot be uniquely split into launch, transport, early imports or shutdown. Child process CPU is a separate whole-process observation and is not summed with parent wall.", "",
             "| Process repeat | Parent caller wall ms | Script imports wall/CPU ms | Script entry→payload wall ms | Outside-script residual wall ms | Child process CPU ms |", "|---|---:|---:|---:|---:|---:|"]
    for i, row in enumerate(ladder["startup"], 1):
        lines.append(f"| {i} | {row['caller_process_delivery_wall_s']*1e3:.3f} | {row['imports_from_script_entry_wall_s']*1e3:.3f}/{row['imports_from_script_entry_cpu_s']*1e3:.3f} | {row['entry_to_payload_wall_s']*1e3:.3f} | {row['startup_transport_shutdown_and_unmeasured_import_residual_wall_s']*1e3:.3f} | {row['child_process_cpu_s']*1e3:.3f} |")
    lines += ["", "## 3. All137 ladder cells: uninstrumented medians", "",
              "Wall and CPU are µs per operation. Exact byte output matched on every row. Complete ranges, all phase fields and memory scopes remain in `ladder_summary.json.cells`; the table retains every arm, including diagnostic wrapper and dense-contract controls.", "",
              "| Case | Arm | Cold wall µs | Cold CPU µs | Resident wall µs/call | Resident CPU µs/call | Output bytes |", "|---|---|---:|---:|---:|---:|---:|"]
    for row in ladder["cells"]:
        cold = row["timing"]["cold_q1"]["per_operation"]
        resident = row["timing"]["resident_q64"]["per_operation"]
        lines.append(f"| {row['case']} | {row['arm']} | {cold['wall_s']['median']*1e6:.3f} | {cold['cpu_s']['median']*1e6:.3f} | {resident['wall_s']['median']*1e6:.3f} | {resident['cpu_s']['median']*1e6:.3f} | {row['output_bytes']} |")
    lines += ["", "## 4. All70 task cells: uninstrumented medians", "",
              "Times are **ms for the whole task**, including q1/q64 or a complete family as labelled. All rows are `ok` with exact correctness. Input loading/conversion dominates some small assignment tasks; symbolic minimization dominates the balanced expression. These are task-specific contracts, so the ms values must not be directly ranked against the µs complete-output prepared ladder.", "",
              "| Task | Case | Arm | q | Wall ms/task | CPU ms/task | Output bytes |", "|---|---|---|---:|---:|---:|---:|"]
    for row in task["cells"]:
        cell = row["cell"]
        assert row["status"] == "ok" and row["correct"]
        lines.append(f"| {cell['task']} | {cell['case']} | {cell['arm']} | {cell['q']} | {row['wall_median_ns']/1e6:.4f} | {row['cpu_median_ns']/1e6:.4f} | {row['output_bytes']} |")
    lines += ["", "## 5. All-arm ladder phase overview", "",
              "Each row time-weights all available cases for that arm/treatment by their own measured phase-pass caller times. Absolute values are mean µs per operation across cases and passes. Listed phases are the largest four; the full exclusive partition is in `ladder_summary.json.time_weighted_phases_by_arm`. A grouped phase intentionally retains inseparable mechanisms.", "",
              "| Arm | Treatment; cases | Mean own caller µs | Largest four phases: own %; mean µs | Unresolved/probe % |", "|---|---|---:|---|---:|"]
    for arm, group in ladder["time_weighted_phases_by_arm"].items():
        for treatment, q in (("cold_q1", 1), ("resident_q64", 64)):
            value = group[treatment]
            phases = value["exclusive_phases"]
            top = [f"{name}: {p['percent_of_own_phase_pass_wall']:.1f}%; {p['mean_wall_s_per_operation']*1e6:.3f}" for name, p in phases.items() if name != "unresolved_harness_and_probe_remainder"][:4]
            residual = phases.get("unresolved_harness_and_probe_remainder", {}).get("percent_of_own_phase_pass_wall", 0)
            lines.append(f"| {arm} | {treatment}; {group['cases']} | {value['sum_caller_wall_s']/value['phase_passes']/q*1e6:.3f} | {'; '.join(top)} | {residual:.1f} |")
    lines += ["", "## 6. Representative complete exclusive phase partitions", "",
              "These full partitions show contrasting mechanisms. They are descriptive observed phase passes, with CPU granularity and probe overhead retained. Nothing here is normalized against an uninstrumented denominator. Every unshown cell has the same detailed fields in the summary JSON; the complete per-cell ledger is not limited to these examples."]
    ladder_index = {(r["case"], r["arm"]): r for r in ladder["cells"]}
    for case, arm, treatment in (("random-shared-seed0-k8", "cm_common_flat", "cold_q1"),
                                  ("random-shared-seed0-k8", "public_cm", "resident_q64"),
                                  ("fixed-structure-output-k18", "cm_common_flat", "resident_q64")):
        value = ladder_index[(case, arm)]["phase"][treatment]
        q, count = value["queries_per_pass"], value["phase_passes"]
        rows = [(name, p["mean_wall_s_per_operation"]*1e6, p["mean_cpu_s_per_operation"]*1e6, p["percent_of_own_phase_pass_wall"]) for name, p in value["exclusive_phases"].items()]
        phase_table(lines, f"{case} / {arm} / {treatment} per operation", rows, value["sum_caller_wall_s"]/count/q*1e6, value["sum_caller_cpu_s"]/count/q*1e6)
    task_index = {(r["cell"]["task"], r["cell"]["case"], r["cell"]["arm"], r["cell"]["q"]): r for r in task["cells"]}
    representatives = (("assignment_batch", "balanced-k8", "cm_batch", 1),
                       ("restriction", "balanced-k8", "cm_packed", 64),
                       ("simplified_expression", "balanced-k8", "cm_shared_minimizer", 1),
                       ("family", "shared_seed2", "cm_cache_on", 1),
                       ("family", "identical_seed2", "public_cache_on", 1))
    for key in representatives:
        row = task_index[key]
        rows = [(name, p["mean_wall_ns"]/1000, p["mean_cpu_ns"]/1000, p["percent_mean_caller"]) for name, p in sorted(row["phases"].items(), key=lambda item: -item[1]["mean_wall_ns"])]
        phase_table(lines, " / ".join(map(str, key)) + " whole task", rows, row["phase_mean_caller_ns"]/1000, row["phase_mean_caller_cpu_ns"]/1000)
    dilations = [r["phase"][t]["instrumentation_dilation_ratio"] for r in ladder["cells"] for t in ("cold_q1", "resident_q64")]
    task_dilations = [r["phase_dilation"] for r in task["cells"]]
    lines += ["", "## 7. Perturbation, omitted splits and predecessor quantitative context", "",
              f"Ladder instrumentation dilation: median **{statistics.median(dilations):.2f}×**, range **{min(dilations):.2f}×–{max(dilations):.2f}×** over274 cell/treatment ratios. Task phase dilation: median **{statistics.median(task_dilations):.2f}×**, range **{min(task_dilations):.2f}×–{max(task_dilations):.2f}×**. These separate-pass ratios are not correction factors; values below1 are retained. Task and ladder pass definitions differ and are not pooled.", "",
              "`cache lookup/validation/binding` and `kernel/allocation/release` are grouped where the code does not expose independent spans. Persistent-cache validation has no equality-fallback phase; reported count placeholders from diagnostics-free family runs are null in the task summary. CPU allocation to tiny phases and native allocation traffic remain unresolved. Symbolic, SAT/count and BDD preparations belong to those algorithms and cannot be relabelled CM wrapper cost.", "",
              "Frozen predecessor observations remain quantitatively separate from local timings:", "",
              "| Frozen source | Read measured rows | Exact quantitative location |", "|---|---:|---|",
              f"| SymPy development Y02–Y05 | {frozen['sympy_gate']['rows']} | `frozen_evidence.json.sympy_gate`: nine gate ratios, per-arm/case caller/task spans and residuals |",
              f"| Performance development | {frozen['performance_development']['raw_rows']} | `performance_development`: cold/warm session times, separate strengthened CSE, staged spans and process lifecycle |",
              f"| Continuation development | {frozen['continuation_development']['rows']} | `continuation_development`: setup/query-delivery/cleanup exact partitions and separate warm/memory data |",
              "| Architecture retry and corrected Clang query ladder | separate historical schedules | `architecture.retry002_gcc` and `architecture.query_ladder_clang`: absolute stage distributions, own-total shares and query counts |", "",
              "See [FROZEN_EVIDENCE.md](FROZEN_EVIDENCE.md) for the complete reaggregation, source-custody verification and timer-overlap prohibitions. Historical caller residuals are not automatically startup costs; query-prefix correctness hashes are not q1 latency measurements; old cumulative profile rows cannot yield exclusive shares. No existing evidence or claim disposition was rewritten.", "",
              "## 8. Reproduction", "",
              "`python -B make_time_ledger.py --output <new-file-in-this-audit.md>` reads only the three saved summaries, performs arithmetic and refuses overwrite. Input SHA-256 values:", ""]
    for name, digest in hashes.items():
        lines.append(f"* `{name}`: `{digest}`")
    lines += ["", "No further timing is needed to reproduce this ledger. Unresolved splits remain explicitly unresolved; no scientific disposition changed.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE / "TIME_LEDGER.md")
    args = parser.parse_args()
    if args.output.exists() or not args.output.resolve().is_relative_to(HERE):
        raise ValueError("new output inside this audit required")
    names = ("ladder_summary.json", "TASK_SUMMARY.json", "frozen_evidence.json")
    raw = {name: (HERE / name).read_bytes() for name in names}
    values = [json.loads(raw[name]) for name in names]
    result = render(*values, {name: hashlib.sha256(raw[name]).hexdigest() for name in names})
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(result)
    print(json.dumps({"output": str(args.output), "ladder_cells": 137, "task_cells": 70}))


if __name__ == "__main__":
    main()
