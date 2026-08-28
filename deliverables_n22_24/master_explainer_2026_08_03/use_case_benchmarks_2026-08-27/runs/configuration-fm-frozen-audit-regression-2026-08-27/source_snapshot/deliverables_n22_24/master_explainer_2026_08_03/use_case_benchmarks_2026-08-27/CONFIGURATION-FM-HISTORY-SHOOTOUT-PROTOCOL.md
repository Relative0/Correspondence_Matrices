# Real feature-model history representation shootout protocol

**Frozen:** 2026-08-27, after exact corpus acquisition and source-format
inspection, but before any shootout case was constructed or timed.

## Question and claim boundary

For bounded residual Boolean relations drawn from real feature-model histories,
which representation is best for complete output, symbolic restriction, exact
counting, serialization/reload, and adjacent-version change analysis?

This is not a whole-feature-model compilation claim.  Every reported relation
has at most 16 free original feature variables; all other variables are fixed
by an explicitly recorded satisfying context.  Natural endpoint and natural
transition results remain separate from the earlier planted synthetic sweep.

## Immutable source and cohort

- Official source: `SoftVarE-Group/feature-model-benchmark` commit
  `afa60ee2c836e7bdc4068e0f4f128ea31158d2ad`.
- The existing frozen history selection supplies the first, middle, and last
  adjacent transition from every history in `statistics/Complete.csv`.
- The acquired cohort contains 40 unique endpoints from seven histories:
  `automotive2`, `FinancialServices01`, `BusyBox`, `Fiasco`, `Linux`, `soletta`,
  and `uClibc`.
- Inputs are admitted only when the exact tree-selected payload is available,
  its recorded SHA-256 matches, DIMACS parsing succeeds, the model is
  satisfiable, and at least 16 original feature names are mapped.  Every
  exclusion or timeout is retained.
- No source-repository script is executed.  Compressed payloads are admitted
  only under the safe single-member archive rule in the frozen history pilot.

## Natural endpoint cases

For every admitted endpoint, use the recorded CaDiCaL witness and condition all
variables outside each selected slice exactly as in the V2 history protocol.
At each `k in {8,12,16}`, select two deterministic slices:

1. `incidence`: highest native-clause incidence, then feature name and DIMACS
   variable number; and
2. `hash`: SHA-256 order of `model_id|DIMACS-variable`, matching the earlier
   representation battery's independently reproducible slice contract.

The external packed contract is LSB-first in the recorded slice order.  Record
residual clause/literal count, unique-clause fraction, solution density, and
conditioning time.  Equal outputs, not equal internal operations, are required
before any timing is accepted.

## Adjacent-version cases

Use the 21 preregistered first/middle/last transitions.  Align original
variables by exact feature name.  Build a combined CNF in which common feature
names share one variable and version-unique names remain disjoint.  A transition
is admitted only if this combined formula is satisfiable, thereby providing one
shared named-feature configuration valid in both versions.

For each admitted transition and width, select `incidence` and `hash` slices
from features common to both endpoints.  Condition each version on the same
joint witness outside the slice.  Compare the two complete bounded relations
and record XOR population, Jaccard similarity, changed clauses, common-feature
fraction, and changed-assignment density.  This measures a local semantic
version delta around a shared valid context; it is not a whole-model diff.

## Arms

1. `cm_flat`: current CM IR compilation and flat packed execution.
2. `cse_flat`: independent structural-CSE flat evaluator.
3. `cnf_bitset`: specialized direct packed CNF evaluation.
4. `cudd_fixed`: native CUDD ROBDD with the recorded slice order.
5. `cudd_sifted`: the same CUDD graph after native dynamic reordering.  Charge
   manager creation, initial construction, and reordering separately; never
   report only the selected graph.
6. `cadical195`: incremental CaDiCaL under complete and partial assumptions.
7. `d4_count` and `d4_ddnnf`: exact model count and d-DNNF compilation from
   official d4 commit `333370cc1e843dd0749c1efe88516e72b5239174`.
8. `cudd_zdd`: admit only if a callable native CUDD ZDD API is available.  The
   Python `dd` BDD wrapper is not a ZDD arm, and no home-grown substitute may be
   labeled CUDD ZDD.  Unavailability is a recorded acquisition refusal.

## Tasks

For every endpoint case where the relevant backend is available:

- cold construction, including manager/declaration and ordering cost;
- complete packed-vector production;
- 256 deterministic complete-assignment point queries;
- 64 deterministic partial contexts at fixed fractions `0.25`, `0.50`, and
  `0.75`;
- exact count and one deterministic witness;
- serialization, artifact bytes, reload, and post-reload equality;
- Python allocation peaks for Python arms, labeled separately from native RSS;
  and
- isolated-process peak RSS on the `k=16` incidence case for each endpoint.

For every admitted transition case:

- fresh versus shared-manager CUDD construction;
- fresh versus persistent-pool CM compilation;
- selector-guarded incremental CaDiCaL sessions for both versions;
- complete relation XOR and affected-assignment count; and
- exact agreement of CM, CNF, CUDD, CaDiCaL, and d4 counts where applicable.

## Timing, resource, and timeout rules

- Five counterbalanced timed rounds after one untimed correctness/warm-up pass.
- Store all raw round samples or case medians and label one-shot operations.
- Query sessions reuse the constructed representation; end-to-end totals are
  also reported.
- Peak RSS is measured in isolated child processes.  Do not compare Python
  `tracemalloc` with CUDD's C heap.
- Per external backend invocation timeout: 60 seconds.  Retain timeout rows.
- Dynamic ordering search/reorder time and d-DNNF extraction/output time are
  charged to the arm that requires them.

## Correctness and audit gates

A case is accepted only when:

- CM, CSE, direct CNF, fixed CUDD, sifted CUDD, and CaDiCaL agree bit-for-bit on
  every complete assignment;
- packed, CUDD, and CaDiCaL partial-context satisfiability agree;
- all available exact counters agree with packed `bit_count`;
- serialized/reloaded representations reproduce their original relation or
  count; and
- transition XOR, count difference, and witness claims independently
  reconstruct from the two endpoint relations.

The independent auditor re-reads the frozen corpus rows and serialized files,
recomputes hashes and all semantic gates, and refuses summary publication on
any mismatch.

## Statistics and reporting

- Raw rows are primary evidence.
- Natural endpoint ratios are equal-weight geometric means by history, then
  across histories; report medians and ranges alongside them.
- Transition summaries weight each history equally, not each version equally.
- Report crossover strata by `k`, solution density, residual clause density,
  duplicate/unique fraction, feature overlap, edit locality, and query reuse.
- Report wins, losses, timeouts, refusals, and never-break-even cells.  No
  aggregate “overall winner” is permitted across tasks with different output
  obligations.

## Planned artifacts

- exact source/provenance snapshot and backend manifest;
- endpoint cases and raw timing rows;
- partial-context rows;
- transition/version-delta rows;
- native-memory rows;
- serialized CM/CNF/ROBDD/d-DNNF artifacts where admitted;
- checksums and independent-audit result; and
- a viewer-oriented results report with explicit negative findings.

## Pre-execution backend acquisition correction

The first native-image build attempted the newer official d4v2 commit
`15eff31962466804a48374826b9e5a746fc2766e`.  Its repository does not contain
the referenced `3rdParty/patoh/libpatoh.a`, so the official build fails at its
final archive step.  No benchmark case had run.  The arm was therefore changed
to the official d4 repository at commit
`333370cc1e843dd0749c1efe88516e72b5239174`, whose documented CLI directly
supports both model counting (`-mc`) and d-DNNF output (`-dDNNF`) and whose
pinned tree contains the referenced library.  The failed d4v2 acquisition is
retained as a refusal; no timing, case, threshold, or corpus rule changed.
