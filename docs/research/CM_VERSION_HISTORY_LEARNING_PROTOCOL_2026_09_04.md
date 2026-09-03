# CM source-blind version-history learning protocol

**Date:** 2026-09-04  
**Scope:** development-only protocol, analytical-control timing, verified benchmark
handoff, fail-closed learning gates, and C5 certificate requirements. No training,
prospective data consumption, exact benchmark execution, production routing, or
model promotion.

## Decision

The requested learning infrastructure is implemented, but selector fitting and
neural training remain disabled.

Two independently verified exact results are now consumed as read-only artifacts:

1. The resident version-history surface has three complete exposed cases, with
   two `sat/resident_engine` labels and one `cnf/resident_engine` label. Its best
   fixed sum is 355,668.5 ns, its per-case-oracle sum is 312,653.5 ns, and gross
   headroom is `1.137580420x`. Only 3,560.5 ns/case of total recognition and
   routing overhead can preserve a 1.10x speedup.
2. The completed query-ladder retry contains 27,648 independently verified rows.
   At q64, `cse_flat_bigint` is the best fixed arm and its reported case-median
   geometric-mean slowdown to the per-case oracle is `1.107862216x`. That metric
   is not a sum-based fully charged selector headroom calculation. The benchmark
   claim boundary explicitly forbids selector/neural claims and requires
   cross-machine replication.

The learning implementation does not import a benchmark runner or recompute either
benchmark. It authenticates completed results using the assessment/analysis,
independent-verification, result, raw-evidence, freeze, runtime, source, and cleanup
hash chains. Missing, incomplete, drifted, tampered, or claim-ineligible inputs
produce complete abstention and the unchanged exact fallback.

## Source-blind protocol

The model-visible vector contains only ten structural counts available before
method timing:

- variable and version counts;
- total, minimum, and maximum clauses per version;
- L1 clause-count churn;
- query and assumption-literal counts; and
- distinct queried versions and revisit count.

Case IDs, source names/families, cluster IDs, opaque provenance hashes, split names,
backend labels, timings, arm order, and blocks are forbidden model fields. Opaque
source-group hashes are retained only for the split auditor.

Groups are assigned deterministically with a salted SHA-256 rule to three
development-only buckets: 60% fit, 20% validation, and 20% audit. This does not
relabel already exposed data as prospective. The current cohort has two fit groups,
one validation group, and zero audit groups. The protocol requires at least
16/8/8 groups respectively and at least eight source groups per label before any
fit can be considered. Cross-split group overlap is zero, but sample sufficiency
fails.

The current exact labels predate this protocol. Therefore all present control
accuracy is explicitly retrospective and earns no eligibility credit.

## Ultra-cheap analytical controls

The feature extractor and three zero-fit controls were timed locally with Python
3.13.5 on Windows using 21 batches and 2,000 repetitions per case per batch. The
timing harness executed zero exact backends.

| Feature + control | Median ns/case | p95 ns/case | p95 under 3,560.5 ns |
|---|---:|---:|---|
| fixed CNF | 2,892.6 | 3,430.6 | yes |
| fixed SAT | 2,657.4 | 2,786.1 | yes |
| bounded CNF then SAT | 2,686.7 | 2,894.2 | yes |

The bounded structural control happens to match all three exposed oracle labels.
Charging its p95 extraction/control time while assuming zero model inference,
exact-verification, and fallback cost gives an optimistic diagnostic speedup of
`1.106842821x`.

That is not authorization evidence:

- three exposed source groups are insufficient;
- the control was specified after the labels existed;
- the recognition timing host does not match the Linux exact-timing host;
- the query-ladder result is still one-host and disallows selector claims; and
- model inference, exact verification, and fallback costs are unmeasured rather
  than silently replaced with zero in the fully charged gate.

Accordingly, fully charged speedup is recorded as `null`, not estimated, and the
1.10x training gate fails closed.

## Fail-closed behavior and tests

The implementation rejects or abstains on:

- missing or altered benchmark artifacts;
- absent or altered independent verification;
- mismatched result, raw-measurement, freeze, runtime, source, or cleanup hashes;
- incomplete exactness or prohibited selector/neural claims;
- source-group overlap across splits or altered split assignment;
- identity, label, or timing leakage into model features;
- incomplete recognition/inference/verification/fallback costs; and
- any attempt to enable advice or bypass the unchanged exact fallback.

The abstention wrapper calls the supplied exact fallback directly and returns the
same result. No learned or analytical advice is live.

## C5 certificate and early termination

C5 retains exact candidate reconstruction and non-anchor variable-renaming
equivariance, but neither property proves global optimality. A future partition
learner is ineligible unless it supplies all of the following:

1. a sound bound for the actual global objective;
2. coverage of every unexplored partition;
3. a checker independent of the model;
4. exact reconstruction of the proposed candidate;
5. the unchanged exact fallback;
6. termination without running the completion search;
7. zero failures on adversarial, variable-renaming, sharing, and operand-order
   metamorphic checks;
8. measured and charged certificate-verification cost; and
9. at least 25% of measured global-best completion work avoided after charging
   certificate verification.

The 25% value is a development engineering floor for “material” work avoidance,
not a mathematical theorem. C5 currently has no global bound, no certificate,
no independent checker, and no measured completion work avoided; partition
learning remains stopped.

## Implementation and artifact

- `cmbench/recognition/version_history_learning_protocol.py`
- `scripts/cm_version_history_learning_protocol.py`
- `scripts/crse_version_history_learning_protocol_verify.py`
- `tests/test_version_history_learning_protocol.py`
- canonical development artifact:
  `docs/recognition/runs/version-history-learning-development-20260904-004`

The canonical assessment SHA-256 is
`50d24b481c1e91a94329ae563042624b3e1f2bcf1601134e29a974c8e9d00460`.
Independent verification status is `verified_protocol_no_training`; it
reauthenticated both benchmark inputs, replayed the assessment and report byte for
byte, and executed a fresh recognition-timing smoke with zero exact-backend calls.

Create-only attempts `-001`, `-002`, and `-003` are superseded local diagnostics.
They were not overwritten: `-001` exposed a verifier key-name defect, `-002`
predates the completed query-ladder handoff, and `-003` briefly bound a concurrently
edited prose interpretation instead of machine evidence alone. None is canonical.

## Next eligibility boundary

No neural training or prospective corpus consumption is justified now. Reconsider
only after a verified, source-closed exact surface supplies a sum-based per-case
oracle calculation that remains at least approximately `1.10x` after all relevant
exact baselines and all recognition, inference, exact-verification, and fallback
costs on the decision-bearing host. A new protocol must be frozen before its labels
are inspected, and its source-group split minimums must pass.
