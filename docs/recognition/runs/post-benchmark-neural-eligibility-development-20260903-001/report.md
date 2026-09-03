# Post-benchmark neural eligibility reassessment

Date: 2026-09-03  
Status: **complete; neural training remains prohibited**

Retry 002 is valid exact, source-bound, one-host development evidence. This
reassessment recomputes fixed-versus-per-case-oracle economics from per-case
median accounted-total timings. It does not fit a selector or consume new data.

## Decision

Across 22 task/cohort surfaces, only
`lane_d_version_history_resident_engine` reaches the 1.10x gross point gate. Its best fixed
method is `sat/resident_engine` and its gross headroom is
`1.137580420x` across only
3 complete cases, with diagnostic labels
`{"cnf/resident_engine": 1, "sat/resident_engine": 2}`.

The gross saving is only 43015.0 ns in total.
Charging the historical recognition allowance of
123,400 ns per case reduces the
optimistic speedup to `0.520856231x`,
while model inference, exact verification, and fallback are still assumed free.
Only 3560.5 ns per case
of total overhead could preserve the 1.10x gate.

Therefore the run contains a new gross signal worth recording, but not a
trainable or prospectively confirmable neural decision. Advice remains disabled,
all cases abstain, and the exact fallback is unchanged.

## Task boundary

- C5 decomposition and partition work remains stopped: retry 002 supplies no
  sound early-termination or certificate mechanism that avoids global-best work.
- Lane B q64, complete-relation, and related-root surfaces remain below 1.10x.
- A future version-history investigation must start with a source-blind expanded
  development design and analytical controls capable of sub-3.6 microsecond
  recognition. It is not authorized by this artifact.

No fresh corpus selection or inspection, prospective data, timing, cloud resource,
selector fit, neural training, route change, production write, or publication
occurred in this reassessment.
