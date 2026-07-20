# ROBDD / CM Fair Comparison Report

## 1. Executive Summary

The earlier tiny `dd.autoref` ROBDD results were partly explained by trivial random expressions: the ordinary random regime used only 3 to 5 variables at median for `n=4..16`, and never used all variables for `n >= 8`. However, the new all-vars regimes show that `dd.autoref` remains compact and fast on these generated formulas, with median ROBDD build times in the 0.0005-0.0026 s range and node counts from 6 to 307 for the tested `n <= 16` cases.

Bitset remains the fastest flat truth-table execution path. CM no-reinflate with persistent cache is stable but slower than bitset cached execution in these local small-`n` runs. ROBDD/dd.autoref is genuinely competitive as a symbolic build baseline for the tested formula regimes, but it is not measuring the same thing as full truth-table execution.

CUDD was not available in this environment, so these results should be labeled `dd.autoref`, not CUDD.

## 2. Audit

| Item | Current state | Needed change |
| ---- | ------------- | ------------- |
| dd-backed ROBDD | Present in `cm_bench.py` with `--robdd-dd-backend`, fixed/expr/random/best-of-k order policies, status fields, and exact small-`n` validation. | Added derived ROBDD diagnostics and ensured summary output includes node/time distribution fields. |
| Custom truth-table ROBDD | Present as legacy `bdd_time_s` / `bdd_nodes`, with `custom_tt_robdd_*` aliases. | Kept separate from `robdd_*`; report recommends explicit slide labels. |
| Expression styles | Existing `ordinary`, `broad`, `low-reuse`, `anti-reduction`. | Added `balanced_all_vars`, `xor_heavy`, `and_or_not`, `mixed_no_constants`. |
| Expression diagnostics | Only node count was broadly available. | Added depth, node/leaf/op counts, per-op counts, variables used, structural hash, simplified-constant marker where TT is safe. |
| Truth-table diagnostics | Not reported as benchmark diagnostics. | Added true/false count, density, constant flag, balanced-ish flag for safe `n`. |
| Nontrivial filtering | Not available. | Added optional `--require-nontrivial-expr` and threshold flags, with regeneration count/reason reporting. |
| CM/bitset summary | Existing fields were mostly internal names. | Added clear aliases for no-reinflate time, persistent-cache no-reinflate time, cached per-eval time, live-vars/materialization/final-repr fields. |
| Fair comparison preset | Not available. | Added `--compare-robdd-cm` convenience preset without hiding the explicit mode fields. |

## 3. Benchmark Configuration

Validation:

```bash
python -m compileall .
python -m pytest -q
```

Smoke:

```bash
python cm_bench.py --sizes 4,8 --trials 2 --max-depth 3 --cm-layout balanced --robdd-dd-backend autoref --robdd-order-policy fixed --print-summary --out-prefix smoke_robdd_cm_diag
```

Comparison runs:

```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --robdd-dd-backend autoref --robdd-order-policy best-of-k --robdd-order-sweeps 10 --print-summary --out-prefix bench_robdd_cm_random
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 5 --expr-style balanced_all_vars --require-nontrivial-expr --min-used-var-fraction 0.75 --min-tt-density 0.05 --max-tt-density 0.95 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --robdd-dd-backend autoref --robdd-order-policy best-of-k --robdd-order-sweeps 10 --print-summary --out-prefix bench_robdd_cm_balanced_all_vars
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 5 --expr-style mixed_no_constants --require-nontrivial-expr --min-used-var-fraction 0.75 --min-tt-density 0.05 --max-tt-density 0.95 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --robdd-dd-backend autoref --robdd-order-policy best-of-k --robdd-order-sweeps 10 --print-summary --out-prefix bench_robdd_cm_mixed_no_constants
```

XOR-heavy full-size attempts were stopped after excessive runtime. Reduced diagnostic run:

```bash
python cm_bench.py --sizes 4,8,12 --trials 3 --max-depth 5 --expr-style xor_heavy --require-nontrivial-expr --min-used-var-fraction 0.75 --min-tt-density 0.05 --max-tt-density 0.95 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --robdd-dd-backend autoref --robdd-order-policy best-of-k --robdd-order-sweeps 5 --print-summary --out-prefix bench_robdd_cm_xor_heavy
```

Additional random-regime order-policy checks:

```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --robdd-dd-backend autoref --robdd-order-policy fixed --print-summary --out-prefix bench_robdd_cm_random_fixed
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --robdd-dd-backend autoref --robdd-order-policy expr --print-summary --out-prefix bench_robdd_cm_random_expr
```

## 4. Expression Complexity Diagnostics

| n | style | median_depth | median_nodes | median_unique_vars | pct_uses_all_vars | pct_constant_tt | median_tt_density |
| -: | ----- | -----------: | -----------: | -----------------: | ----------------: | --------------: | ----------------: |
| 4 | ordinary | 5 | 9 | 3 | 0.4 | 0.0 | 0.500 |
| 8 | ordinary | 5 | 10 | 5 | 0.0 | 0.0 | 0.250 |
| 12 | ordinary | 5 | 15 | 5 | 0.0 | 0.0 | 0.500 |
| 16 | ordinary | 5 | 12 | 4 | 0.0 | 0.0 | 0.500 |
| 4 | balanced_all_vars | 7 | 66 | 4 | 1.0 | 0.0 | 0.375 |
| 8 | balanced_all_vars | 7 | 66 | 8 | 1.0 | 0.0 | 0.523 |
| 12 | balanced_all_vars | 7 | 65 | 12 | 1.0 | 0.0 | 0.500 |
| 16 | balanced_all_vars | 7 | 68 | 16 | 1.0 | 0.0 | 0.881 |
| 4 | mixed_no_constants | 7 | 65 | 4 | 1.0 | 0.0 | 0.500 |
| 8 | mixed_no_constants | 7 | 66 | 8 | 1.0 | 0.0 | 0.492 |
| 12 | mixed_no_constants | 7 | 64 | 12 | 1.0 | 0.0 | 0.801 |
| 16 | mixed_no_constants | 7 | 66 | 16 | 1.0 | 0.0 | 0.620 |
| 4 | xor_heavy | 7 | 65 | 4 | 1.0 | 0.0 | 0.438 |
| 8 | xor_heavy | 7 | 67 | 8 | 1.0 | 0.0 | 0.500 |
| 12 | xor_heavy | 7 | 65 | 12 | 1.0 | 0.0 | 0.508 |

## 5. ROBDD Results

| n | style | order_policy | backend | median_build_time_s | median_nodes | best_nodes | worst_nodes | ok_rate |
| -: | ----- | ------------ | ------- | ------------------: | -----------: | ---------: | ----------: | ------: |
| 4 | ordinary | best-of-k | dd.autoref | 0.000071 | 4 | 4 | 5 | 1.0 |
| 8 | ordinary | best-of-k | dd.autoref | 0.000097 | 6 | 6 | 8 | 1.0 |
| 12 | ordinary | best-of-k | dd.autoref | 0.000180 | 8 | 8 | 14 | 1.0 |
| 16 | ordinary | best-of-k | dd.autoref | 0.000097 | 5 | 5 | 7 | 1.0 |
| 4 | balanced_all_vars | best-of-k | dd.autoref | 0.000457 | 6 | 6 | 7 | 1.0 |
| 8 | balanced_all_vars | best-of-k | dd.autoref | 0.000731 | 30 | 30 | 46 | 1.0 |
| 12 | balanced_all_vars | best-of-k | dd.autoref | 0.001162 | 68 | 68 | 183 | 1.0 |
| 16 | balanced_all_vars | best-of-k | dd.autoref | 0.001539 | 162 | 162 | 551 | 1.0 |
| 4 | mixed_no_constants | best-of-k | dd.autoref | 0.000456 | 6 | 6 | 8 | 1.0 |
| 8 | mixed_no_constants | best-of-k | dd.autoref | 0.000810 | 25 | 25 | 46 | 1.0 |
| 12 | mixed_no_constants | best-of-k | dd.autoref | 0.001724 | 90 | 90 | 207 | 1.0 |
| 16 | mixed_no_constants | best-of-k | dd.autoref | 0.002539 | 307 | 307 | 785 | 1.0 |
| 4 | xor_heavy | best-of-k | dd.autoref | 0.000498 | 7 | 7 | 8 | 1.0 |
| 8 | xor_heavy | best-of-k | dd.autoref | 0.000707 | 17 | 17 | 27 | 1.0 |
| 12 | xor_heavy | best-of-k | dd.autoref | 0.001488 | 59 | 59 | 91 | 1.0 |

Random-regime order policies were similar because the ordinary expressions were small:

| n | fixed_nodes | expr_nodes | bestofk_nodes |
| -: | ----------: | ---------: | ------------: |
| 4 | 4 | 4 | 4 |
| 8 | 6 | 6 | 6 |
| 12 | 8 | 8 | 8 |
| 16 | 6 | 5 | 5 |

## 6. CM / Bitset / ROBDD Comparison

| n | style | bitset_time_s | cm_no_reinflate_s | cm_cached_exec_s | robdd_bestofk_s | notes |
| -: | ----- | ------------: | -----------------: | ----------------: | --------------: | ----- |
| 4 | ordinary | 0.000009 | 0.000078 | 0.000038 | 0.000071 | ordinary uses few vars |
| 8 | ordinary | 0.000010 | 0.000067 | 0.000025 | 0.000097 | ordinary uses few vars |
| 12 | ordinary | 0.000022 | 0.000102 | 0.000050 | 0.000180 | ordinary uses few vars |
| 16 | ordinary | 0.000046 | 0.000132 | 0.000053 | 0.000097 | ordinary uses few vars |
| 4 | balanced_all_vars | 0.000028 | 0.000252 | 0.000128 | 0.000457 | all vars |
| 8 | balanced_all_vars | 0.000031 | 0.000814 | 0.000559 | 0.000731 | all vars |
| 12 | balanced_all_vars | 0.000061 | 0.000893 | 0.000638 | 0.001162 | all vars |
| 16 | balanced_all_vars | 0.000205 | 0.001242 | 0.000999 | 0.001539 | all vars |
| 4 | mixed_no_constants | 0.000026 | 0.000242 | 0.000107 | 0.000456 | all vars |
| 8 | mixed_no_constants | 0.000030 | 0.000743 | 0.000554 | 0.000810 | all vars |
| 12 | mixed_no_constants | 0.000061 | 0.000864 | 0.000615 | 0.001724 | all vars |
| 16 | mixed_no_constants | 0.000202 | 0.001287 | 0.001130 | 0.002539 | all vars |
| 4 | xor_heavy | 0.000025 | 0.000205 | 0.000118 | 0.000498 | reduced run |
| 8 | xor_heavy | 0.000030 | 0.000865 | 0.000463 | 0.000707 | reduced run |
| 12 | xor_heavy | 0.000066 | 0.000831 | 0.000580 | 0.001488 | reduced run |

## 7. Interpretation

The old ordinary random expressions were too easy structurally: median unique variable count dropped to 4 at `n=16`, so the earlier tiny ROBDDs should not be used as evidence by themselves. The new all-vars styles remove that ambiguity. Under those regimes, `dd.autoref` node counts increase but remain modest for `n <= 16`.

ROBDD/dd.autoref remains compact in these tests. Best-of-k variable order matters more in the all-vars runs than in the ordinary random runs, as shown by larger best/worst spread at `n=12..16`.

CM no-reinflate with persistent cache remains stable and correct, but on these small dense truth-table cases bitset is still the fastest flat evaluator. CM cached execution is the relevant CM number for repeated execution, and it improves relative to one-shot no-reinflate but does not beat bitset locally here.

ROBDD should move upward in performance-ranking slides only if the slide is about symbolic build/representation compactness. It should not be ranked as a direct replacement for bitset truth-table execution without separately measuring truth-table extraction from the ROBDD.

## 8. Slide Label Recommendations

Use these labels:

| Baseline | Recommended label |
| -------- | ----------------- |
| Existing custom TT ROBDD | `Custom fixed-order ROBDD from truth table (in-repo Python)` |
| New dd.autoref AST path | `Symbolic ROBDD from AST (dd.autoref, order policy reported)` |
| Future CUDD path | `Symbolic ROBDD from AST (dd.cudd/CUDD, dynamic reordering reported separately)` |

Do not label `dd.autoref` results as CUDD. Do not merge custom truth-table ROBDD timings with symbolic ROBDD build timings.

## 9. Limitations

CUDD was unavailable in this environment. XOR-heavy at full requested scale was too slow with the full auxiliary baseline set, so the report uses a reduced XOR-heavy diagnostic (`n=4,8,12`, 3 trials, 5 sweeps). All truth-table balance diagnostics are limited to safe dense-truth-table sizes. The benchmark still measures ROBDD symbolic build time, not ROBDD truth-table extraction time.
