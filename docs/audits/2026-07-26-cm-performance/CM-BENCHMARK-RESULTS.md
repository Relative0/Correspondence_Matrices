# CM Benchmark Results

Date: 2026-07-26

## Result policy

Only controlled measurements are called improvements:

- identical interpreter, hardware, workload, warmup count, repetition count,
  instrumentation, and benchmark script;
- exact result signatures or truth arrays on every repetition;
- median and dispersion reported;
- effect larger than ordinary observed noise;
- claim limited to the code path actually changed.

The compile optimization satisfies that policy. Other measurements characterize
the final system and do not imply that the compile change caused them.

## Environment

| Item | Value |
|---|---|
| Machine | HP EliteBook 845 G8 |
| CPU | AMD Ryzen 5 PRO 5650U, 6 cores / 12 logical processors |
| RAM | 33,622,650,880 bytes (31.31 GiB) |
| OS | Windows 10 Pro 10.0.19045 |
| Power plan | Balanced |
| Git branch / `HEAD` | `main` / `6419b21909b7994cdec0aae04a3c1eaba357bc75` |
| Benchmark Python | `.venv` Python 3.13.5, 64-bit |
| Benchmark NumPy | 2.3.2 |
| Benchmark pandas | 2.3.2 |
| Benchmark SymPy | 1.14.0 |
| Benchmark `dd` | 0.6.0 (`dd.autoref`; native CUDD unavailable) |
| Test Python | system Python 3.10.11 |
| Test NumPy / pytest | 2.2.6 / 9.0.2 |
| Thread environment | `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, and `NUMEXPR_NUM_THREADS` unset |
| Affinity | not pinned |
| GPU / remote worker | not used |

The worktree was already dirty. Every JSON result records `git status --short`,
source hashes, interpreter, platform, dependency version, command, and timestamp.

## Reproduction commands

Run from the repository root in PowerShell.

### Install

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### Fast benchmark smoke

```powershell
.\.venv\Scripts\python.exe scripts\cm_performance_audit.py `
  --suite smoke `
  --label smoke `
  --warmups 2 `
  --repetitions 5 `
  --output-prefix docs\audits\2026-07-26-cm-performance\reproduction_smoke
```

### Representative local benchmark

```powershell
.\.venv\Scripts\python.exe scripts\cm_performance_audit.py `
  --suite local `
  --label local `
  --warmups 3 `
  --repetitions 11 `
  --output-prefix docs\audits\2026-07-26-cm-performance\reproduction_local
```

### Larger opt-in benchmark

```powershell
.\.venv\Scripts\python.exe scripts\cm_performance_audit.py `
  --suite large `
  --label large `
  --warmups 3 `
  --repetitions 5 `
  --output-prefix docs\audits\2026-07-26-cm-performance\reproduction_large
```

### Actual controlled compile A/B commands

Before the complement lookup change:

```powershell
.\.venv\Scripts\python.exe scripts\cm_performance_audit.py `
  --suite local `
  --label before-linear-complement-scan `
  --warmups 3 `
  --repetitions 11 `
  --output-prefix docs\audits\2026-07-26-cm-performance\before
```

After the complement lookup change:

```powershell
.\.venv\Scripts\python.exe scripts\cm_performance_audit.py `
  --suite local `
  --label after-constant-time-complement-lookup `
  --warmups 3 `
  --repetitions 11 `
  --output-prefix docs\audits\2026-07-26-cm-performance\after
```

Both files record benchmark script SHA-256
`019470b64ae3028e124398bac141ed283eec5faf02dfd65d03843e3882630235`.

### Whole-pipeline profile

```powershell
.\.venv\Scripts\python.exe -m cProfile `
  -o docs\audits\2026-07-26-cm-performance\baseline_pipeline.prof `
  cm_bench.py `
  --sizes 8,12,16 `
  --trials 5 `
  --max-depth 5 `
  --expr-style balanced_all_vars `
  --require-nontrivial-expr `
  --min-used-var-fraction 1.0 `
  --cm-compare-no-reinflate `
  --cm-compile-once-per-expression `
  --cm-eval-repeat 5 `
  --cm-words-eval `
  --cm-hybrid-threshold 16 `
  --no-sympy --no-robdd --no-dd --no-espresso --no-bdd-sop --no-numba `
  --no-bitset `
  --out-prefix docs/audits/2026-07-26-cm-performance/baseline_pipeline
```

`--cm-compare-no-reinflate` intentionally re-enables the matched raw-AST bitset
control through preset logic even though `--no-bitset` appears later in the
command.

### Tests

```powershell
python -m pytest -q
```

Final result: `209 passed in 67.80s`.

## Dataset and case definitions

All new cases are deterministic and constructed inside the worker process.

| Family | Definition | Purpose |
|---|---|---|
| `compile_and_wN` | balanced binary AST of `N` unique variables, canonicalized to one wide AND | complement-scan and wide-key scaling |
| `compile_or_wN` | balanced binary AST of `N` unique variables, canonicalized to one wide OR | same for OR |
| `eval_mixed_nN` | all-live balanced tree cycling AND/OR/XOR/IMP/EQV with deterministic NOTs | packed explicit evaluation across output sizes |
| `dense_numpy_nN` | same mixed tree through dense NumPy materialization | dense output scaling |
| `sparse_ambient32_live5` | five-live-variable XOR in a 32-variable ambient basis, guarded reduced output | ambient dimension versus true output support |

The compile A/B covers widths 32, 64, 128, 256, and 512. The final opt-in
suite extends compile to 2,048 operands, packed output to `n=20`, and dense
output to `n=18`.

These are controlled structural workloads, not real-domain datasets. No
validated real-world dataset currently exists in the repository.

## Methodology

Each case runs in a fresh subprocess so peak working set and cache state do not
leak from another case. The worker:

1. constructs the deterministic expression and independent reference;
2. performs the requested warmups;
3. forces a Python GC before the measured series;
4. records wall and process CPU time;
5. records GC collections and tracemalloc peak;
6. validates the result;
7. repeats and checks a stable result signature;
8. reports median, MAD, linearly interpolated p10/p90, and throughput.

Final-state short operations are batched so Windows process CPU time exceeds its
scheduling quantum. Reported wall/CPU values are divided by batch size. Compile
A/B is unbatched but identical on both sides.

Peak working-set delta is the worker process's maximum working set after the
warmup baseline. It is page-granular and may include allocator first-touch.
Tracemalloc is better for comparative Python/NumPy allocation behavior, but it
is not a complete native-memory census.

## Controlled compile before/after

### AND

| Width | Before median | Before MAD | After median | After MAD | Speedup | Peak allocation ratio before/after |
|---:|---:|---:|---:|---:|---:|---:|
| 32 | 4.418 ms | 0.623 ms | 3.804 ms | 1.076 ms | 1.16× | 1.00 |
| 64 | 10.115 ms | 1.518 ms | 6.631 ms | 0.557 ms | 1.53× | 1.00 |
| 128 | 22.063 ms | 0.794 ms | 14.105 ms | 0.550 ms | 1.56× | 1.00 |
| 256 | 58.606 ms | 4.454 ms | 31.033 ms | 0.434 ms | 1.89× | 1.00 |
| 512 | 145.749 ms | 1.829 ms | 64.893 ms | 2.250 ms | 2.25× | 1.00 |

### OR

| Width | Before median | Before MAD | After median | After MAD | Speedup | Peak allocation ratio before/after |
|---:|---:|---:|---:|---:|---:|---:|
| 32 | 4.611 ms | 0.604 ms | 2.837 ms | 0.104 ms | 1.63× | 1.00 |
| 64 | 9.363 ms | 1.030 ms | 7.337 ms | 0.866 ms | 1.28× | 1.00 |
| 128 | 16.570 ms | 0.381 ms | 14.400 ms | 0.259 ms | 1.15× | 1.00 |
| 256 | 40.544 ms | 1.298 ms | 30.406 ms | 0.669 ms | 1.33× | 1.00 |
| 512 | 112.321 ms | 8.830 ms | 55.248 ms | 3.163 ms | 2.03× | 1.00 |

Every before/after structural SHA-256 signature matched. Allocation volume was
effectively unchanged, as expected: the optimization removes comparisons, not
the canonical IR objects.

The effect exceeds dispersion most clearly from width 128 upward. The 32- and
64-operand rows are retained for scaling but should not be used as universal
small-expression claims.

## Line/call-stack profile

Five uninstrumented 512-term AND compiles:

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Total cProfile time | 1.389 s | 0.280 s | 4.96× faster |
| Function calls | 3,011,731 | 418,451 | 7.20× fewer |
| `make_and` cumulative | 1.351 s | 0.244 s | 5.54× faster |
| `_is_negation_of` calls | 1,296,640 | no wide scan | removed |
| `any` cumulative | 1.068 s | no wide scan | removed |

The raw unprofiled median for one 512-term AND compile changed from 72.464 ms
to 16.235 ms (4.46×) in the same focused probe. This focused probe excludes
tracemalloc and subprocess orchestration, so its absolute time differs from the
JSON benchmark.

## Whole-pipeline results

The profile made 1,953,266 calls and took 4.860 s:

| Cumulative path | Time | Share of process time |
|---|---:|---:|
| import machinery | 3.712 s | 76% |
| `detect_backends` | 1.501 s | 31% (overlaps imports) |
| `run_bench` | 1.210 s | 25% |
| pandas aggregation | 0.718 s | 15% |

Selected median result rows:

| `n` | Dense CM | No-reinflate total | Cached no-reinflate per eval | Matched raw control per eval | Exact CM checks |
|---:|---:|---:|---:|---:|---|
| 8 | 2.349 ms | 2.572 ms | 93.16 µs | 82.32 µs | pass |
| 12 | 2.359 ms | 2.504 ms | 95.40 µs | 81.36 µs | pass |
| 16 | 3.742 ms | 2.916 ms | 139.30 µs | 126.56 µs | pass |

The absolute pipeline values include profiler overhead and should not be mixed
with the isolated unprofiled results. Their purpose is cost attribution.

## Cold versus warm cache behavior

This run used `--warmups 0 --repetitions 7`. The first observation is compared
with the median of observations 2–7:

| Case | First | Warm median | First/warm |
|---|---:|---:|---:|
| compile AND width 64 | 6.708 ms | 6.955 ms | 0.96× |
| packed mixed `n=8` | 22.359 ms | 0.130 ms | 171.86× |
| dense NumPy `n=8` | 1.908 ms | 0.817 ms | 2.33× |
| ambient 32/live 5 reduced | 15.253 ms | 0.141 ms | 108.14× |

First-touch mask/environment construction dominates packed latency. Compile is
not helped because each measured operation builds a fresh IR. Cache-aware
benchmarks must state whether they measure first request, first expression,
warm repeated evaluation, or cross-expression reuse.

## Final packed and dense scaling

Sustained timing and CPU use come from `final_batched_large_*`. One-operation
allocation and RSS values come from the companion unbatched
`final_large_*` run so batching does not inflate retained allocator peaks.

### Packed exact output

| Case | Output elements | Wall median | MAD | CPU median | Throughput | Traced peak | Peak RSS delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| mixed `n=4` | 16 | 35.67 µs | 1.49 µs | 31.25 µs | 28,035/s | 4.1 KiB | 0.11 MiB |
| mixed `n=8` | 256 | 67.84 µs | 1.60 µs | 62.50 µs | 14,741/s | 4.7 KiB | 0.11 MiB |
| mixed `n=12` | 4,096 | 89.84 µs | 2.85 µs | 93.75 µs | 11,131/s | 6.7 KiB | 0.11 MiB |
| mixed `n=16` | 65,536 | 144.67 µs | 2.41 µs | 140.63 µs | 6,913/s | 30.7 KiB | 1.57 MiB |
| mixed `n=18` | 262,144 | 211.89 µs | 8.24 µs | 218.75 µs | 4,720/s | 106.1 KiB | 6.80 MiB |
| mixed `n=20` | 1,048,576 | 511.71 µs | 25.45 µs | 500.00 µs | 1,954/s | 407.1 KiB | 29.64 MiB |
| ambient 32/live 5 | 32 | 80.20 µs | 1.34 µs | 78.13 µs | 12,469/s | 5.6 KiB | 0.11 MiB |

The ambient-32 case demonstrates that guarded reduced execution scales with
actual output support, not nominal variable count. It does not prove complete
32-live-variable feasibility.

### Dense NumPy output

| Case | Output elements | Wall median | MAD | CPU median | Throughput | One-operation traced peak | One-operation peak RSS delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| dense `n=8` | 256 | 0.756 ms | 0.039 ms | 0.781 ms | 1,322/s | 27.2 KiB | 0.20 MiB |
| dense `n=12` | 4,096 | 1.271 ms | 0.131 ms | 1.250 ms | 787/s | 61.2 KiB | 0.15 MiB |
| dense `n=16` | 65,536 | 1.566 ms | 0.149 ms | 1.563 ms | 638/s | 365.6 KiB | 0.92 MiB |
| dense `n=18` | 262,144 | 2.932 ms | 0.062 ms | 2.813 ms | 341/s | 1.49 MiB | 5.69 MiB |

### Wide compile final-state scaling

| Case | Wall median | CPU median | Traced peak | Peak RSS delta |
|---|---:|---:|---:|---:|
| AND width 512 | 51.244 ms | 52.083 ms | 0.83 MiB | 1.31 MiB |
| AND width 1,024 | 116.743 ms | 125.000 ms | 1.61 MiB | 2.94 MiB |
| AND width 2,048 | 263.040 ms | 250.000 ms | 3.39 MiB | 6.62 MiB |
| OR width 2,048 | 269.025 ms | 250.000 ms | 3.39 MiB | 7.03 MiB |

CPU time remains quantized on Windows, even after batching, so close wall/CPU
differences should not be overinterpreted.

## Concurrency correctness

Before thread isolation, one shared CM node/program and 12 synchronized words
evaluations produced 12 mismatches in the first round. An independent two-thread
probe over 25 rounds found corruption even for identical bindings.

After thread isolation:

```text
mismatches 0 calls 600
```

Both raw-AST and CM-node regression paths pass under an 8-thread barrier. This
is a correctness result, not a throughput speedup. Scratch memory now scales
with active evaluation threads.

## Numerical deviation

All benchmark cases report:

- `correct: true`;
- maximum Boolean mismatch count: `0`;
- stable SHA-256 result signature across repetitions.

No floating-point output exists, so tolerance is exactly zero. Timing ratios and
summary statistics use floating-point only as measurement metadata.

## Known limitations

- Synthetic structural cases are not a substitute for real EDA, policy, or
  compiler workloads.
- The machine was on the Balanced power plan without fixed affinity.
- No independent machine replication was run.
- Native CUDD, GPU, WSL, Docker, and RunPod were unavailable or intentionally
  not used.
- Initial before/after RSS values are null due to a Windows handle declaration
  bug in the first version of the audit tool. Tracemalloc before/after is valid;
  final RSS was rerun after correction.
- cProfile changes absolute timings and is used for attribution, not headline
  latency.
- Windows process CPU time is quantized; batching reduces but does not eliminate
  that limitation.
- The V4 corpus repeats expressions across ambient bindings and is unsuitable
  for treating every record as an independent formula.
- `cm_bench.py` still lacks the full metadata and dispersion model supplied by
  the isolated audit tool.
- No performance threshold was added to ordinary pytest because heterogeneous
  hardware would make it unstable.

## Machine-readable files

| File | Role |
|---|---|
| `before_raw.jsonl` / `before_summary.json` | controlled pre-optimization raw samples and summary |
| `after_raw.jsonl` / `after_summary.json` | same-script post-optimization comparison |
| `final_batched_large_raw.jsonl` / `final_batched_large_summary.json` | final sustained wall/CPU scaling |
| `final_large_raw.jsonl` / `final_large_summary.json` | final one-operation allocation/RSS scaling |
| `final_cold_warm_raw.jsonl` / `final_cold_warm_summary.json` | first-touch and subsequent observations |
| `baseline_pipeline_raw.csv` / `baseline_pipeline_summary.csv` | whole-pipeline generated rows |
| `baseline_pipeline.prof` | whole-pipeline cProfile |
| `baseline_wide_compile.prof` / `after_wide_compile.prof` | focused core profiles |
| `benchmark-manifest.json` | hashes, commands, and artifact selection |
