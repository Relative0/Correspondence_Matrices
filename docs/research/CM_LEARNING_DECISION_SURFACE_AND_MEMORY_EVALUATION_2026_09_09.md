# CM learning decision-surface and memory-evaluation boundary

Date: 2026-09-09
Status: development infrastructure implemented; no benchmark, model fit, training,
prospective-data access, routing change, or production action

## Decision

The September 8 exact-CM results justify stronger learning eligibility checks and a
memory-aware development evaluator. They do not reopen model fitting on any retained
cohort. The existing q64 learning handoff now requires a v2 decision-surface record
before its fitter can run. The new memory evaluator accepts only separately supplied,
source-blind, split-isolated, independently verified measurements and remains
development-only even when all checks pass.

Legacy `crse-learning-benchmark-handoff/v1` documents remain readable so current and
historical evidence can still be assessed. They fail closed with
`decision_surface_evidence_missing`; only
`crse-learning-benchmark-handoff/v2` can reach development fitting.

## Latency decision-surface gate

A v2 exact-benchmark handoff adds an independently verified decision-surface summary
bound to the same label table. It records the frozen label-policy hash, stable and
material winner counts by split, cross-host disagreements, threshold abstentions,
coverage, and the set of arms that actually win material cases.

Development fitting remains ineligible unless:

- the surface and its independent replay are complete;
- at least two task-identical exact arms win material cases;
- non-abstain coverage is at least 80% overall and separately in fit, validation, and
  audit;
- winner counts, abstentions, labels, split counts, and digests close exactly;
- the label policy is the one frozen before timings; and
- all earlier source-blind, cross-machine, exactness, label-support, and fully charged
  economic gates also pass.

This closes the gap exposed by the September work: merely listing two or more
available implementations is not a learning surface when one arm always wins, the
alternatives are within measurement resolution, or most cases must abstain.

### Raw q64 reconstruction boundary

`cmbench/recognition/query_ladder_decision_surface.py` now reconstructs that v2
summary from the decision-bearing evidence rather than trusting pre-aggregated
winner counts. Its input is a normalized package containing every one of the 16
q64 block timings for every frozen case, exact arm, and physical host, plus the
complete same-host p95 charged-cost vector.

The verifier binds the package to the frozen task, case, label-policy, and source
identities; requires two distinct physical machines and two distinct independent
verification records; and rejects missing arms, missing blocks, non-finite or
non-positive timings, schedule drift, semantic mismatch, and source/artifact drift.
For each host and case it recomputes the arm medians, median runner-up advantage,
paired-block win fraction, and paired p10 speedup. P10 replays the frozen pre-timing
implementation exactly: sort the 16 paired ratios and select index
`floor(0.10 × (n−1))`, with no interpolation. The frozen `1.03x`, `75%`, and `1.00x`
threshold comparisons are inclusive. A threshold failure, host abstention, or
cross-host winner disagreement becomes `__abstain__`.

Only after those raw calculations close does it recompute the label-table digest,
best-fixed and oracle sums, gross speedup, and fully charged speedup, construct a v2
handoff in memory, and pass that handoff through the separate learning-handoff
validator. It never writes a handoff, runs an exact backend, or fits a model.

## Memory-aware development evaluator

`cmbench/recognition/memory_learning_evidence.py` defines two read-only contracts.

The measurement contract requires two distinct physical hosts and independent
verification records, at least two exact arms, unique source groups assigned to the
frozen fit/validation/audit splits, a byte-resolution floor, a relative materiality
floor, exact-output verification, retained unfavorable/refused rows, and zero early
prospective consumption. It derives a label only when every host has the same
materially separated minimum-memory arm. Ties, insufficient separation, or host
disagreement become `__abstain__`.

Before a memory development experiment is eligible, the surface must meet the same
16/8/8 split minimums and eight-source-group-per-label floor used by the learning
protocol, have at least two materially winning arms, retain at least 80% usable labels
overall and per split, and contain every learned label in validation and audit.

The prediction contract evaluates validation and audit separately. It measures:

- material underprediction prevalence, capped at 20%;
- median overprediction factor, capped at 2.0;
- ordering agreement on materially separated arm pairs, at least 70%;
- selections within one measurement-resolution floor of the measured minimum, at
  least 80%;
- candidate non-abstain coverage, at least 80%; and
- whether every cross-host-unstable label was explicitly abstained.

All prediction rows are bound to the measurement digest. Validation and audit target
visibility, changed rows, a selected arm that is not the predicted minimum, incomplete
arms, or prospective consumption fail closed. Passing establishes only a development
signal; advice and production routing remain disabled and the exact fallback remains
unchanged.

The single-candidate path admits analytical, bounded-tree, and linear candidates. A
neural prediction is rejected from that path even if its metrics pass. Neural memory
evidence must instead use the replicated-seed wrapper and a separately supplied
protocol that declares one candidate-family and candidate-specification hash, an
independent verification hash, and a sorted schedule of at least three distinct seeds.
The protocol must declare that the specification was frozen before training, only the
fit split was used for training, validation and audit targets were hidden from fitting,
the candidate was locked before audit, all declared seeds are required, and no
prospective cases were consumed.

Every scheduled seed must provide a complete prediction table bound to that exact
protocol. The wrapper assesses validation and audit independently for every seed and
reports the worst safety, calibration, ordering, selection, regret, and coverage value
across seeds. One failed, missing, duplicate, extra, malformed, or protocol-mismatched
seed rejects the replicated signal. Seed input order cannot change the assessment.
This is evaluation infrastructure only: it neither trains the declared models nor
establishes that a real neural memory signal exists.

## Relationship to the H6 result

The H6 fresh-process calibration remains valid evidence that an OS-level memory signal
can be measured. Its stopped estimator result remains negative routing evidence: the
candidate ordered zero of three materially separated holdout pairs correctly. Those
exposed calibration and holdout cases are not imported into this evaluator and are not
relabelled as source-blind data.

The historical H6 freeze also exposed a checkout-portability issue in its original
strict replay: its source closure hashes raw bytes, while this Windows checkout has a
mixture of LF and CRLF materializations. The strict validator and frozen artifact
remain untouched. A separate read-only audit now verifies the frozen document and
source-closure digests, parent freeze and oracle canonical bindings, all 708 schedule
identities, exact binary bytes, and text files under LF/CRLF normalization. It reports
zero semantic or binary mismatches on the current checkout. This diagnoses the replay
difference; it does not weaken or replace the strict H6 validator and does not reopen
the stopped H6 estimator result.

The `multiply-low-cone` failure is represented only as a synthetic regression pattern:
a confident estimator that reverses the memory ordering must fail the pairwise-order,
underprediction, and near-minimum-selection checks. It is a software guardrail, not a
new empirical result. Any evidence-bearing memory learner still requires a newly
frozen independent cohort.

## Read-only use

```powershell
.\.venv\Scripts\python.exe scripts\cm_query_ladder_decision_surface.py `
  --evidence <verified-complete-q64-block-timings.json> `
  --freeze docs\recognition\runs\query-ladder-source-blind-learning-freeze-20260904-001\FREEZE.json

.\.venv\Scripts\python.exe scripts\cm_query_ladder_decision_surface.py `
  --evidence <verified-complete-q64-block-timings.json> `
  --freeze docs\recognition\runs\query-ladder-source-blind-learning-freeze-20260904-001\FREEZE.json `
  --emit-handoff

.\.venv\Scripts\python.exe scripts\cm_memory_learning_evidence.py `
  --measurements <verified-memory-measurements.json>

.\.venv\Scripts\python.exe scripts\cm_memory_learning_evidence.py `
  --measurements <verified-memory-measurements.json> `
  --predictions <development-predictions.json>

.\.venv\Scripts\python.exe scripts\cm_memory_learning_evidence.py `
  --measurements <verified-memory-measurements.json> `
  --neural-protocol <frozen-neural-memory-protocol.json> `
  --neural-predictions <seed-11.json> <seed-23.json> <seed-47.json>
```

Exit code `0` means the applicable development-only checks passed. Exit code `2`
means fail-closed abstention or rejection. The q64 command prints either its raw
surface assessment or the reconstructed handoff and independent readiness result to
standard output. Neither command fits a model, executes an exact backend, or writes
an artifact.

The H6 portability diagnosis is likewise read-only:

```powershell
.\.venv\Scripts\python.exe scripts\crse_audit_h6_freeze_portability.py
```

## Remaining exact-CM dependency

No retained exact-CM result currently supplies an admissible learning dataset. The next
evidence-bearing step still belongs to a separately authorized exact Benchmark task:

1. execute the already frozen 72-case q64 surface on two distinct hosts;
2. retain every arm, block, failure, tie, and refusal;
3. independently verify task identity and exact outputs;
4. derive the joint label table using the pre-timing frozen label policy;
5. supply the complete raw blocks to the independent decision-surface verifier and
   replay its reconstructed v2 handoff; and
6. measure the complete same-host p95 feature/control, inference, exact-verification,
   and fallback cost vector.

Only a handoff that passes all of those checks and retains at least 1.10x fully charged
headroom on both hosts may invoke the existing identity-free development fitter.
Analytical, bounded-tree, and linear controls remain ahead of any neural candidate.

## Implementation and tests

- `cmbench/recognition/learning_benchmark_handoff.py`
- `cmbench/recognition/query_ladder_decision_surface.py`
- `cmbench/recognition/memory_learning_evidence.py`
- `cmbench/comparative/h6_freeze_portability.py`
- `scripts/cm_query_ladder_decision_surface.py`
- `scripts/cm_memory_learning_evidence.py`
- `scripts/crse_audit_h6_freeze_portability.py`
- `tests/test_learning_benchmark_handoff.py`
- `tests/test_query_ladder_development_experiment.py`
- `tests/test_query_ladder_decision_surface.py`
- `tests/test_memory_learning_evidence.py`
- `tests/test_h6_freeze_portability.py`

The q64 and memory tests use constructed timing, measurement, and prediction tables
only. The H6 audit test reads the existing freeze and its bound files. No test invokes
a benchmark runner or trains a model.
