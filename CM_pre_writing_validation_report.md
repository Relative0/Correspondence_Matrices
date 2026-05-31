# CM Pre-Writing Validation Report

## 1. Executive Summary

Phase A validated `n=32` safely in an explicit large-`n` structural mode. The benchmark now refuses accidental full no-reinflate output materialization above the configured limit unless `--large-n-safe` opts into reduced live-variable output. In the `n=20..32` runs, no dense CM matrix or full truth-table vector was materialized; final outputs used representation code `3` (reduced packed bitset).

Phase B supports the compile-once/evaluate-many framing. Cached no-reinflate execution stabilizes by roughly `N=10..50`; at `n=16` it is about `2.1x..2.5x` direct bitset, while smaller or heavily reduced outputs show fixed overhead more clearly.

Phase C shows the remaining overhead is mostly execution scaffolding plus the CM bitset invocation path. For nominal `n=16`, the CM cached path is still dominated by bitset evaluation itself. For tiny reduced outputs, dispatch, variable ordering, and result wrapping become a larger fraction because the core bitset work is very small.

Overall recommendation: `Ready to write`, with one caveat: describe `n=32` as structural/reduced-live validation, not exact full truth-table validation.

## 2. Phase A: n=32 Feasibility

Safety audit:
- Full TT correctness remains limited by `--full-tt-max-n` (default `16`).
- Added `--large-n-safe` for structural large-`n` no-reinflate benchmarking.
- Added `--cm-max-full-output-vars`; no-reinflate raises instead of producing a nominal full output above this limit unless reduced output is explicitly allowed.
- Large no-reinflate outputs use `output_vars = live_vars`, not all nominal variables.
- Dense CM, dense hybrid, partial hybrid reinflation, parallel CM, SymPy, Espresso, BDD, ROBDD, BDD-SOP, and Numba were disabled for the large sweep.

Command:

```bash
python cm_bench.py --sizes 16,20,24,28,32 --trials 3 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 10 --cm-hybrid-threshold 7 --cm-report-ir-breakdown --large-n-safe --no-dd --no-espresso --no-sympy --no-robdd --no-bdd-sop --no-numba --print-summary --out-prefix bench_n32_scaling
```

| n | completed | no_reinflate_time | cached_exec | bitset_time | cached_ratio | live_vars/out_vars | IR_nodes | final_repr | final_cm_mat | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16 | yes | 0.000238 | 0.0000518 | 0.0000759 | 2.13 | 16 | 9 | 2 | 0 | exact full |
| 20 | yes | 0.000208 | 0.0000217 | 0.0000054 | 1.75 | 7 | 16 | 3 | 0 | reduced |
| 24 | yes | 0.000131 | 0.0000192 | 0.0000043 | 8.05 | 5 | 10 | 3 | 0 | reduced |
| 28 | yes | 0.000053 | 0.00000817 | 0.0000022 | 7.36 | 2 | 4 | 3 | 0 | reduced |
| 32 | yes | 0.000204 | 0.0000332 | 0.0000063 | 7.99 | 5 | 15 | 3 | 0 | reduced |

Answers:
- `n=32` ran.
- No path allocated or attempted a dense `2^32` TT vector or dense CM matrix in the large-`n` safe mode.
- CM reduction kept effective output size small: `n=32` returned 5 output vars (`32` packed rows) instead of nominal `2^32`.
- Runtime follows reduced live structure more than nominal `n`.
- This is safe enough to mention in the paper as structural/reduced-live feasibility.

Verdict: `n=32 validated safely`.

## 3. Phase B: Compile-Once / Evaluate-Many

Small exact commands used `--sizes 4,8,12,16 --trials 5`; large structural commands used `--sizes 16,20,24,28,32 --trials 3 --large-n-safe`. Repeat counts were `1,10,50,100`, with persistent cache and no-reinflate enabled.

Small exact-TT results:

| n | repeat_N | cm_cached_per_eval | bitset_cached_per_eval | ratio | final_repr |
| --- | --- | --- | --- | --- | --- |
| 4 | 10 | 0.0000286 | 0.00000243 | 11.78 | 2 |
| 8 | 10 | 0.0000203 | 0.00000244 | 8.30 | 2 |
| 12 | 10 | 0.0000353 | 0.00000584 | 6.05 | 2 |
| 16 | 10 | 0.0000550 | 0.0000237 | 2.32 | 2 |
| 4 | 100 | 0.0000196 | 0.00000209 | 9.38 | 2 |
| 8 | 100 | 0.0000196 | 0.00000235 | 8.35 | 2 |
| 12 | 100 | 0.0000333 | 0.00000605 | 5.51 | 2 |
| 16 | 100 | 0.0000525 | 0.0000240 | 2.19 | 2 |

Large structural results:

| n | repeat_N | cm_cached_per_eval | bitset_cached_per_eval | ratio | final_repr |
| --- | --- | --- | --- | --- | --- |
| 16 | 100 | 0.0000549 | 0.0000238 | 2.31 | 2 |
| 20 | 100 | 0.0000216 | 0.0000033 | 6.56 | 3 |
| 24 | 100 | 0.0000194 | 0.00000254 | 7.63 | 3 |
| 28 | 100 | 0.00000878 | 0.00000312 | 2.81 | 3 |
| 32 | 100 | 0.0000309 | 0.00000347 | 8.90 | 3 |

Answers:
- Compile-once/evaluate-many improves CM+bitset as expected; the cached execution window removes compile cost from the measured path.
- Runtime stabilizes by `N=10..50` for these expressions.
- Cached no-reinflate gets closest at nominal `n=16` (`~2.1x..2.5x` direct cached bitset).
- Larger nominal `n` does not itself determine the ratio; reduced live-variable count and expression shape matter more.
- This supports the `CM as compiler` framing, with the caveat that pure bitset remains the flat-kernel lower bound.

Verdict: `compile-once/evaluate-many strongly supports CM-as-compiler`.

## 4. Phase C: Cached-Execution Overhead

Instrumentation added:
- `--cm-profile-cached-exec`
- `cached_exec_total_time_s`
- `cached_exec_dispatch_time_s`
- `cached_exec_var_order_time_s`
- `cached_exec_fixed_handling_time_s`
- `cached_exec_bitset_eval_time_s`
- `cached_exec_result_wrap_time_s`
- `cached_exec_correctness_or_extract_time_s`
- `cached_exec_other_time_s`
- counts for cached evaluations, bitset calls, result wrappers, fallback TT vectors, packed bitset returns, and reduced outputs

Command:

```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 100 --cm-profile-cached-exec --cm-hybrid-threshold 7 --no-dd --no-espresso --no-sympy --no-robdd --no-bdd-sop --no-numba --out-prefix bench_cached_exec_profile
```

Per-eval medians:

| n | cm_cached | bitset_cached | ratio | bitset_eval | dispatch | var_order | result_wrap | other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 0.0000268 | 0.00000220 | 12.20 | 0.0000183 | 0.00000211 | 0.000000968 | 0.00000215 | 0 |
| 8 | 0.0000249 | 0.00000250 | 9.96 | 0.0000184 | 0.00000202 | 0.00000105 | 0.00000189 | 0 |
| 12 | 0.0000428 | 0.00000751 | 5.70 | 0.0000356 | 0.00000216 | 0.00000129 | 0.00000209 | 0 |
| 16 | 0.0000637 | 0.0000303 | 2.10 | 0.0000553 | 0.00000227 | 0.00000141 | 0.00000235 | 0 |

Answers:
- Largest component at exact small sizes is bitset evaluation through the CM node evaluator.
- Remaining fixed overhead is structural dispatch, variable ordering, and result wrapping.
- At `n=16`, bitset core evaluation is still dominant inside cached CM execution.
- Flattening/codegen/JIT would likely help by removing recursive IR traversal and wrapper dispatch.
- This is useful future work, but not necessary before writing.

Verdict: `remaining overhead is execution scaffolding and should be future work`.

## 5. Overall Recommendation Before Writing

`Ready to write`.

Write the paper around:
- CM as a structure-preserving compiler/optimizer.
- Bitset as the flat execution kernel.
- No-reinflate output as the correct execution path when a CM matrix is not the desired artifact.
- Compile-once/evaluate-many as the natural usage model.

## 6. Paper-Relevant Takeaways

- CM can be used as a structural compiler.
- Dense CM materialization should be avoided unless a CM matrix is explicitly required.
- Compile-once/evaluate-many is the natural usage model.
- Persistent cache and no-reinflation make CM+bitset much closer to bitset performance, especially after compile cost is removed.
- Nominal `n` is less predictive than reduced live structure.
- `n=32` is feasible as structural/reduced-live validation, not as exact full truth-table enumeration.
- Parallel dense CM execution is not useful after structural reduction for this path.

## 7. New Thread Handoff Summary

```text
SYSTEM SUMMARY FOR NEW THREAD

Architecture:
- Best path is compile Expr to CM IR, then evaluate with hybrid_no_reinflate.
- Bitset is the flat execution kernel; dense CM matrix output is only for matrix-output contracts.
- Large-n safe mode uses reduced live-variable outputs to avoid full 2^n materialization.

Validated Results:
- n=32 completed with --large-n-safe, persistent cache, no-reinflate, repeat=10.
- Large n=20..32 returned representation code 3 (reduced packed bitset), no dense CM materialization.
- Cached execution stabilizes by N=10..50; n=16 cached CM is about 2.1x..2.5x direct cached bitset.

Current Best Mode:
- --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat N --cm-hybrid-threshold 7.
- Add --large-n-safe for n > 16 structural validation.

Open Questions:
- Whether to flatten/codegen CM IR evaluation to reduce dispatch and wrapper overhead.
- Whether future paper experiments need sampled correctness beyond reduced structural equality.

Constraints:
- Do not claim exact full n=32 truth-table validation.
- Keep dense CM, full TT extraction, BDD/SymPy/Espresso/Numba disabled for large-n validation.
```
