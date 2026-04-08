# CM_parallel Stress Test Report

## 1. Configuration
- Base stress config used: `--sizes 12,16,18 --trials 5 --max-depth 6 --seed 123 --cm-layout legacy_square --cm-parallel --cm-parallel-workers 4 --cm-parallel-min-n 1 --cm-parallel-min-nodes 1 --cm-parallel-chunk-elems <CE> --cm-parallel-min-work-elems <MW> --cm-hybrid-threshold 0 --cm-debug-stats --no-robdd --no-dd --no-espresso --no-sympy --no-bdd-sop --no-numba`
- Attempted to disable reductions: no CLI flags exist in `cm_bench.py` help output for subtree memoization/pruning/canonical rewrites/DAG reuse (only parallel flags are exposed).
- Note on `n=18`: `cm_bench.py` does not run CM/CM_parallel when it skips TT building for `n>16`, so `n=18` rows are `NaN` in these benchmark CSVs.

## 2. Activation Results
- Activation rate (all stress-grid trials): 0.000 (activated_trials=0/135)
- Pool starts sum (all stress-grid trials): 0
- Fallback reasons (stress grid, all trials):
  - `small_total_work`: 90
  - `(missing)`: 45
- Observed `live_vars_max` (stress grid): max=15. This implies per-combine element counts up to ~`2^15` (e.g. 32768 if fully-live).
- With `--cm-parallel-min-work-elems >= 50000`, this max live-k regime is still below the activation threshold in most combines, explaining the consistent `small_total_work` fallbacks.

## 3. Chunking Behavior
- Stress grid: no activation observed, so chunk size distribution was not measurable (no `chunk_sizes` diagnostics emitted).
- Additional activation-forcing run (not in the prompt’s MW sweep): `--cm-parallel-min-work-elems 10000` with `--cm-parallel-chunk-elems 10000` (sizes 12,16).
  - activated_trials=2/10
  - example `chunk_sizes`: 10000,6384
  - observed max `number_of_chunks`=4, max `chunk_size_min`=6384, max `chunk_size_max`=10000

## 4. Performance Results

| n | chunk_elems | min_work | cm_time | cm_parallel_time | ratio |
|---|------------|----------|--------:|-----------------:|------:|
| 12 | 10000 | 50000 | 0.002568 | 0.003273 | 1.275 |
| 12 | 10000 | 250000 | 0.002280 | 0.002966 | 1.301 |
| 12 | 10000 | 1000000 | 0.002724 | 0.002998 | 1.101 |
| 12 | 100000 | 50000 | 0.003015 | 0.003391 | 1.125 |
| 12 | 100000 | 250000 | 0.002711 | 0.002766 | 1.020 |
| 12 | 100000 | 1000000 | 0.002807 | 0.004285 | 1.526 |
| 12 | 1000000 | 50000 | 0.002356 | 0.003714 | 1.577 |
| 12 | 1000000 | 250000 | 0.003063 | 0.003222 | 1.052 |
| 12 | 1000000 | 1000000 | 0.002265 | 0.003156 | 1.394 |
| 16 | 10000 | 50000 | 0.002393 | 0.004706 | 1.966 |
| 16 | 10000 | 250000 | 0.002753 | 0.003017 | 1.096 |
| 16 | 10000 | 1000000 | 0.004280 | 0.003410 | 0.797 |
| 16 | 100000 | 50000 | 0.003709 | 0.004474 | 1.206 |
| 16 | 100000 | 250000 | 0.002644 | 0.003920 | 1.483 |
| 16 | 100000 | 1000000 | 0.002267 | 0.003285 | 1.449 |
| 16 | 1000000 | 50000 | 0.003504 | 0.004013 | 1.145 |
| 16 | 1000000 | 250000 | 0.002373 | 0.003791 | 1.598 |
| 16 | 1000000 | 1000000 | 0.003293 | 0.005434 | 1.650 |

Extra activation-forcing run (MW=10000):

| n | chunk_elems | min_work | cm_time | cm_parallel_time | ratio |
|---|------------|----------|--------:|-----------------:|------:|
| 12 | 10000 | 10000 | 0.002387 | 0.002721 | 1.140 |
| 16 | 10000 | 10000 | 0.003142 | 0.002948 | 0.938 |

## 5. Key Findings
- Did CM_parallel activate under stress? Not under the prompt’s MW sweep (`min_work >= 50000`): activation_rate was 0.0 and fallbacks were dominated by `small_total_work`.
- Did it provide speedup? No consistent speedup in the stress grid; results mostly show overhead without activation (ratios often > 1).
- At what size does it help? In this repo’s random-expr benchmark family, live tensors rarely exceed ~`2^15` elements even under `legacy_square` + `hybrid_threshold=0`; with `min_work >= 50000` that stays below activation. Lowering `min_work` to 10000 triggered occasional activation (2/10 trials) and showed a small win at `n=16` in that run.
- Is chunking effective? When activation occurs (extra run), chunk ranges are contiguous and chunk sizes match the flat element-block scheduler output (e.g. `10000,6384` for a 16384-element combine), but activation frequency was low.

## 6. Final Verdict
CM_parallel activates but provides limited benefit

Justification: Under the prompt’s stress grid, activation never occurs because `min_work` is still above the largest observed live-tensor combines. When `min_work` is lowered enough to allow activation, parallel combine triggers and chunk diagnostics appear, but measured speedups are small and activation is intermittent for these random expressions.
