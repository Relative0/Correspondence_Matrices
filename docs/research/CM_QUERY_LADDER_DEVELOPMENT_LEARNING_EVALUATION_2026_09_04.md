# CM query-ladder development learning evaluation

**Date:** 2026-09-04
**Status:** evaluation and fit guards implemented; no labels consumed, model fit,
neural training, prospective access, exact benchmark execution, or routing change.

## Decision

There is now an executable post-benchmark learning boundary for the frozen q64
architecture-query surface. It does not relax the current stop decision. Until a
future handoff is independently verified, bound to the pre-label freeze, and remains
at least `1.10x` faster after every charged routing cost on both physical machines,
the fitter is never called and the exact fallback is unchanged.

If that exact gate eventually passes, learned predictions still receive no credit
for being merely better than a coin toss. Validation and audit are evaluated
separately against the class-balanced chance rate, the empirical majority-class
accuracy, and the frozen ultra-cheap analytical control. A learned result must pass
every criterion on both splits.

This assessment can establish only a development signal. It cannot authorize
prospective evaluation, advice, model promotion, or production routing.

## Authenticated inputs

The signal evaluator accepts four documents:

1. the independently replayed 72-case source-blind freeze;
2. a verified two-machine benchmark handoff accepted by the existing charged
   economics gate;
3. a labeled development table containing exactly the frozen cases, source groups,
   splits, and 13 model features; and
4. a complete candidate prediction table bound to the same freeze and label table.

The economic evaluator additionally accepts independently verified routing evidence
containing every per-case exact-arm median and the candidate's same-host p95
inference and fallback-dispatch costs for each physical-machine replication.

The labeled table has a replayed record digest and must agree with the handoff's
case-set, label-table, and per-label counts. Changed or missing rows, source-group
identity drift, split changes, feature changes, illegal labels, prospective cases,
or a mismatched digest fail closed.

The prediction table may name only one of the eight frozen exact arms or
`__abstain__`. It must cover all 72 cases exactly once. It declares that fitting saw
only `development_fit`, and that validation/audit labels were not visible to the
fitter. Prediction-table tampering, illegal arms, missing cases, label-table drift,
or claimed label visibility fails closed.

## Fit isolation

The guarded fit entry point first replays the exact handoff and dataset validators.
Only then can it call a supplied fitter. The fitter receives only:

- the 13-value frozen structural feature tuple; and
- the joint cross-host exact-arm label.

It receives only non-abstaining `development_fit` rows. Case IDs, source-group
hashes, family/shape metadata, split names, expressions, query traces, timings,
machine/compiler identities, and validation/audit labels are not passed. If the
handoff or dataset is ineligible, the callback is not invoked.

The entry point is future infrastructure. It has not been invoked on benchmark
labels because no eligible handoff or labeled version of the source-blind freeze
exists yet.

## Precommitted signal tests

Every non-abstaining class present anywhere in the development label table must be
represented in both validation and audit. Candidate abstention counts as an
incorrect prediction for classification and lowers coverage. Each split must meet:

| Test | Required value |
|---|---:|
| Balanced accuracy | at least `max(0.65, balanced chance + 0.15)` |
| Accuracy above majority-class control | at least `+0.10` |
| Balanced accuracy above frozen analytical control | at least `+0.03` |
| Candidate non-abstain coverage | at least `0.80` |

Balanced chance is `1 / number_of_non_abstaining_labels`; it is not hard-coded to
`0.50`. The majority control is recomputed per split. The analytical control is the
pre-label frozen `shared_node_count_positive_then_cse_else_native/v1` rule. This
prevents a skewed label table, a constant majority predictor, or aggressive
abstention from being reported as meaningful learning.

These statistical gates supplement rather than replace exact economics. A passing
classifier can still be economically useless.

## Candidate routed economics

The implemented economic evaluator first requires the prediction signal to pass.
It then authenticates one routing record for every handoff replication, requires
the same physical-machine and independent-verification identities, and recomputes
the best-fixed and oracle sums from all 72 by 8 exact-arm medians. A missing arm or
case, changed timing, cross-host reuse, incomplete p95 timing, verification mismatch,
or disagreement with the handoff totals fails closed.

For every host it recomputes:

`candidate exact-arm sum + 72 * (feature/control p95 + candidate inference p95 + exact verification p95) + candidate abstentions * fallback-dispatch p95`.

The selected exact-arm sum itself retains wrong-arm and fixed-fallback regret;
nothing is silently replaced with the oracle. Cross-host-unstable labels must be
explicitly abstained. The candidate must retain at least `1.10x` fully charged
speedup over the best fixed arm and must be faster than the fully charged frozen
analytical control on every host. Perfect classification with expensive inference
therefore fails, as it should.

## Neural repeatability

A `tiny_neural` candidate is assessed across at least three distinct training
seeds. Every seed must independently pass every validation and audit criterion.
The combined report records the worst accuracy, balanced accuracy, coverage,
majority margin, and analytical-control margin across seeds. One failing seed
rejects the replicated neural signal; duplicate seeds or candidate IDs fail closed.

No neural architecture has been trained under this protocol. The repeatability
gate exists so that a future lucky seed cannot be mistaken for a robust result if
the exact economics ever justify a development experiment.

## Implementation and verification

- `cmbench/recognition/query_ladder_development_experiment.py`
- `scripts/cm_query_ladder_development_experiment.py`
- `tests/test_query_ladder_development_experiment.py`

The tests cover fit callback non-invocation, freeze/handoff mismatch, feature and
split tampering, abstention exclusion from fit, identity-free fit rows, explicit
chance/majority/control comparisons, low-signal rejection, validation/audit leakage,
prospective-data refusal, prediction digest tampering, three-seed neural stability,
duplicate-seed refusal, exact timing-table replay, same-host binding, expensive-model
rejection, and the read-only command-line evaluator.

A future eligible result can be assessed without running a benchmark or training a
model:

```powershell
.\.venv\Scripts\python.exe scripts\cm_query_ladder_development_experiment.py `
  --freeze <FREEZE.json> `
  --handoff <verified-handoff.json> `
  --dataset <verified-development-labels.json> `
  --predictions <candidate-predictions.json> `
  --routing-evidence <verified-routing-evidence.json> `
  --output <development-assessment.json>
```

Without `--routing-evidence`, exit code `0` means the candidate established a
development-only prediction signal. With that argument, exit code `0` additionally
requires candidate-specific fully charged economics on both hosts. Exit code `2`
means rejection or fail-closed abstention. Neither exit code permits a production
action.

## Remaining admissible work

The Benchmark task must independently produce the exact two-machine labels and
same-host charged cost vector for the already frozen 72-case surface. The learning
task must not reproduce that run or treat the inspected 54-case cohort as
source-blind training data.

If the future handoff passes, the next bounded development sequence is:

1. time the frozen analytical control and identity-free feature extraction on both
   benchmark hosts;
2. fit deterministic bounded-tree and linear controls before any neural model;
3. evaluate validation without exposing audit labels to fitting or model selection;
4. lock a candidate and evaluate audit once;
5. for neural work, require all three predeclared seeds to pass; and
6. feed independently verified per-host candidate timing into the routed-economics
   evaluator, retaining abstention regret and the unchanged exact fallback.

If any exact, signal, repeatability, or economic gate fails, stop without prospective
consumption or promotion. C5 partition learning remains a separate stopped task
until a sound independently checked certificate avoids material global-best
completion work.
