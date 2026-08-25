# CM Deep Performance Benchmark Results

> **Correction, 2026-08-25:** Historical `held out` labels below mean reused
> selection-validation data, not untouched held-out data. Corrected fail-closed
> truth verification and the matched CSE-flat successor are documented in
> `deliverables_n22_24/corrections_2026_08_25/CM_BENCHMARK_AUDIT_CORRECTION_REPORT_2026-08-25.md`.

Audit date: 2026-08-24. Performance commands used the project virtual environment. Correctness tests used the existing global pytest installation because the virtual environment contains no pytest.

## Environment

| Field | Value |
|---|---|
| Repository revision | `main`, `6fe11d713cae39e56cd3251cca8e8ceb9cc5578f`, dirty tree preserved |
| OS | Windows 10.0.19045, AMD64 |
| CPU | AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD |
| Logical CPUs | 12 |
| Process affinity | Windows process/system masks `0xfff`; all 12 logical CPUs eligible; no pinning |
| Benchmark Python | `.venv\Scripts\python.exe`, CPython 3.13.5, MSC v.1943, 64 bit |
| Dependencies | NumPy 2.3.2, pandas 2.3.2, SymPy 1.14.0, `dd` 0.6.0; Numba absent |
| Thread environment | `MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS` unset |
| Test Python | global CPython 3.10.11, pytest 9.0.2 |
| Corpus identity | BX1 `1709ff...963b`; B2 `feadff...cf`; EPFL `bb98f1...06ac` (full hashes in environment JSON) |
| Seeds | BX1/B2 per-record seeds are in final raw CSV; EPFL uses immutable circuit hash/root IDs |

The final environment and source/corpus hashes are in `final_authoritative_environment.json`. The post-affinity-fix smoke sidecar records the Windows mask directly. No benchmark result combines machines.

## Commands

Baseline smoke before production edits:

```powershell
& .\.venv\Scripts\python.exe scripts\cm_performance_audit.py `
  --suite smoke --label deep-audit-baseline --warmups 3 --repetitions 11 `
  --output-prefix docs\audits\2026-08-24-cm-deep-performance\baseline_smoke
```

Final representative paired replay:

```powershell
& .\.venv\Scripts\python.exe scripts\cm_deep_performance_audit.py `
  --suite representative --corpora bx1,b2,epfl `
  --prep-repetitions 3 --kernel-rounds 5 `
  --max-kernel-temporary-bytes 8388608 `
  --output-prefix docs\audits\2026-08-24-cm-deep-performance\final_authoritative
```

Profile smoke:

```powershell
& .\.venv\Scripts\python.exe -m cProfile `
  -o docs\audits\2026-08-24-cm-deep-performance\current_pipeline_b2.prof `
  scripts\cm_deep_performance_audit.py --suite smoke --corpora b2 `
  --prep-repetitions 3 --kernel-rounds 3 `
  --output-prefix docs\audits\2026-08-24-cm-deep-performance\profiled_b2_smoke
```

Focused correctness:

```powershell
python -m pytest tests\test_cm_ir_cost.py tests\test_bitset_engine_policy.py -q
```

Full correctness, using a new audit-local temp root because sandbox policy denies pytest's default user-temp root:

```powershell
python -m pytest -q `
  --basetemp docs\audits\2026-08-24-cm-deep-performance\.pytest_tmp_full
```

The first unredirected full run is retained as an environment result: 325 passed and 20 setup errors, all caused by `PermissionError` while enumerating `C:\Users\brian\AppData\Local\Temp\pytest-of-brian`. It reported no assertion failures. The audit-local rerun is the completion gate.

## Timing definitions

- `compile_external_ns`: wall time around a cold `compile_expr_to_cm_ir` call with internal phase diagnostics enabled. Three samples, median.
- `hash_ns_median`: structural hash wall time, three samples.
- `ir_*_ns`: builder-internal instrumentation for canonicalization, rewrite, interning, live-variable work, and total compile.
- `lower_cm_ns_median`: `compile_flat(CMNode)` wall time, three samples.
- `raw_flat_ns_median` / `raw_words_ns_median`: prepared raw-expression kernels. Each pair is warmed once, run in size-dependent batches, and alternates order over five paired rounds; the reported value is median per call.
- `cm_flat_ns_median` / `cm_words_ns_median`: identical protocol for the CM-node kernels.
- `wrapper_current_ns_median`: no-reinflate wrapper on an already compiled CM node; includes admission, selection, evaluation, and packed result construction.
- `end_to_end_current_ns_median`: compile plus current wrapper.
- `node_count_cold/warm`: first full-DAG count after deleting only the derived `_node_count` field versus the immediately repeated lookup.
- Selector regret: selected kernel time divided by the faster eligible kernel for the same formula/arm. Catastrophic means regret `>=2.0`.
- Selector 95% intervals: deterministic 2,000-replicate cluster bootstrap of geomean regret, resampling `(corpus, circuit/operator-family)` clusters.

Correctness checks and digest construction are outside timed kernel windows. Every eligible raw/CM flat/words result is compared as the same packed integer artifact before a row is accepted.

## Baseline smoke

| Workload | Median wall time | Dispersion/notes |
|---|---:|---|
| compile AND width 64 | 21.905 ms | p10 20.705 ms; p90 24.476 ms; instrumented batch workload |
| mixed packed evaluation `n=8` | 0.364 ms | p10 0.316 ms; p90 0.459 ms |
| dense NumPy `n=8` | 3.609 ms | p10 3.079 ms; p90 4.569 ms |
| sparse ambient 32/live 5 | 0.305 ms | p10 0.283 ms; p90 0.326 ms |

All baseline signatures were exact. These smoke operations are diagnostic and are not used as before/after evidence for the selector.

## Preparation phases

Final representative medians:

| Corpus/phase | Median | p10 | p90 | Median fraction of cold compile |
|---|---:|---:|---:|---:|
| BX1 hash | 37.8 us | 11.9 us | 85.9 us | 11.7% |
| BX1 canonicalize | 14.4 us | 3.6 us | 42.0 us | 5.7% |
| BX1 rewrite | 23.7 us | 6.2 us | 59.0 us | 7.6% |
| BX1 intern | 70.4 us | 23.1 us | 151.9 us | 22.5% |
| BX1 live vars | 36.9 us | 7.6 us | 96.4 us | 10.8% |
| BX1 lower | 40.7 us | 16.5 us | 83.8 us | 13.2% |
| B2 hash | 42.3 us | 26.2 us | 76.1 us | 10.8% |
| B2 canonicalize | 24.1 us | 5.8 us | 57.5 us | 6.4% |
| B2 rewrite | 38.6 us | 17.6 us | 84.0 us | 8.7% |
| B2 intern | 93.8 us | 50.7 us | 165.4 us | 21.5% |
| B2 live vars | 52.9 us | 21.8 us | 111.3 us | 12.3% |
| B2 lower | 45.2 us | 26.3 us | 81.2 us | 10.9% |
| EPFL hash | 82.9 us | 30.7 us | 518.9 us | 9.6% |
| EPFL canonicalize | 52.6 us | 18.9 us | 403.7 us | 7.0% |
| EPFL rewrite | 65.9 us | 25.1 us | 466.9 us | 8.2% |
| EPFL intern | 194.0 us | 84.5 us | 1,188.2 us | 24.5% |
| EPFL live vars | 89.5 us | 26.5 us | 804.6 us | 11.5% |
| EPFL lower | 87.0 us | 34.8 us | 578.7 us | 11.0% |

Because fractions are per-row ratios and absolute columns are separate marginal quantiles, columns should not be algebraically recombined. Internal diagnostic instrumentation adds overhead and is used for attribution, not user-visible latency claims.

End-to-end medians were 385 microseconds on BX1, 472 microseconds on B2, and 926 microseconds on EPFL. Their p90 values were approximately 0.78, 0.85, and 4.92 milliseconds. Structural complexity, not merely `k`, drives the wide EPFL tail.

## Selector result

| Arm/role | Policy | n eligible | Geomean regret | Cluster-bootstrap 95% CI | Median | p90 | Max | `>=2x` |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| raw / BX1 tuning | old `k>=6` | 80 | 2.060 | [1.870, 2.158] | 1.669 | 4.945 | 7.607 | 39 |
| raw / BX1 tuning | current `k>=16` | 80 | 1.012 | [1.000, 1.041] | 1.000 | 1.000 | 1.737 | 0 |
| raw / B2+EPFL reused validation | old `k>=6` | 307 | 2.743 | [2.532, 3.012] | 3.601 | 5.801 | 11.001 | 200 |
| raw / B2+EPFL reused validation | current `k>=16` | 307 | 1.011 | [1.003, 1.019] | 1.000 | 1.000 | 1.609 | 0 |
| CM / BX1 tuning | old `k>=6` | 80 | 1.912 | [1.694, 2.027] | 1.532 | 4.545 | 6.391 | 38 |
| CM / BX1 tuning | current `k>=16` | 80 | 1.011 | [1.000, 1.029] | 1.000 | 1.000 | 1.273 | 0 |
| CM / B2+EPFL reused validation | old `k>=6` | 321 | 2.416 | [2.246, 2.617] | 3.108 | 4.827 | 7.055 | 200 |
| CM / B2+EPFL reused validation | current `k>=16` | 321 | 1.013 | [1.005, 1.022] | 1.000 | 1.000 | 1.961 | 0 |

Raw reused-validation eligibility excludes 10 source-protocol skips and 4 explicit 8 MiB temporary-budget refusals. These outcomes remain in the raw file. CM evaluation completed for all 401 rows.

The table is a same-run policy replay over paired raw times, so it avoids between-process drift. The selector itself is a single integer comparison and contributes no measurable model overhead.

## Node-count memoization

| Corpus | n | Median IR nodes | Cold count median | Warm count median | Geomean warm/cold |
|---|---:|---:|---:|---:|---:|
| BX1 | 80 | 13 | 6.35 us | 0.40 us | 0.064 |
| B2 | 192 | 20 | 7.40 us | 0.30 us | 0.048 |
| EPFL | 129 | 53 | 14.60 us | 0.30 us | 0.017 |

The no-reinflate budget calculation formerly requested the same count for full and reduced estimates. It now performs one cold traversal at most and subsequent calls are constant-time lookups. Wrapper-level results from separate processes were too schedule-sensitive for a precise microsecond claim, so only the directly measured operation and eliminated traversal are reported.

## Profile and allocation observations

The B2 smoke cProfile artifact contains only six sampled expressions and includes startup/import work. Its useful call-level signals are:

- CM compilation: 36 calls, about 36 ms cumulative; `_build_rec` about 29 ms.
- `make_xor`: about 16 ms cumulative.
- interning: 744 calls, about 9 ms cumulative.
- shared-associative UID handling: about 7 ms.
- live-variable set unions: about 6 ms.
- word evaluator: 1,666 calls, about 40 ms cumulative.
- raw flat evaluator: 1,432 calls, about 11 ms cumulative.
- CM flat evaluator: 1,462 calls, about 9 ms cumulative.

This agrees with paired measurements: word dispatch/scratch overhead is too large at narrow widths, while preparation cost is distributed across several builder activities. No allocation-heavy phase was isolated as a safe one-line production win.

The baseline audit's tracemalloc/RSS fields are stored in JSON. The final deep harness records exact packed output size and analytical word-environment/scratch estimates per row. At `k=16`, output is 8 KiB and the words environment is 128 KiB. Maximum estimated CM word scratch in this corpus was approximately 57 KiB (BX1), 72 KiB (B2), and 468 KiB (EPFL).

A separate B2 persistent-cache probe compiled 192 parsed expressions twice under tracemalloc. The cold pass recorded 1,368 misses, 1,253 within-pass subtree hits, 1,368 final entries, a 2.887 ms median, and 6.101 ms p90. The warm pass recorded 192 root hits and no misses, with 0.810 ms median, 1.244 ms p90, and warm/cold paired geomean 0.263. Traced retained memory over the post-parse baseline was 1.31 MiB after cold population and 1.43 MiB after the warm pass; peak was 1.66 MiB. The first 12 persistent roots were asserted equal to normal compile roots.

These cache times are allocation-instrumented and therefore not comparable to the uninstrumented compile table. They show a real warm benefit and bounded entry growth for this one pass, but they also reinforce the missing telemetry: entry count alone does not enforce a retained-byte budget, and an all-hit synthetic second pass is not a realistic service hit-rate estimate. Exact values are in `cache_probe_b2.json`.

## Reproducibility and interpretation limits

- The final raw CSV preserves formula IDs, roles, clusters, structural hashes, expected truth hashes, seeds when present, result hashes, operation counts, phase timings, kernel timings, memory estimates, refusals, batch sizes, and rounds.
- Whole-file corpus and implementation hashes are in the sidecar.
- No affinity pinning was applied. Very short kernels vary between complete replays; policy conclusions rely on large paired differences and reused-validation transfer, not marginal individual rows.
- BX1 has no direct `k=13..15` rows. `k=16` is a conservative measured endpoint, not proof of a universal hardware crossover.
- Cluster intervals quantify corpus clustering, not machine-to-machine uncertainty.
- No result is extrapolated beyond `k=16`.

## Test results

- Focused selector/CM-cost suite: **25 passed**.
- Full suite with default pytest temp: **325 passed, 20 setup errors**, all sandbox temp-root permission errors and no assertion failure.
- Full suite with audit-local `--basetemp`: **345 passed, 4 subtests passed in 114.05 seconds**.
