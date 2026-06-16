# CM Final Robustness Report

## 1 Executive Summary

The main architecture recommendation does not change:

```python
compiled = compile_expr(expr, use_persistent_cache=True)
result = evaluate_compiled(compiled, mode="hybrid_no_reinflate", vars_all=[...])
```

Writing should proceed, with one sharpened caveat: large-n success depends on the reduced live output staying small enough to materialize. The robustness pass exposed that an intentionally unreduced expression can retain too many live variables; the code now rejects reduced outputs above `--cm-max-full-output-vars` instead of attempting unsafe materialization.

The earlier `n=32` conclusion remains valid for the ordinary reduced-live workload. For less-reducible workloads, the practical boundary is the reduced output variable count, not nominal `n`.

## 2 Multi-Seed Results

Command family:

```powershell
.\.venv\Scripts\python.exe .\cm_bench.py --sizes 16,20,24,28,32 --trials 3 --max-depth 4 --seed <seed> --expr-style ordinary --out-prefix paper_robustness_seed_<seed> --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --cm-hybrid-threshold 7 --cm-report-ir-breakdown --large-n-safe --no-dd --no-espresso --no-sympy --no-robdd --no-bdd-sop --no-numba
```

Seeds: `123`, `456`, `789`, `2025`, `31415`.

| n | cached ratio mean | std | min | max | output vars min/median/max |
|---:|---:|---:|---:|---:|---:|
| 16 | 2.2920 | 0.4865 | 1.7293 | 2.8213 | 16 / 16 / 16 |
| 20 | 1.1911 | 0.2360 | 0.9467 | 1.5044 | 3 / 6 / 7 |
| 24 | 1.1276 | 0.0908 | 1.0068 | 1.2530 | 5 / 5 / 7 |
| 28 | 1.7255 | 1.2821 | 0.9613 | 3.9901 | 2 / 6 / 8 |
| 32 | 2.0151 | 1.8555 | 0.9298 | 5.3183 | 3 / 5 / 8 |

All five seeds completed at `n=32`. No dense CM materialization was performed. All rows reported `cm_hybrid_no_reinflate_ok_all=True` and `bitset_ok_all=True`.

Verdict: conclusions are qualitatively stable across seeds. The ordinary generator keeps reduced output small at `n=20..32`. Seeds `456` at `n=28` and `31415` at `n=32` are slower outliers, but not correctness or safety failures. A reviewer should consider the ordinary-workload result robust, provided the paper states that scaling follows reduced live-variable count.

## 3 Less-Reducible Stress Results

Stress modes added: `--expr-style broad`, `--expr-style low-reuse`, and `--expr-style anti-reduction`.

| style | n=16 output vars | n=32 output vars | n=16 cached ratio | n=32 cached ratio | verdict |
|---|---:|---:|---:|---:|---|
| ordinary | 16 | 5 | 2.1521 | 0.9989 | collapses strongly |
| broad | 16 | 16 | 5.2112 | 2.2409 | feasible, less reduced |
| low-reuse | 16 | 16 | 8.4240 | 2.0924 | feasible, materially slower |
| anti-reduction | 16 | 16 | 8.3173 | 3.2316 | feasible at bounded depth |

Reduction quality matters substantially. Ordinary expressions collapse to 2-7 output variables for large nominal `n`; stress expressions retained 16 output variables across `n=16..32`. The practical scaling boundary is therefore around the configured output cap, currently `--cm-max-full-output-vars 16` for these runs.

The unbounded anti-reduction attempt with deeper trees was too expensive and exposed a missing guard. That is now fixed: reduced outputs above the configured cap fail fast instead of attempting a huge truth-table-like materialization.

Verdict: `n=32` remains feasible when reduced live variables remain at or below the cap. It is not a claim that arbitrary 32-live-variable expressions can be materialized.

## 4 Sampled Correctness Results

Implemented `--sampled-correctness K`.

Projection method: each sampled full assignment is evaluated directly against the original AST. The no-reinflate result is indexed only by `result.output_vars`; for reduced output, the full assignment is projected to those variables in MSB-first order, and the packed bitset or reduced TT vector is read at that projected row.

Run: `n=20,24,28,32`, seeds `123`, `456`, `789`, `K=1000`, one trial per size.

| seeds | sizes | samples per row | mismatches | mismatch rate |
|---|---|---:|---:|---:|
| 123,456,789 | 20,24,28,32 | 1000 | 0 | 0.0 |

Verdict: yes, the paper can state that large-n reduced-live evaluation was validated with sampled assignment checks. This supplements structural validation without full truth-table enumeration.

## 5 Paper Packaging

Added:

- `run_paper_benchmarks.ps1`
- `paper_exact_summary.csv`
- `paper_large_n_summary.csv`
- `paper_robustness_summary.csv`
- `paper_stress_summary.csv`
- `paper_sampled_correctness_summary.csv`

The runner reproduces exact small-n, large-n structural, multi-seed robustness, stress, and sampled-correctness outputs.

## 6 Final Recommendation

Ready to write immediately.

State the main result as: CM is a structural compiler/optimizer whose large-n behavior is governed by reduced live-variable output size. No-reinflate plus compiled-expression reuse avoids dense CM output and makes ordinary reduced-live `n=32` safe. Add the caveat that less-reducible expressions hit an output-variable boundary; the implementation now guards that boundary explicitly.

## 7 New Thread Handoff Summary

SYSTEM SUMMARY FOR NEW THREAD

CM benchmark best path is compile_expr(expr, use_persistent_cache=True), then evaluate_compiled(..., mode="hybrid_no_reinflate"). Bitset remains flat execution kernel; CM is structural optimizer. No-reinflate avoids dense CM output. Large-n-safe ordinary workload validates n=32 with reduced output vars about 3-8 across seeds, no dense materialization. Stress modes show less-reducible expressions can retain 16 live vars and slow down; arbitrary 32-live expressions are not claimed feasible. Added sampled correctness: full AST assignment evaluation projected onto result.output_vars; 3 seeds x n=20,24,28,32 x 1000 samples had zero mismatches. Added output cap guard and run_paper_benchmarks.ps1.
