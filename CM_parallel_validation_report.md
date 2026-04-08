# CM_parallel Validation Report

## 1. Benchmark Configuration
- Fixed args: `--sizes 8,12,16 --max-depth 4 --trials 10 --seed 123 --cm-layout balanced --cm-parallel --cm-parallel-workers 4 --cm-parallel-min-n 1 --cm-parallel-min-nodes 1 --cm-debug-stats --no-robdd --no-dd --no-espresso --no-sympy --no-bdd-sop --no-numba`
- Command template: `python cm_bench.py --sizes 8,12,16 --trials 10 --seed 123 --max-depth 4 --cm-layout balanced --cm-parallel --cm-parallel-workers 4 --cm-parallel-min-n 1 --cm-parallel-min-nodes 1 --cm-parallel-chunk-elems <CE> --cm-parallel-min-work-elems <MW> --cm-hybrid-threshold <HT> --cm-debug-stats --no-robdd --no-dd --no-espresso --no-sympy --no-bdd-sop --no-numba --out-prefix cmpar_val_ht<HT>_ce<CE>_mw<MW> --print-summary`
- `--cm-hybrid-threshold`: `[0, 3]`
- `--cm-parallel-chunk-elems`: `[10000, 100000, 1000000]`
- `--cm-parallel-min-work-elems`: `[50000, 250000, 1000000]`
- Optional spot-check: `--cm-parallel-no-reuse-pool` at `ht=3, ce=100000, mw=250000`

## 2. Activation Behavior
- Overall activation_rate across all configs/n: min=0.000, median=0.000, max=0.000.
- n=8: activation_rate min=0.000, median=0.000, max=0.000
- n=12: activation_rate min=0.000, median=0.000, max=0.000
- n=16: activation_rate min=0.000, median=0.000, max=0.000
- Pool starts (reuse enabled): total sum=0, groups with any pool starts=0.
- Fallback reasons among non-activated trials (top):
  - `small_total_work`: 441
  - `(missing)`: 99

## 3. Chunking Analysis
- No trials activated `CM_parallel` combine (`parallel_combine_activations > 0` was never observed), so chunk size distribution cannot be evaluated on this benchmark grid.
- Evidence: `live_vars_max` stayed small; overall max observed was 9.

## 4. Performance Results

| n | ht | chunk_elems | min_work | cm_time | cm_parallel_time | ratio_parallel/cm | ratio_parallel/bitset |
|---|----|------------|----------|--------:|-----------------:|------------------:|----------------------:|
| 8 | 0 | 10000 | 50000 | 0.000852 | 0.000773 | 0.908 | 39.743 |
| 12 | 0 | 10000 | 50000 | 0.000759 | 0.000839 | 1.105 | 33.968 |
| 16 | 0 | 10000 | 50000 | 0.001398 | 0.002210 | 1.580 | 16.959 |
| 8 | 0 | 10000 | 250000 | 0.000674 | 0.000996 | 1.478 | 64.672 |
| 12 | 0 | 10000 | 250000 | 0.000646 | 0.001135 | 1.756 | 37.645 |
| 16 | 0 | 10000 | 250000 | 0.001550 | 0.002507 | 1.617 | 18.711 |
| 8 | 0 | 10000 | 1000000 | 0.000738 | 0.000797 | 1.080 | 40.552 |
| 12 | 0 | 10000 | 1000000 | 0.000885 | 0.001133 | 1.280 | 37.826 |
| 16 | 0 | 10000 | 1000000 | 0.001748 | 0.002408 | 1.377 | 18.670 |
| 8 | 0 | 100000 | 50000 | 0.000645 | 0.000803 | 1.245 | 48.222 |
| 12 | 0 | 100000 | 50000 | 0.000617 | 0.000816 | 1.322 | 34.205 |
| 16 | 0 | 100000 | 50000 | 0.001795 | 0.002976 | 1.658 | 16.048 |
| 8 | 0 | 100000 | 250000 | 0.000807 | 0.001042 | 1.290 | 59.520 |
| 12 | 0 | 100000 | 250000 | 0.000693 | 0.001024 | 1.478 | 40.882 |
| 16 | 0 | 100000 | 250000 | 0.001717 | 0.002054 | 1.196 | 15.993 |
| 8 | 0 | 100000 | 1000000 | 0.000873 | 0.000829 | 0.950 | 38.572 |
| 12 | 0 | 100000 | 1000000 | 0.000590 | 0.000996 | 1.688 | 39.695 |
| 16 | 0 | 100000 | 1000000 | 0.001496 | 0.002308 | 1.543 | 17.502 |
| 8 | 0 | 1000000 | 50000 | 0.000673 | 0.000909 | 1.351 | 49.279 |
| 12 | 0 | 1000000 | 50000 | 0.000860 | 0.001224 | 1.424 | 43.476 |
| 16 | 0 | 1000000 | 50000 | 0.001925 | 0.001978 | 1.027 | 12.581 |
| 8 | 0 | 1000000 | 250000 | 0.000716 | 0.000843 | 1.179 | 44.384 |
| 12 | 0 | 1000000 | 250000 | 0.000664 | 0.001023 | 1.540 | 37.413 |
| 16 | 0 | 1000000 | 250000 | 0.001424 | 0.002409 | 1.691 | 18.565 |
| 8 | 0 | 1000000 | 1000000 | 0.000862 | 0.001153 | 1.337 | 43.184 |
| 12 | 0 | 1000000 | 1000000 | 0.001266 | 0.001594 | 1.259 | 38.553 |
| 16 | 0 | 1000000 | 1000000 | 0.002019 | 0.002615 | 1.295 | 18.374 |
| 8 | 3 | 10000 | 50000 | 0.000689 | 0.000585 | 0.849 | 38.121 |
| 12 | 3 | 10000 | 50000 | 0.000553 | 0.000777 | 1.404 | 28.517 |
| 16 | 3 | 10000 | 50000 | 0.001463 | 0.001703 | 1.163 | 12.631 |
| 8 | 3 | 10000 | 250000 | 0.000609 | 0.000585 | 0.960 | 34.812 |
| 12 | 3 | 10000 | 250000 | 0.000563 | 0.000532 | 0.946 | 26.359 |
| 16 | 3 | 10000 | 250000 | 0.001620 | 0.001834 | 1.132 | 15.236 |
| 8 | 3 | 10000 | 1000000 | 0.000630 | 0.000784 | 1.245 | 34.236 |
| 12 | 3 | 10000 | 1000000 | 0.000649 | 0.000556 | 0.856 | 21.175 |
| 16 | 3 | 10000 | 1000000 | 0.001441 | 0.001473 | 1.022 | 11.845 |
| 8 | 3 | 100000 | 50000 | 0.000729 | 0.000674 | 0.924 | 41.085 |
| 12 | 3 | 100000 | 50000 | 0.000513 | 0.000688 | 1.342 | 29.157 |
| 16 | 3 | 100000 | 50000 | 0.001704 | 0.001617 | 0.949 | 13.078 |
| 8 | 3 | 100000 | 250000 | 0.000596 | 0.000588 | 0.987 | 38.195 |
| 12 | 3 | 100000 | 250000 | 0.000594 | 0.000749 | 1.261 | 32.479 |
| 16 | 3 | 100000 | 250000 | 0.001755 | 0.001978 | 1.127 | 11.411 |
| 8 | 3 | 100000 | 1000000 | 0.000593 | 0.000700 | 1.180 | 49.456 |
| 12 | 3 | 100000 | 1000000 | 0.000613 | 0.000732 | 1.193 | 31.740 |
| 16 | 3 | 100000 | 1000000 | 0.001446 | 0.001839 | 1.271 | 16.439 |
| 8 | 3 | 1000000 | 50000 | 0.000779 | 0.000624 | 0.801 | 38.619 |
| 12 | 3 | 1000000 | 50000 | 0.000978 | 0.000826 | 0.845 | 23.303 |
| 16 | 3 | 1000000 | 50000 | 0.002056 | 0.001902 | 0.925 | 11.619 |
| 8 | 3 | 1000000 | 250000 | 0.000574 | 0.000575 | 1.001 | 39.896 |
| 12 | 3 | 1000000 | 250000 | 0.000460 | 0.000661 | 1.436 | 28.932 |
| 16 | 3 | 1000000 | 250000 | 0.001519 | 0.001606 | 1.057 | 12.123 |
| 8 | 3 | 1000000 | 1000000 | 0.000751 | 0.000971 | 1.293 | 41.059 |
| 12 | 3 | 1000000 | 1000000 | 0.000856 | 0.000888 | 1.037 | 22.229 |
| 16 | 3 | 1000000 | 1000000 | 0.001528 | 0.001452 | 0.950 | 12.416 |

Best/Worst per (ht, n) based on `ratio_parallel/cm`:
- ht=0, n=8: best ratio=0.908 at ce=10000, mw=50000; worst ratio=1.478 at ce=10000, mw=250000
- ht=0, n=12: best ratio=1.105 at ce=10000, mw=50000; worst ratio=1.756 at ce=10000, mw=250000
- ht=0, n=16: best ratio=1.027 at ce=1000000, mw=50000; worst ratio=1.691 at ce=1000000, mw=250000
- ht=3, n=8: best ratio=0.801 at ce=1000000, mw=50000; worst ratio=1.293 at ce=1000000, mw=1000000
- ht=3, n=12: best ratio=0.845 at ce=1000000, mw=50000; worst ratio=1.436 at ce=1000000, mw=250000
- ht=3, n=16: best ratio=0.925 at ce=1000000, mw=50000; worst ratio=1.271 at ce=100000, mw=1000000

Optional `--cm-parallel-no-reuse-pool` spot-check (medians):

| n | ht | chunk_elems | min_work | cm_time | cm_parallel_time | ratio_parallel/cm | ratio_parallel/bitset |
|---|----|------------|----------|--------:|-----------------:|------------------:|----------------------:|
| 8 | 3 | 100000 | 250000 | 0.000628 | 0.000592 | 0.944 | 32.806 |
| 12 | 3 | 100000 | 250000 | 0.000675 | 0.000928 | 1.375 | 29.273 |
| 16 | 3 | 100000 | 250000 | 0.002041 | 0.002027 | 0.993 | 13.617 |

## 5. Overhead Analysis
- Config rows with `ratio_parallel/cm > 1`: 41 / 54
- In this grid, `parallel_combine_activations` was never observed, so `CM_parallel` behaves like `CM` plus additional scheduling checks; slowdowns here are consistent with overhead without offsetting parallel speedup.

## 6. Key Findings
- Does CM_parallel activate only when real work exists? Yes: it consistently did not activate and commonly reported `fallback_reason=small_total_work`, indicating the gate is working.
- Are chunk sizes large, balanced, and meaningful? Not measurable on this grid because no activations occurred.
- Does CM_parallel outperform CM at larger sizes? Not reliably; without activation it is often slightly slower (overhead) and sometimes slightly faster within noise.
- Is process pool overhead avoided when unnecessary? Yes: `parallel_pool_starts` stayed at 0 and activation rate was 0.
- Does the new scheduling align with actual expensive work? It is aligned to element count, but this benchmark workload rarely produced large live tensors (`live_vars_max` stayed small), so benefit was not exercised.

## 7. Clear Verdict
CM_parallel is somewhat improved but still marginal

Justification: The redesign correctly avoids pool startup and parallel work when combines are below the `min_work_elems` gate, but on this benchmark grid it never activates. There is therefore no demonstrated speedup regime here; to justify “genuinely useful”, we need a workload that preserves larger live-variable NumPy combine regions so chunking and scaling can be observed.
