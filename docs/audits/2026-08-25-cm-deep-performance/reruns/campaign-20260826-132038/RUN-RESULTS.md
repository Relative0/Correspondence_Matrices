# Run Results

## Executive result

All authorized local gates passed. The retained implementation is exact and
green (`368 passed, 4 subtests passed`). The one-memo preparation change again
improved representative BX1/B2 and EPFL preparation by about 2.5%--2.7% with
zero exact mismatches. DP-R1 compact canonical-order labels were exact but much
slower and used more peak memory, so they were rejected and reverted.

The later explicitly approved external follow-up used three Runpod pods for a
total `$0.002815`, downloaded the commit-pinned Berkeley ABC i10 source and
license, and completed with zero active pods. No dependency was installed.

## Correctness and reliability

| Gate | Result |
|---|---|
| Initial full suite | `363 passed, 4 subtests passed` in 92.44 s |
| Final full suite after retained tooling | `365 passed, 4 subtests passed` in 85.51 s |
| Release full suite after website/package reconciliation | `365 passed, 4 subtests passed` in 97.08 s |
| Website/package focused integrity suite | `75 passed, 4 subtests passed` in 2.36 s |
| External-follow-up focused integrity suite | `86 passed, 4 subtests passed` in 3.27 s |
| Final full suite after external follow-up | `368 passed, 4 subtests passed` in 95.82 s |
| Aggregator unit tests | `2 passed` |
| Post-DP-R1 focused compiler/cache tests | `28 passed, 4 subtests passed` |
| Representative exact packed outputs | 401/401 equal |
| Above-guard bounded cases | 16/16 direct kernels exact; 16/16 wrappers refused; no timeout/OOM |

The DP-R1 source experiment was restored byte-for-byte: retained `cm_ir.py`
SHA-256 is `ff1633cc...57dcb7d7`, identical to its pre-experiment snapshot.

## Preparation profile

Representative medians, with each fraction relative to its corresponding CM
compile window:

| Corpus | Rows | Intern | Live vars | Lowering | Hash | Rewrite | Canonicalize |
|---|---:|---:|---:|---:|---:|---:|---:|
| BX1 | 80 | 23.2% | 11.3% | 13.4% | 12.1% | 7.6% | 5.5% |
| B2 | 192 | 22.0% | 12.7% | 11.9% | 10.9% | 9.0% | 6.3% |
| EPFL | 129 | 25.1% | 11.7% | 11.4% | 10.1% | 8.7% | 7.2% |

Median end-to-end current-call time was 328 us (BX1), 380 us (B2), and 770 us
(EPFL). The profile again points to several compiler constant factors rather
than one hidden scaling catastrophe.

## Symmetric V3 repeatability

Each run used 24 rounds, 264 rows, 216 formula clusters, exact packed equality,
and 10,000 formula-cluster bootstrap draws.

| Fresh run | Bare CM/CSE-flat overall | 95% formula CI | `k=16` | Public wrapper/CSE-flat |
|---|---:|---:|---:|---:|
| 1 | 0.908991 | [0.896660, 0.920466] | 0.977922 | 2.775383 |
| 2 | 0.908879 | [0.896082, 0.920992] | 0.973972 | 2.836843 |
| 3 | 0.904905 | [0.891868, 0.916944] | 0.978159 | 2.818942 |

Three-run geomean: `0.907590`; run range: `0.904905--0.908991`. These runs
agree with the prior Runpod range (`0.903--0.913`) but are above the accepted
single local V3 point (`0.890570`). Formula-cluster intervals are conditional
within one run and do not cover between-run/machine variation. Historical V3
is preserved rather than silently overwritten.

## One-memo preparation replication

Candidate is the retained one-memo sharing-aware builder; baseline explicitly
reconstructs the historical two-memo path.

| Slice | Rows | Repetitions | Candidate/baseline geomean | 95% clustered interval | Exact mismatches |
|---|---:|---:|---:|---:|---:|
| Smoke all | 25 | 11 | 0.973213 | [0.965356, 0.979776] | 0 |
| BX1+B2 representative | 272 | 11 | 0.973437 | [0.968471, 0.982526] | 0 |
| B2 | 192 | 11 | 0.969675 | [0.968970, 0.970381] | 0 |
| BX1 | 80 | 11 | 0.982526 | [0.966079, 0.988070] | 0 |
| EPFL representative | 129 | 5 | 0.974627 | [0.965820, 0.983220] | 0 |

Smoke traced-peak candidate/baseline geomean was `0.882005`. The fresh speed
effect is smaller than the earlier BX1+B2 point (`0.960113`) but remains useful,
directionally consistent, exact, and independently repeatable on this host.

`scripts/cm_combine_memo_ablation.py` now refuses overwrite, rejects duplicate
IDs or row-count mismatches, verifies typed exactness fields, and records every
input SHA-256 when combining bounded EPFL chunks.

## Backend selection

The current `k=16` policy on the representative reused corpus had low regret:

| Arm | Role | Rows | Regret geomean | Maximum | Catastrophic >=2 |
|---|---|---:|---:|---:|---:|
| Raw | tuning | 80 | 1.010683 | 1.599742 | 0 |
| Raw | reused validation | 307 eligible | 1.012205 | 1.657477 | 0 |
| CM | tuning | 80 | 1.009308 | 1.335591 | 0 |
| CM | reused validation | 321 | 1.012154 | 1.949342 | 0 |

The focused gap replay again rejected a universal support-only retune: the CM
validation slice had one catastrophic route (`2.284338` regret), so the overall
gate failed as designed. A new selector must be feature-based and validated on
a corpus frozen before outcome inspection.

## Cache and repeated evaluation

The flag named "persistent cache" is process-local. Descriptive medians show it
reduced CM no-reinflate whole-call time versus separate no-cache runs, but CM
still trailed BitSet by `3.13x--12.84x` on the cached run. With 50 cached
evaluations, CM execution-only still trailed BitSet by approximately `2.80x`
at `k=16`, `3.87x` at `k=12`, `8.91x` at `k=8`, and `11.18x` at `k=4`.

These are synthetic all-hit economics, not evidence for a durable cache or a
production working set. No byte-LRU or new production cache policy is justified.

## Related-expression families

The composition smoke and high-reuse family runs were exact. Cache reuse did
not establish a strongest-baseline win:

| Workload | `k` | Family size | Cached CM / BitSet |
|---|---:|---:|---:|
| composition mix | 8 | 10 | 22.42x |
| shared-block mix | 8 | 25 | 26.45x |
| shared-block mix | 12 | 25 | 12.06x |
| shared-block mix | 16 | 25 | 5.25x |

The process-local cache sometimes helped CM versus CM and sometimes added
overhead. This lane still needs a real edit/version trace.

## Partial-context break-even surface

The grid covered fixed fractions `0.25, 0.50, 0.75`, context counts
`25, 100, 500`, `n=8,12,16`, three trials, sliding-window locality, remaining-
variables output, and reuse of compiled IR. Cached CM was about `4.85x--7.37x`
faster than uncached CM but generally slower than direct BitSet recomputation.

At `n=16, c=500`, the medians approached the synthetic break-even:

| Fixed fraction | Remaining vars | BitSet total | Cached CM total | CM/BitSet |
|---:|---:|---:|---:|---:|
| 0.25 | 12 | 33.409 ms | 37.018 ms | 1.108 |
| 0.50 | 8 | 33.981 ms | 32.335 ms | 0.952 |
| 0.75 | 4 | 33.499 ms | 33.398 ms | 0.997 |

This is a useful hypothesis surface, not a production route: only three trials,
synthetic expressions/contexts, and no native CUDD restriction comparator.

## DP-R1 negative experiment

The exact rational-label ordering prototype preserved all 25 smoke DAGs and
packed outputs but made every row slower. Aggregate preparation was `1.8317x`
baseline and traced peak memory was `1.2440x`; EPFL was `2.1936x` slower. It was
rejected before representative expansion and reverted. See `DP-R1-REJECTION.md`.

## External follow-ups completed

- Native CUDD: `dd.cudd` unavailable; `dd.autoref` available.
- Numba/LLVM/SIMD JIT: Numba and llvmlite unavailable; no dependency installed.
- Runpod one-memo confirmation passed independently on `cpu3c`, `cpu3m`, and
  `cpu5c`: BX1+B2 ratios `0.972147--0.978781`; EPFL
  `0.969411--0.976902`; zero exact mismatches; total cost `$0.002815`; zero
  postflight pods.
- Berkeley ABC i10 produced 144 exact held-out cones, 16 per `k=8..16`. The
  current k16 rule had `1.012285` raw and `1.012460` CM regret with zero
  catastrophes. The preregistered feature selector failed with `1.121191` raw
  and `1.136482` CM regret and 7/11 catastrophes; rejected without retuning.
- See `EXTERNAL-RUNS-RESULTS.md` for exact per-host intervals, commands, hashes,
  cost, and held-out selection evidence.

## Exact command index

Commands and source/corpus hashes for the principal preparation/selector runs
are embedded in each `*_environment.json`. The remaining commands were:

```powershell
python -m pytest -q --basetemp <campaign>\.pytest_final

& .\.venv\Scripts\python.exe scripts\cm_above_guard_boundary.py `
  --timeout-seconds 45 --estimate-cap-bytes 67108864 `
  --rss-cap-bytes 536870912 --repetitions 3 `
  --output-prefix <campaign>\above_guard

& .\.venv\Scripts\python.exe cm_bench.py `
  --bench-partial-contexts --sizes 8,12,16 --trials 3 --max-depth 4 `
  --expr-style mixed_no_constants --partial-contexts <25|100|500> `
  --partial-fixed-var-fraction <0.25|0.5|0.75> `
  --partial-context-style sliding_window --partial-output-mode remaining-vars `
  --partial-reuse-compiled-ir --partial-report-live-vars `
  --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache `
  --robdd-dd-backend autoref --robdd-order-policy fixed --print-summary `
  --out-prefix <unique-prefix>

& .\.venv\Scripts\python.exe `
  deliverables_n22_24\cm_memo_runpod_campaign_2026_08_26.py --dry-run
```

Every output prefix was unique. Raw paired rows and failed/rejected evidence are
retained; historical accepted artifacts were not overwritten.

The master explainer was regenerated twice after incorporating the fresh V3
repeatability and above-guard evidence. All five generated files were
byte-stable across the two builds; two JSON files and four HTML files parsed;
the builder byte-compiled; shared JavaScript passed `node --check`; and no site
was deployed or published.
