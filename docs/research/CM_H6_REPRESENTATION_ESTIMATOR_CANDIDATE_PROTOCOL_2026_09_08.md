# H6 representation-estimator candidate protocol

Date: 2026-09-08  
Scope: one development-only, exact non-neural H6 estimator candidate  
Status: protocol drafted before decision-bearing candidate evaluation

## Question

Does a minimal representation-specific model improve conservative retained-memory
estimates for repeated-restriction prepared state, relative to the same model with no
representation identity, when both are evaluated against unchanged current-source H6
measurements?

This is the single small reversible candidate permitted by the successful fresh-process
H6 calibration gate. It is research tooling only. It does not alter an evaluator,
router, selector, cache, serialization format, production default, or caller-visible
behavior, and it does not reopen H2, H3, H8, or H9.

## Frozen evidence and split

The candidate consumes the sealed 708-row H6 attempt and its independently verified
summary. It does not launch new workloads or refit the H6 measurement protocol.

- Only Lane B `reused` rows are admitted.
- All four unchanged arms are retained: R2 topological liveness, CM-IR bigint,
  CSE-flat bigint, and native fused slots.
- Both q1 and q64 and all three fresh-process replicates are combined. The target for
  each row is the larger nonnegative prepared-state retained delta from working set and
  private usage. Each case/arm target is the median of its six rows.
- The six preselected synthetic `fresh-*` cases are the calibration cohort.
- The five preselected `c36-*` observed cases are a locked holdout cohort.
- The only predictor is the preconstruction `expression_bytes` feature already emitted
  by H6. No timing, target-memory, family label, case identity, query result, fitted
  selector, or postconstruction metric is a feature.

The split and formula are fixed before parsing any H6 memory value for candidate
evaluation. Failures, ties, zero deltas, and unfavorable predictions remain in the
analysis.

## Candidate and control

Both models use the same nonnegative-slope affine upper-envelope rule. For training
pairs `(x, y)`, ordinary least squares supplies a slope and intercept; the slope is
clamped to zero, the intercept is recomputed as the mean residual, and the smallest
nonnegative additive margin that covers every training target is applied. Predictions
are clamped to zero and rounded upward to whole bytes.

- **Control:** one pooled model across all four arms.
- **Only candidate:** one independently fitted model per arm.

The candidate therefore adds representation identity and nothing else. It remains a
diagnostic estimate and cannot serve results or make a routing decision.

## Frozen evaluation

Prediction error is absolute base-2 log ratio with a 64 KiB additive resolution floor:
`abs(log2((prediction + 65536) / (actual + 65536)))`. The same floor defines material
underprediction and observed pairwise ties, reflecting the H6 OS-signal floor.

The candidate passes only if every condition holds:

1. The parent freeze, raw rows, controller summary, and independent replay hashes match;
   all 708 H6 rows remain exact and the replay remains verified with zero mismatches.
2. The candidate has exactly 24 calibration cells and 20 locked holdout cells, with six
   source rows per case/arm cell, all expected arms present, and invariant features.
3. Holdout median log-ratio error improves by at least 15% over the pooled control.
4. No more than 20% of holdout cells materially underpredict actual retained memory by
   more than 64 KiB.
5. Median holdout overprediction factor, using the same 64 KiB floor, is at most 2.0.
6. At least 70% of materially ordered holdout arm pairs have the same ordering in the
   candidate predictions. Observed arm pairs within 64 KiB are ties and excluded.
7. For at least four of five observed cases, the candidate-selected minimum-memory arm
   is within 64 KiB of the measured minimum.
8. In leave-one-fresh-case-out calibration, the arm-specific model has lower median
   error than the pooled control in at least four of six folds.
9. Independent summary replay reports zero source, schedule, fit, prediction, metric,
   and decision mismatches.

Passing means only `go_local_estimator_evidence_request_runpod_authorization`. It allows
preparing an exact authorization request for one independently frozen RunPod replication;
it does not itself authorize RunPod or any production change. Any failed condition means
`no_go_h6_estimator_and_routing_deferred`; no second candidate is tried in this phase.

## Required local checks

- candidate freeze, fit, split, metric, decision, and independent-replay tests;
- the H6 calibration tests and repaired historical-freeze/current-drift tests;
- exhaustive small-function, sharing metamorphic, ordering/hash, low-sharing, and
  cold/reused architecture controls;
- `scripts/cm_research_check.py` and maintained non-neural research checks.
