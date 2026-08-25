# CM Deep Performance Benchmark Results

Audit date: **2026-08-25**. Ratios below one favor the candidate. All packed comparisons use identical expressions, semantic support, fixed bindings, and output order. BX1 is tuning evidence; B2 and EPFL are **reused validation**, not untouched held-out data.

## Environment and preservation

- Repository: `C:\Users\brian\Documents\CM_Computation`
- Starting branch / HEAD: `main` / `1ba3a7312fa99439b57ddb3b4433ead7e86b2c74`
- OS/CPU: Windows 10.0.19045, AMD64 Family 25 Model 80, 12 logical CPUs, process mask `0xfff`
- Audit interpreter: `.venv\Scripts\python.exe`, CPython 3.13.5, MSC v.1943 64-bit
- Dependencies: NumPy 2.3.2, pandas 2.3.2, SymPy 1.14.0, `dd` 0.6.0; Numba, pytest, and psutil absent from `.venv`
- Test interpreter: global CPython 3.10.11 with pytest 9.0.2, because pytest is not installed in `.venv`
- Thread variables: `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, and `VECLIB_MAXIMUM_THREADS` unset
- Starting status, dependency versions, corpus/source hashes, affinity, and exact dirty-file list are preserved in `baseline_smoke_environment.json`. Pre-existing website, README, benchmark, correction, and audit edits were not changed or attributed to this audit.

No dependencies were installed and no external compute was started. Every writer used a new prefix and refused overwrite.

## Timing definitions

| Window | Definition |
|---|---|
| Structural hash | `expr_structural_hash` only; excludes serialization and compile |
| CM compile | external wall time for `compile_expr_to_cm_ir`; cold per invocation; excludes evaluator lowering |
| Instrumented IR phases | diagnostic timers inside canonicalize, rewrite, intern, live-support union; timers are non-overlapping by construction but instrumentation itself adds overhead |
| Lowering | CM-node or expression DAG to a flat slot program; excludes packed execution |
| Bare kernel | prepared flat-bigint or NumPy-word program execution; batch divided to per-evaluation time |
| Wrapper | selection/binding/evaluator boundary around an already compiled node; separate from CM compile |
| End to end | compile plus current wrapper/evaluation for that call; excludes corpus load and benchmark reporting |
| Allocation | one cold compile per arm under `tracemalloc`; Python-traced peak, not RSS |
| Correctness | exact O(`s`) ordered CM-DAG signature plus exact packed truth integer/digest |

The memo ablation uses an odd number of repetitions and alternates baseline-first/candidate-first order per formula. Its reported ratio is the candidate median divided by the historical two-memo baseline median for the same formula. Aggregates are geometric means of per-formula ratios. Percentile intervals resample circuit/family clusters 2,000 times; they are descriptive robustness intervals, not a claim that formulas within a circuit are independent.

## Commands

### Clean smoke baseline and post-change smoke

```powershell
& .\.venv\Scripts\python.exe scripts\cm_deep_performance_audit.py `
  --suite smoke --corpora bx1,b2,epfl --prep-repetitions 3 `
  --kernel-rounds 5 --max-kernel-temporary-bytes 8388608 `
  --output-prefix docs\audits\2026-08-25-cm-deep-performance\baseline_smoke

& .\.venv\Scripts\python.exe scripts\cm_deep_performance_audit.py `
  --suite smoke --corpora bx1,b2,epfl --prep-repetitions 3 `
  --kernel-rounds 5 --max-kernel-temporary-bytes 8388608 `
  --output-prefix docs\audits\2026-08-25-cm-deep-performance\post_memo_smoke
```

The second command validates the changed tree. Separate-process smoke results are **not** used as the before/after performance estimate because process/schedule variance was larger than the candidate effect.

### Profile

```powershell
& .\.venv\Scripts\python.exe -m cProfile `
  -o docs\audits\2026-08-25-cm-deep-performance\baseline_smoke.prof `
  scripts\cm_deep_performance_audit.py --suite smoke --corpora bx1,b2,epfl `
  --prep-repetitions 3 --kernel-rounds 3 --max-kernel-temporary-bytes 8388608 `
  --output-prefix docs\audits\2026-08-25-cm-deep-performance\profiled_smoke
```

### Paired memo ablation

```powershell
# Allocation/correctness smoke, 25 rows.
& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite smoke --corpora bx1,b2,epfl --repetitions 11 `
  --output-prefix docs\audits\2026-08-25-cm-deep-performance\memo_ablation_smoke

# Representative BX1+B2, 272 rows.
& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite representative --corpora bx1,b2 --repetitions 11 --skip-allocation `
  --output-prefix docs\audits\2026-08-25-cm-deep-performance\memo_ablation_bx1_b2

# Representative EPFL was run in bounded 20-root chunks; repeat for starts
# 0,20,40,60,80,100 and start 120 with limit 9.
& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite representative --corpora epfl --repetitions 5 --skip-allocation `
  --record-start 0 --record-limit 20 `
  --output-prefix docs\audits\2026-08-25-cm-deep-performance\memo_ablation_epfl_000_019
```

After the candidate became production, the harness was changed to construct both the historical two-memo baseline and one-memo candidate explicitly. The reproducibility smoke was:

```powershell
& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite smoke --corpora bx1,b2,epfl --repetitions 7 `
  --output-prefix docs\audits\2026-08-25-cm-deep-performance\memo_ablation_repro_smoke
```

### Tests

```powershell
python -m pytest -q tests\test_build_memo.py tests\test_share_aware_flatten.py `
  tests\test_persistent_path_consistency.py tests\test_cm_ir_cost.py `
  --basetemp docs\audits\2026-08-25-cm-deep-performance\.pytest_tmp_memo_01

python -m pytest -q `
  --basetemp docs\audits\2026-08-25-cm-deep-performance\.pytest_tmp_full_01
```

## Baseline profile

The 25-row smoke is deliberately a quick path check, not the selector acceptance corpus.

| Corpus | Rows | Median CM compile | Median current wrapper | Median end to end | Median CM flat kernel | Median CM words kernel |
|---|---:|---:|---:|---:|---:|---:|
| BX1 | 10 | 153.1 us | 17.6 us | 172.8 us | 2.11 us | 9.01 us |
| B2 | 6 | 321.5 us | 21.3 us | 338.9 us | 3.78 us | 13.34 us |
| EPFL | 9 | 725.4 us | 42.4 us | 809.7 us | 25.77 us | 46.66 us |

Representative diagnostic phase fractions of CM compile:

| Phase | BX1 median fraction | B2 median fraction | EPFL median fraction | Calls / cProfile context |
|---|---:|---:|---:|---|
| Interning | 21.9% | 21.1% | 26.2% | 6,324 `_intern` calls across 150 profiled compiles |
| Lower CM flat program | 14.6% | 10.4% | 12.5% | separate lowering window |
| Live-variable unions | 10.0% | 10.3% | 11.0% | 2,736 calls |
| Structural hash | 10.7% | 8.9% | 11.8% | separate external hash window |
| Rewrite | 7.6% | 11.3% | 7.3% | instrumented builder window |
| Canonicalize | 5.9% | 6.7% | 6.1% | 2,622 calls |

The complete cProfile run made 6,898,109 calls in 6.313 s. Harness word evaluation consumed 2.379 s and selector bootstrapping 2.027 s; these are benchmark-driver costs, not CM compile costs. The 150 CM compiles consumed 0.370 s cumulative: `_build_rec` 0.296 s, `_intern` 0.089 s cumulative, `_shared_assoc_uids` 0.070 s, live-variable union 0.061 s, and canonicalization 0.031 s. Diagnostic `_bump`/timing calls are visible, so production absolute timing should come from the external wall clock, not phase-timer sums.

Scaling evidence remains consistent with the accepted B3 study: compile follows structural DAG size `s`, not unfolded tree count `t`. The current profile exposes distributed constant-factor costs rather than one catastrophic pass.

## Implemented candidate: remove redundant identity memo

Before the change, the default sharing-aware build maintained both:

1. `uid_by_id` plus `memo_by_uid`, created by the sharing/fanout prepass; and
2. `id(expr) -> (expr, CMNode)` for the same recursive build.

The candidate leaves the identity map unset only when the structural UID plan exists. The legacy `share_aware_flatten=False` path retains its lifetime-safe identity memo.

### Paired compile timing

| Slice | Rows | Repetitions | Candidate / baseline geomean | Cluster interval | Median ratio | p10 / p90 | Faster / slower | Exact mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BX1 tuning | 80 | 11 | **0.9581** | [0.9539, 0.9709] | 0.9609 | 0.9382 / 0.9953 | 73 / 7 | 0 |
| B2 reused validation | 192 | 11 | **0.9609** | [0.9496, 0.9724] | 0.9655 | 0.8896 / 1.0084 | 169 / 23 | 0 |
| BX1+B2 | 272 | 11 | **0.9601** | [0.9510, 0.9721] | 0.9642 | 0.9023 / 1.0020 | 242 / 30 | 0 |
| EPFL reused validation | 129 | 5 | **0.9768** | [0.9547, 0.9995] | 0.9711 | 0.8487 / 1.1490 | 91 / 38 | 0 |

The BX1+B2 result is a reproducible compile-time reduction of about 4.0%. EPFL’s point estimate is about 2.3%, but its upper clustered endpoint is near parity and its tails are wide. This is deliberately described as a smaller/noisier external confirmation, not a universal 2.3% claim.

### Allocation and retained memory

The 25-row `tracemalloc` smoke reported a candidate/baseline peak-byte geomean of **0.8820**, about 11.8% lower, with zero DAG or packed mismatches. The explicit-arm reproducibility smoke reported 0.8824. This measures one cold compile’s Python-traced peak. The removed map and `(expr, node)` tuples are compilation-temporary, so the expected retained-memory effect after `build()` is zero; the audit does not claim an RSS plateau improvement.

### Correctness

- BX1+B2: 272/272 exact ordered CM-DAG signatures and packed outputs matched.
- EPFL: 129/129 exact ordered CM-DAG signatures and packed outputs matched.
- Allocation and reproducibility smokes: 25/25 matched in each run.
- Focused tests: **33 passed, 4 subtests passed in 4.34 s**.
- Full suite: **359 passed, 4 subtests passed in 204.62 s**.
- Refuse-overwrite check: rerunning the tool against `memo_ablation_repro_smoke` exited before measurement and named all four existing targets; no artifact changed.

## Backend selector audit

No selector code changed in this audit. The corrected 401-row replay remains authoritative:

| Arm / role | Admitted | Current-policy regret geomean | Maximum | Rows >=2x |
|---|---:|---:|---:|---:|
| Raw / BX1 tuning | 80 | 1.0047 | 1.258 | 0 |
| Raw / reused validation | 307/321 | 1.0112 | 1.591 | 0 |
| CM / BX1 tuning | 80 | 1.0030 | 1.193 | 0 |
| CM / reused validation | 321 | 1.0100 | 1.900 | 0 |

The focused `k=13..15` replay still has one CM reused-validation row at 2.174x regret. Cross-machine results show that thresholds 14 and 15 trade circuit improvements for synthetic catastrophic misses. Therefore `WORDS_AUTO_MIN_VARS = 16` remains a conservative default, not a universal crossover theorem. A production feature selector needs a newly frozen untouched corpus; B2 and EPFL cannot supply that gate.

The exactly counterbalanced V3 strongest-comparator study supersedes the V2 local headline quoted in the original audit. Formula-balanced bare CM/CSE-flat is `0.890570` overall with formula-cluster 95% bootstrap interval `[0.874065, 0.907272]`, and `0.961234` at `k=16` with interval `[0.928974, 0.994177]`. Formula-balanced public CM wrapper/CSE-flat is `3.094136` overall with interval `[2.883083, 3.310818]`; bare CM/raw-AST is `0.822450` overall with interval `[0.789444, 0.855425]`. V3 used 24 rounds, exact schedule counterbalancing, 264 timing rows, 216 unique formulas, and 10,000 deterministic paired formula-cluster bootstrap resamples. These are local, workload-specific results and do not supersede B1’s CM/CSE-flat parity result. Immutable evidence: `deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_{raw,summary,inference,audit}.*`.

## Negative and reliability results

1. **Separate smoke processes are unsuitable for a 2–4% change.** Schedule/process variation overwhelmed the effect. Only alternating per-expression A/B data is used.
2. **Deep structural-key equality is a verifier trap.** The first ablation verifier compared independently built `CMNode.key` tuples. On high-sharing EPFL cones this follows unfolded occurrences and can become `t`-scale even when the IR DAG is small. No result file was written before cancellation. The tool now compares an exact ordered child-index DAG signature in O(`s`) time/space.
3. **Smoke timing is inconclusive.** Its all-corpus timing ratio was 0.992 with interval [0.944, 1.063]; it is useful for correctness/allocation only.
4. **No broad pass fusion.** The profile has several 6–26% subphases and diagnostic overhead; no single duplicate traversal demonstrated enough removable time.
5. **No native/JIT/SIMD change.** Flat bigint wins most admitted widths and the repository lacks Numba. A new dependency and compilation/copy boundary are not justified by this workload.
6. **No cache-policy change.** Existing all-hit synthetic warm passes do not establish a real admission/eviction policy or cross-process economics.
7. **No parallel/GPU/distributed reopening.** Current complete outputs and small kernels do not amortize startup, copying, synchronization, or memory amplification.

## Machine-readable evidence index

| Artifact | Purpose |
|---|---|
| `baseline_smoke_raw.csv`, `baseline_smoke_phases.csv`, `baseline_smoke_selector.csv` | Clean pre-change smoke, exact outputs, phase and selector data |
| `baseline_smoke_environment.json`, `baseline_smoke_source_snapshot/` | Starting branch/HEAD/status, environment, corpus/source hashes, listed run-defining sources |
| `baseline_smoke.prof`, `profiled_smoke_*` | cProfile and profiled smoke sidecars |
| `memo_ablation_smoke_*` | Allocation/correctness smoke using the pre-change source snapshot |
| `memo_ablation_bx1_b2_*` | 272-row representative paired timing |
| `memo_ablation_epfl_000_019_*` through `memo_ablation_epfl_120_128_*` | Bounded EPFL paired chunks and immutable listed-source snapshots |
| `memo_ablation_epfl_combined_summary.json` | 129-row circuit-clustered aggregate |
| `memo_ablation_repro_smoke_*` | Post-change explicit-arm reproducibility/allocation smoke |
| `post_memo_smoke_*` | Changed-tree smoke correctness and current-path data |

Raw historical accepted artifacts were not overwritten. Source snapshots beside
every run are authoritative for the files they list if later working-tree bytes
differ. Historical memo-ablation snapshots did not include every transitive
project import; the current writer expands the list for future runs.
