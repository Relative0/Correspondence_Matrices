# CM learning benchmark handoff contract

**Date:** 2026-09-04  
**Status:** cross-machine q64 evidence ingested; current gate abstains; no training or benchmark run.

## Purpose

The Benchmark task and learning task now have an explicit machine-readable
boundary. The Benchmark task may produce exact evidence independently; the learning
task accepts only a normalized `crse-learning-benchmark-handoff/v1` document and
recomputes its economics. It never calls the benchmark runner.

Passing this contract permits only consideration of a development learning
experiment. It does not itself train a model, open prospective data, enable routing,
or authorize production advice.

## Required handoff

The contract requires:

- a frozen task, source tree, case set, and exact-baseline closure;
- confirmation that all relevant task-identical exact arms and unfavorable/refused
  rows were retained;
- a source-blind development protocol frozen before labels;
- at least 16 fit, 8 validation, and 8 audit source groups;
- at least two backend labels with at least eight source groups per label;
- zero source-group overlap and zero prospective cases consumed;
- at least two independently verified runs on distinct physical machines;
- identical case-set and label-table hashes across both machines;
- zero schedule, semantic, and source/artifact mismatches;
- sum-based best-fixed and per-case-oracle totals, not a geometric-mean proxy;
- p95 feature/control, inference, exact-verification, and expected-fallback costs
  measured on each exact-timing host; and
- at least `1.10x` gross and fully charged speedup on every replication.

The handoff must explicitly permit development-training eligibility while keeping
prospective consumption and production routing prohibited. Economic totals and
speedups are recomputed; altered derived values are rejected.

## Current result after cross-machine completion

The completed GCC/AMD EPYC 9655 and Clang/AMD EPYC 9575F artifacts have now been
consumed without rerunning either benchmark. The adapter authenticates both raw-file
hashes against their independent verifications, requires all 6,912 q64 rows per host
to be exact and complete, takes the median of 16 repetitions for each case/arm, and
then computes the required sums across 54 cases.

| Host | Sum-based best fixed | Best-fixed sum | Oracle sum | Gross headroom | Total cost budget per case preserving 1.10x |
|---|---|---:|---:|---:|---:|
| GCC / EPYC 9655 | `native_fused_slots` | 141,549,155.0 ns | 127,998,459.5 ns | `1.105866083x` | 12,640.6 ns |
| Clang / EPYC 9575F | `native_fused_slots` | 127,877,156.0 ns | 114,731,375.5 ns | `1.114578775x` | 28,159.0 ns |

Thus the gross threshold survives on both hosts, but the limiting margin is only
`0.005866083x` above the `1.10x` gate. This sum-based result names
`native_fused_slots`; the previously reported `cse_flat_bigint` best fixed arm used a
different aggregate-median statistic and is not reused as the learning-economics
total.

The result is not training authorization. The normalized incomplete handoff is fed
through the ordinary gate and abstains because:

1. the benchmark cohort and split were not frozen as a source-blind learning
   protocol before these labels were known;
2. the two hosts disagree on one of 54 oracle labels (`native_fused_slots` versus
   `cse_flat_bigint` for `fresh-high-sharing-andor-k11-r0`);
3. p95 feature/control, inference, exact-verification, and expected-fallback costs
   have not been measured on both decision-bearing hosts;
4. fully charged headroom is consequently unknown; and
5. the verified Benchmark claim boundary explicitly forbids selector or neural
   claims.

The separate incremental-revision local gate is a negative architecture result: its
prototype lost to the existing persistent cache, remained slower than CSE-flat
through q64, and failed activation and retained-memory gates. It does not provide a
new learning decision surface or relax any blocker above.

Current output remains complete abstention with the unchanged exact fallback. No
prospective corpus was consumed and no model was trained.

## Next admissible evidence

Do not relabel the already-inspected cohort as source-blind training data. A new
development freeze is now complete at
`docs/recognition/runs/query-ladder-source-blind-learning-freeze-20260904-001`.
It contains 72 new deterministic cases with zero alpha-structural overlap against the
prior q64 cohort, 40/16/16 fit/validation/audit source groups, frozen query traces,
and 13 model-visible structural integer features. It contains zero exact timings,
labels, trained models, prospective cases, or cloud executions.

The label policy requires the same winning exact arm on every host, at least a 1.03x
median advantage over the runner-up, at least 75% paired-block wins, and a paired p10
ratio of at least 1.00x. Every disagreement or threshold failure becomes
`__abstain__`, remains in charged economics, and is excluded from model fitting.
This policy and the split were frozen before any label for the new cohort exists.

Each replication must time the exact source-blind feature/control path and the full
inference, verification, and expected-fallback vector on that same host. On the
current limiting GCC evidence, those four p95 costs have a combined ceiling of
12,640.6 ns/case merely to retain `1.10x`; a new run must recompute its own ceiling
rather than inherit this diagnostic. Its claim boundary must explicitly permit only
development experiment design. Production routing and prospective evaluation remain
separate, prohibited gates.

The freeze-file SHA-256 is
`3cf5c2672e01aae6130282f2ea1a65de32746597a59689605a2d913a675a0692`.
Independent verification status is `verified_source_blind_freeze_no_labels`; it
replayed the generator and cohort byte-for-byte, rechecked source closure and prior
identity exclusion, and confirmed zero exact executions, timings, labels, models,
prospective cases, and RunPod resources.

The next action belongs to the Benchmark task: prepare a separately authorized,
two-machine exact execution bound to this freeze and include the same-host charged
component measurements. This learning task must not reproduce that benchmark. A
future handoff can be checked against the exact pre-label freeze with:

```powershell
.\.venv\Scripts\python.exe scripts\cm_learning_benchmark_handoff.py `
  --handoff <verified-handoff.json> `
  --freeze docs\recognition\runs\query-ladder-source-blind-learning-freeze-20260904-001\FREEZE.json
```

## Implementation

- `cmbench/recognition/learning_benchmark_handoff.py`
- `cmbench/recognition/query_ladder_learning_evidence.py`
- `cmbench/recognition/query_ladder_learning_freeze.py`
- `cmbench/recognition/query_ladder_development_experiment.py`
- `scripts/cm_learning_benchmark_handoff.py`
- `scripts/cm_query_ladder_learning_freeze.py`
- `scripts/cm_query_ladder_development_experiment.py`
- `scripts/crse_query_ladder_learning_freeze_verify.py`
- `tests/test_learning_benchmark_handoff.py`
- `tests/test_query_ladder_learning_evidence.py`
- `tests/test_query_ladder_learning_freeze.py`
- `tests/test_query_ladder_development_experiment.py`

Current readiness can be checked without running benchmarks:

```powershell
.\.venv\Scripts\python.exe scripts\cm_learning_benchmark_handoff.py
```

Exit code `2` means fail-closed abstention. A later in-project handoff can be
checked with `--handoff <path>`; malformed, incomplete, drifted, economically
insufficient, or over-broad handoffs also abstain.

After, and only after, a freeze-bound handoff becomes eligible, candidate predictions
are evaluated under the separately documented chance, majority, frozen analytical
control, split-isolation, coverage, and three-seed neural-repeatability gates in
`CM_QUERY_LADDER_DEVELOPMENT_LEARNING_EVALUATION_2026_09_04.md`. Passing those gates
still establishes development evidence only and does not permit prospective access
or production routing.
