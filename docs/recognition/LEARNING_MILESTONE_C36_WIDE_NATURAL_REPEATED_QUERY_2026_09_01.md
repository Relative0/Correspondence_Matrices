# Learning milestone C36: wider natural repeated-query routing headroom

Date: 2026-09-01  
Status: **locally complete and independently verified; fixed CM gate failed; exploratory routing headroom found**

## Question

C35 showed that resident CM IR could amortize past direct AST restriction at 64 queries, but
remained behind sharing-aware flattened CSE on natural functions of support 3-10. C36 tests fresh,
wider functions and adds an efficient compiled truth-projection control. Every timed method must
deliver the same reduced relation, exact count, SAT status, and canonical witness.

C36 performs no neural training, model fitting, policy refit, production write, or production
promotion.

## Frozen wider-natural corpus

The corpus contains **18 fresh parameter/truth identities**, with three cases at each support width
from 11 through 16. Five circuit families are represented: decoder index, reverse-shift decoder,
adder tree, low multiply cone, and low multiply-add cone. Selection was frozen from source metadata
without method outputs or timings.

The underlying Yosys repository and pinned commit are reused, so this is fresh function evidence but
not independent-source confirmation. None of the selected width/truth identities occurs in the prior
C23 natural corpus.

Each function receives 64 deterministic, output-blind restrictions. Every query leaves exactly 6,
8, or 10 variables live. The frozen dataset therefore contains 1,152 semantic queries. Its separate
verifier regenerated the source selections, scalar truth vectors, traces, reduced relations, counts,
SAT results, and witnesses with zero mismatches.

## Aligned exact methods

Four resident methods were timed:

1. recursive direct AST restriction;
2. sharing-aware flattened structural CSE with the NumPy word kernel;
3. canonical CM IR with the same NumPy word kernel; and
4. full truth materialization followed by precompiled NumPy projection indices.

The fourth arm is a materially stronger truth-cache control than C35's transparent scalar
projection. Setup, compilation/materialization, all query work, output delivery, and cleanup are
charged. The eight-block schedule counterbalances every method twice through every execution
position for each case. Cumulative totals are recorded after 1, 4, 16, and 64 queries.

`dd.autoref` BDD and CaDiCaL also reproduced exact bounded query results on one case at each width.
They are functional checks, not performance rankings. Native CUDD was unavailable locally.

## Local results

The retained run contains **576 sessions and 36,864 timed exact queries**.

| Queries | Best fixed method | CM vs flattened CSE | CM vs direct AST | CM vs compiled projection |
|---:|---|---:|---:|---:|
| 1 | flattened CSE | 0.4313x | 0.6403x | 3.9260x |
| 4 | flattened CSE | 0.5410x | 1.5942x | 3.1779x |
| 16 | flattened CSE | 0.7153x | 3.5346x | 1.9507x |
| 64 | flattened CSE | **0.8783x** | **5.3326x** | **0.9376x** |

At 64 queries, aggregate case medians total 125.454 ms for flattened CSE, 133.925 ms for compiled
truth projection, 142.836 ms for CM IR, and 761.686 ms for direct AST. The direct total is dominated
by multiply cases; direct AST is still the individual winner on the 14 non-multiply or multiply-add
cases. CM is about 13.9% slower than flattened CSE and about 6.7% slower than compiled projection.
It beats flattened CSE on zero of the 18 cases at the final checkpoint.

The fixed CM promotion gate therefore fails. C36 does not support CM IR as the universal backend for
this wider repeated-restriction workload.

## Exact routing headroom

The individual winners reveal a clean family split. Direct AST is best for adder trees, both decoder
families, and multiply-add. Compiled truth projection is best in aggregate for low multiply cones.
A post-hoc family rule using those choices totals 95.479 ms. Charging the previously frozen
123.4-microsecond recognition budget once for every case raises it to 97.700 ms, still **1.2841x**
faster than the best fixed method. The unattainable per-case oracle is 1.3564x faster than the best
fixed method, so the simple family rule captures most of the observed selectable headroom.

This is an exploratory result. The rule was chosen after examining C36 timings, so it cannot be
promoted or described as held-out learning. Its value is that it establishes a measurable decision
surface large enough to justify a prospective routing experiment.

## Exactness and independent verification

All four methods produced the same canonical output digest for all cases and blocks. The independent
verifier replayed 18 source truth vectors, all 1,152 semantic queries, 72 contracts, 576 measurement
rows, 36,864 timed query deliveries, and 12 external functional-probe rows. It independently
recomputed every checkpoint, median, fixed winner, family total, routing charge, and promotion gate.

- trace mismatches: 0;
- oracle mismatches: 0;
- contract mismatches: 0;
- measurement mismatches: 0;
- summary mismatches: 0; and
- control mismatches: 0.

## Where the learning work stands

There is no fully trained expression oracle and no neural model is used in C36. Earlier work trained
matrix MLP, matrix CNN, graph GNN, fused graph-plus-matrix, contrastive graph-retrieval, and later
variable-conditioned GNN models. Some learned the generated training mechanism, but none transferred
reliably enough to natural held-out circuits or beat the strongest exact controls. Every neural
proposal remained advisory and independently checked; exact fallback preserved correct final
outputs.

The strongest promoted research results so far are deterministic exact algorithms and guarded
policies, including packed source ANF/GF(2), exact caches, and prepared rules. Their perfect outputs
come from exact computation and verification, not from a neural model making perfect predictions.

C36 is the first recent lifecycle to expose enough outcome-independent *candidate* headroom for a
new routing comparison. The next comparison should begin with the smallest interpretable rule or
tree; a larger neural model is not justified until a simple prospective selector fails despite
stable headroom.

## Decision and next milestone

C37 should freeze the C36 family rule before loading new cases, then test it prospectively on unseen
parameter/truth identities and at least one independently authored family or source. Compare:

1. the frozen family rule;
2. a tiny depth-limited cost tree trained only on a development split;
3. all four fixed exact methods; and
4. the unattainable per-case oracle as a diagnostic ceiling.

Charge representation recognition, selection, exact output verification, and fallback. Require at
least 1.05x over the best fixed method, no material family or width regret, zero semantic mismatches,
and unchanged results with advice disabled. Only a prospectively passing selector should proceed to
unchanged second-machine confirmation. Persistence/reload and related-DAG version traces remain a
separate later lifecycle.

## Evidence

- Verified run: `docs/recognition/runs/c36-wide-repeated-windows-20260901-003`
- Frozen dataset: `docs/recognition/c36_wide_repeated_query_dataset.json`
- Dataset verification: `docs/recognition/c36_wide_repeated_query_dataset_verification.json`
- Core adapters: `cmbench/comparative/gf2_wide_repeated_queries.py`
- Experiment: `cmbench/comparative/gf2_wide_repeated_query_experiment.py`
- Independent verifier: `scripts/crse_gf2_wide_repeated_query_verify.py`
