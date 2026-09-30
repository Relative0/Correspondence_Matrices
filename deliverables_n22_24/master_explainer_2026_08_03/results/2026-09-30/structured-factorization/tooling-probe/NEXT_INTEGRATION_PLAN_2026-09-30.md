# Next gate: live-vtree integration into exact factorization

**Status:** plan only, 30 September 2026. No new campaign has been run.

The live PySDD probe cleared the local-move tooling question. It did not test
whether a search that uses those moves improves complete exact factorization.
Phase 5B's registered algorithmic **NO-GO** remains the result for its
recompilation-based M5 campaign. This plan defines a separate, bounded
integration gate. The live probe's eight synthetic timing cases are regression
inputs only and must not become its held-out decision set.

## Research question and decision boundaries

Does a live M1 or M2 search, started from the same syntax tree and given the
same neighbor order and budget as its fresh-compilation counterpart, reduce
complete exact factorization time relative to the strongest eligible baseline?
Complete time includes vtree/manager setup, CNF construction, GC, every native
move, extraction and scoring, inverse moves and winner replay, exact residual
SAT, carrier assembly, and any failed-operation handling. Do not use semantic
prime truth, measured SAT time or held-out outcomes to score candidate trees.

There are two distinct decisions:

1. **Mechanism GO/NO-GO:** Can live M1/M2 reproduce the exact outcome of fresh
   M1/M2 with fewer resources at identical search decisions?
2. **Algorithmic GO/NO-GO:** Does a validation-selected live method beat a
   validation-selected non-oracle baseline on new held-out total time under the
   locked protocol below? A positive mechanism decision does not imply a
   positive algorithmic decision.

Neither decision would establish industrial performance or a publication
claim. A broader scale/public-corpus gate would require a separate protocol.

## Phase 1 — isolated integration and matched implementation

Create a new sibling output directory for all code, manifests and results.
Use the probe's `LiveSession` as a starting point, with documented ownership of
the manager and every referenced root. Compile the CNF once at the syntax B3
tree, then retain the root through local transformations. Reacquire the
manager-owned vtree and SDD elements after every edit; GC before every move;
check the native return code; undo each successful rejected candidate with an
uncapped inverse; replay the selected candidate once. Failed limited moves
must leave the state intact and be charged. Record cumulative native forward,
inverse, GC, extraction, score and replay times, plus peak working set.

Port **M1 and M2 only** at first. Preserve Phase 5B's non-oracle objectives,
syntax B3 starting tree, serialized neighbor order, first six unseen neighbors
per round, at most two rounds, and deterministic tie breaks. The probe's
`one_round()` evaluates *all* neighbors; do not use that broader policy in the
matched comparison. Keep a fresh-compilation M1/M2 adapter with the same
candidate set so a pair differs only in how candidates are realized.

For every final tree, pass its **certified direct partition** into the existing
`exact_refine(n, clauses, direct_partition, carrier)` path. Every nonsingleton
direct block still gets SAT refinement. Keep the PySAT solver persistent inside
that refinement, preserve the final carrier least-common-coarsening rule, and
separate the worker from the independent truth evaluator. No oracle partition
enters any non-oracle worker. Do not add M3–M5 features or tune weights in this
gate; they would confound the local-move mechanism.

Maintain three non-oracle comparison baselines: B2 (the original balanced tree
with native PySDD minimization), B3 (the original syntax component/min-fill
tree), and a stronger **B4 syntax-only recursive separator tree**. Define B4
deterministically before timing: preserve disconnected primal-graph components
as clades; within a connected set choose the most balanced bipartition with
minimum crossing primal edges, breaking ties lexicographically by variable
labels; recurse on each side. Exhaustive bipartition search is acceptable for
the bounded variable sizes in this gate, and its construction time is charged.
Validate the implementation and document its size limit before freezing.

**Exit to Phase 2:** all seven implementations return the same semantic and
carrier-combined exact partitions on the development tests; the live/fresh
M1 and M2 pairs also return the same candidate order, per-candidate score,
acceptance decisions, final tree, and direct partition. Any mismatch is a
correctness defect, not a timing observation.

## Phase 2 — hostile correctness and resource checks

Use the old probe's exhaustive evaluator only in development tests. Add
long sequences that mix root and internal swaps/rotations and compare every
edited state against fresh compilation and direct CNF truth where exhaustive
evaluation is feasible. Include true, false, free/literal variables, trimmed
SDDs, multiple referenced roots, crossing carriers, and cases with many dead
intermediate nodes. For larger SDDs, use independent SAT equivalence checks
or an equivalent exact miter, not just equal model counts. Compare final exact
refinement against a separate relation-projection oracle on small cases.

Induce native `limited=1` failures using initialized size/time/cartesian
limits; check tree, function, partition and all referenced roots immediately
after each failure. Alternate accepted/rejected moves to expose stale-pointer
and inverse-state bugs. Measure memory and restoration costs over long move
sequences, with process isolation so a crash or cap breach is retained as a
failure. A limit configuration must be fixed before formal timing; uncapped
inverses need a worker watchdog and memory cap.

**Exit to Phase 3:** zero exactness, pair-parity or rollback discrepancies;
all stress runs either complete or produce a correctly classified resource
failure. If this fails, stop and report integration NO-GO. Repair and rerun
development tests before freezing, retaining a repair log.

## Phase 3 — freeze a new experimental protocol

Before validation or held-out performance runs, save and hash the source,
protocol, environment, dependencies, generator, manifest and independent
evaluator. Freeze the instance IDs, structure families, sizes, carriers,
generation seeds, timing repetition seeds, method order, baseline/challenger
selection rule, time/memory limits, failure accounting and analysis script.
The new manifest must not contain Phase 5B's 30 held-out CNFs or the probe's
eight timing CNFs. Neither set may choose objectives, coefficients or seeds.

Generate independently structured nonfalse inputs rather than relabelled
versions of one module: include component/block-cut cases, overlapping
bounded-width constraints, cardinality/threshold constraints, parity or XOR
constraints, nested operators, and crossing-carrier cases. Reserve entire
generator templates for the new held-out split, not merely new seeds of the
same templates. Include satisfiable/unsatisfiable and free-variable controls
in correctness testing, with false handled under its explicit contract.
Separate any licensed public CNFs into an external challenge stratum; record
license, source and preprocessing. Small documentation CNFs remain smoke tests.

For a **bounded local gate**, propose n=8–14 with a fixed manifest of at least
12 validation and 24 held-out instances spanning at least four and six
structural templates respectively; choose the exact IDs and sizes once from
generator output and freeze them before timing. Use three fresh-process timing
repetitions per instance and method. Freeze a 20-second worker watchdog,
2 GiB process-memory cap, 40-second PAR2 value for timeout/error/cap failures,
and 90-minute total campaign ceiling. If implementation of the memory cap is
not reliable on this Windows host, stop before formal timing and either repair
it or revise the **unrun** protocol with a dated record. All limits, including
the live native operation limits, must apply consistently and be logged.

The decision set contains B2, B3, B4, fresh M1/M2 and live M1/M2. Select one
baseline from B2/B3/B4 and one live challenger from live M1/M2 using *only*
validation geometric-mean complete time with PAR2 failures; freeze those
identities before held-out execution. Fresh M1/M2 remain matched mechanism
controls, not candidates for post hoc rescue. No method sees independent
semantic truth until its worker has finished.

**Exit to Phase 4:** hash and chronology checks pass, every method has an
executable worker, and no held-out result exists. A pilot on development
fixtures may set engineering limits before this freeze; validation and
held-out results may not.

## Phase 4 — sequential measurement and final decision

Run validation, lock selections, then run held-out sequentially with shuffled
method order. Charge all worker stages in the same timer. Record root-reachable
SDD size/count, direct exposed blocks, residual block sizes, SAT calls and
solve/setup time, move/undo/replay counts and cost, total wall time, process
wall time, peak memory, failures and raw per-move traces. Exclude independent
truth evaluation equally from all algorithm timers. Keep one fresh worker per
trial so process peak memory has a comparable meaning. The evaluator checks
semantic and carrier-combined exact partitions and stops on disagreement.

On held-out data, compute each instance's median over three repetitions,
pair challenger with the locked baseline, and bootstrap instances (10,000
draws with a frozen seed). **Algorithmic GO** requires zero correctness
disagreements, no excess failures, a paired geometric complete-time ratio
at most 0.90, and a 95% paired-bootstrap upper ratio below 1. Report both
failure-adjusted and completed-run times, all raw rows, family strata,
per-instance wins/losses, SAT work and memory. A mechanism GO requires exact
M1/M2 parity and a lower paired complete *search-stage* cost for live versus
fresh M1/M2, with a 95% paired-instance bootstrap upper cost ratio below 1;
it does not override an algorithmic NO-GO. Stop if the campaign
ceiling is hit and report censored outcomes rather than extending the budget
after seeing results. Do not turn a favorable secondary exposure/SAT metric
into a substitute for the locked primary criterion.

The deliverable is a short **integration GO/NO-GO report** with hashes,
instrumented source, raw rows, independent correctness results, exact resource
accounting, selected comparisons and limitations. It explicitly retains
Phase 5B's negative result. A positive bounded result warrants a separately
registered larger-scale/public-corpus experiment, not a publication claim.

## Work boundary and task choice

Continue the integration and protocol drafting in this task: the probe's live
code, exactness tests and source audit directly reduce setup and mistake risk.
At the boundary after the integration passes hostile checks, reassess context.
If the frozen measurement phase is fully specified and its compact handoff is
smaller than carrying the development history, move that self-contained run to
a fresh task; otherwise keep the same task. Task length alone is not a reason
to move. The old archived Phase 4/5 files and frozen campaign outputs remain
read-only throughout.
