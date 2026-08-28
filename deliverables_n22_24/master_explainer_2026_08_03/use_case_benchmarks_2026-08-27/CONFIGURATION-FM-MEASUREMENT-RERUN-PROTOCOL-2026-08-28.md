# Feature-model measurement repair: next-run protocol

Prepared 2026-08-28. **Not executed, not yet frozen as a preregistered run,
and not a new result.** This is the implementation/acceptance contract for
repairing the 13 gaps in the saved-run independence audit. The historical
outputs remain immutable, and their existing qualifications remain in force.

## Priority and decision

Repair measurement boundaries and reproducibility before adding more
headline speedup ratios or a larger corpus. The independently replayed
bounded Boolean outputs remain useful; they do not establish an overall
winner. The next result should identify when CM's reuse and bounded-output
costs beat alternatives, including cases where they do not.

First implement and test the runner against a tiny synthetic contract suite.
Then run a small real-corpus plumbing pilot. Only after independent artifact
replay and resource/timer checks pass should the full cohort be timed. Do not
spend cloud budget on a runner which still has the audited contract defects.
The separate memory-safety task's approved smoke is not this experiment and
does not authorize a new upload, image, workload, or resource allocation.

## Preserve two distinct cohorts

### A. Matched historical bridge

Reuse the exact saved 240 endpoint residuals and 120 admitted transition
pairs, including their variable order, conditioning, and source identities.
Pin the official feature-model repository at
`afa60ee2c836e7bdc4068e0f4f128ea31158d2ad`. Keep all 21 originally selected
transitions in the ledger; the joint-UNSAT Linux transition is a refusal,
not a missing row or an equivalent-model claim.

This is the 40-endpoint/seven-history cohort at k=8,12,16 with incidence and
hash slices. Preserve the actual historical DIMACS-ID incidence tie-break;
do not silently relabel it with the protocol's different name tie-break.
The independently regenerated joint witnesses are retrospective, not
recovered original process state. Hash every residual consumed by the rerun.

This cohort measures **conditioned** relations: outside features and
auxiliaries are fixed. It does not existentially project away those variables
or count whole-model original-feature configurations. Never call it either.

### B. Expanded workload coverage, separately reported

After the matched runner is validated, preregister a separate context/trace
selection file before timing. Include valid configuration sessions, invalid
and conflicting sessions, balanced point-query diagnostics, and source-level
edit neighborhoods which actually change assignments. Keep natural sampling
and deliberately balanced diagnostics in separate strata, with construction
costs and acceptance/refusal rates visible. Do not present a planted edit as
a naturally observed feature-model history.

Use a deterministic seed and a fixed candidate budget per source history.
Retain every sampled candidate, including zero deltas, trivial residuals,
unsatisfiable contexts, duplicates and rejections. Density/incidence/locality
may define preregistered bins, but timing outcomes must never choose the bins
or determine which cases are retained. Selecting a density bin with an
oracle is dataset preparation whose cost and conditioning must be disclosed.

Synthetic controls should vary one factor at a time: residual width,
solution density, duplicated substructure, edit locality and query reuse.
Include tautology, contradiction, parity, repeated clauses, highly shared
subexpressions, and no-sharing negative controls. Save generator source,
seed, canonical input and oracle output. Do not claim these are domain data.

## Equal-task result cells

| Cell | Cold starting point and required output | Reuse variant, reported separately |
| --- | --- | --- |
| Complete bounded vector | Recorded residual CNF plus order; exact LSB-first binary vector of 2^k bits. Charge all arm-specific preparation, ordering and extraction. | Resident compiled structure with scratch/first-touch work explicitly complete; recompute the vector. Cached-answer retrieval is a third, separately named task. |
| Partial configuration | Same residual and fixed trace; exact SAT/UNSAT for every recorded assumption set. Charge preparation plus the complete session. | Resident representation; same 64-query trace at each of the 25%, 50%, 75% fixed-variable levels, replayed without retaining previous trace answers. |
| Exact count | Same residual and variable universe; exact integer count. Charge compilation/process setup plus counting. | Resident structure or materialized vector, named distinctly. Cold d4 and warm vector popcount are never a speedup pair. |
| Version delta | Both named residuals and alignment; exact full XOR vector and changed-assignment count. | A later-version build from an earlier resident structure, versus a matched fresh later-version build; also compare warm XOR on two already resident outputs. |

Point queries, witness extraction, conflict explanations and complete
enumeration each need their own output contract. An arbitrary witness is
checked against the residual; different valid witnesses are not an exactness
failure. An UNSAT answer is not a minimal conflict explanation. A count or
symbolic graph is not a complete materialized output vector.

For version deltas report both the marginal cost of the later version and
the total cost of the earlier-plus-later session. A shared pool's creation
and retained memory do not disappear from the lifetime accounting.

## Arms and enforceable phase boundaries

Use CM flat, direct CNF BitSet, structural CSE-flat, native CUDD ROBDD with
fixed order, explicitly configured native CUDD reordering, incremental
CaDiCaL, and pinned d4 counting/d-DNNF where each task is supported. CUDD ZDD
is an explicit unavailable/refused cell until a real native binding and
set-family semantics are verified; a BDD or home-built ZDD must not be
relabeled CUDD ZDD. Unsupported output tasks remain visible as refusals.

1. Record common source parsing/conditioning separately. The primary cold
   task starts from the same canonical residual. Also report a whole-session
   total including common input preparation, without adding it twice.
2. CM cold work includes expression/IR construction, lowering, binding,
   masks/word plan, scratch allocation, and first execution. If the API fuses
   phases, report a fused total rather than invented separate timings.
3. For fixed-order CUDD, disable automatic reordering before node creation;
   assert the setting and retain counters/order before and after the case.
   Do not infer execution history from a final identity order alone.
4. For reordered CUDD, explicitly record the method the pinned binding
   actually invokes, its configuration, search cost, counters and final
   order. Do not name group sifting ordinary sifting. Serialize the actual
   measured graph, not the fixed-order graph or a later rerun of reordering.
5. Charge CUDD manager creation/declarations, d4 process launch/parse/solve,
   and any graph-to-vector conversion to the task that requires them. d4
   process invocation and resident d-DNNF evaluation are distinct arms.
6. For incremental SAT, retain the full assumptions/selector trace. Reusing
   learned clauses is an explicit session state. A fresh-session comparison
   rebuilds the solver, including the same base clauses, for each session.
7. Correctness/oracle preparation must not warm the objects later called
   cold. Validate in a separate process, then create new timed objects in
   new processes and verify their returned outputs outside the timer.

## Serialization, memory and process isolation

For every serializable arm retain native structure, canonical compact
encoding bytes, variable universe/order, original-name mapping, and optional
cached answer as separately sized components. Include dependency/image
requirements separately. Internal counters and independently parsed
serialized node/arc counts are different metrics.

Reload is a fresh process: read bytes, construct the manager/runtime,
deserialize the actual structure, and perform the first required query.
Remove the cached output from a structural CM reload fixture. A deliberately
corrupted cached answer must not make structural replay return that answer.
Report file-read, structural reconstruction and first-query phases where
observable; include their total. Label OS file-cache state as uncontrolled
unless genuinely controlled. Do not call this a disk-cold measurement merely
because the process is new.

Measure each arm for the **same task** in its own process tree. Record OS
process high-water memory, baseline memory at a declared point, and sampled
RSS (if used) as separately named quantities. High-water-minus-baseline is a
diagnostic increment, not exact representation memory. Include d4 child
processes and retained shared pools; do not compare parent-only memory to
whole-process-tree memory. Record sampling interval, units and platform API.
Python tracemalloc is a separate Python-allocation metric, never a substitute
for native CUDD/d4 RSS. Record timeout and memory-limit enforcement.

The controller should record process startup/end-to-end latency separately
from the inner cold task. Pin thread counts and record CPU model, available
RAM, OS, container digest, dependency/binary versions, affinity settings and
observed background load. Do not stop unrelated user workloads. If the host
is contended, label it or defer performance claims; correctness can still run.

## Scheduling, failures and immutable evidence

- Freeze an explicit non-secret source/test/dependency allowlist and the
  runner before timing; use the existing source-snapshot helper as a starting
  point, then verify hashes before and after execution. Record HEAD and dirty
  status, but exact loaded bytes are the identity. Execute from the snapshot,
  not the shared checkout another task is changing.
- Create a new run directory exclusively. Retain the run plan, exact command,
  source and input hashes, backend identities, seed, and a complete scheduled
  case/arm/task ledger before starting workers. Never rewrite the old runs.
- Use fresh processes for cold replicates. For each warm comparison group
  with m arms, use 2m timed rounds with recorded cyclic rotations and their
  reversals, so each arm appears equally often in every position. Preserve
  all samples and the schedule; do not report just the best ordering/round.
  Timer-resolution checks and batches must be set before inspecting winners.
- For genuinely warm repeated kernels, calibrate batch size in an explicitly
  excluded pilot and retain its results. Fresh sessions/cold starts cannot
  be batched into a loop that accidentally reuses construction or answers.
- Start each cell with an incremental `running` record and finish it with
  `ok`, `refused`, `timeout`, `memory_limit`, `mismatch`, or `error`, plus reason
  and elapsed time. A crashed controller leaves visible unfinished cells;
  resumptions use a new attempt identity. Bound stderr/evidence sizes.
- Fault-injection tests must exercise timeout, nonzero exit, malformed/missing
  output, memory refusal, corruption and controller interruption. A failed
  cell cannot become a zero time, vanish from the denominator, or prevent
  evidence for all other completed cells from being retained.

## Independent checks and publication gate

Use the separate scalar CNF, CM-instruction, ROBDD and d-DNNF interpreters in
`independence_audit_2026_08_27/artifact_audit.py` as the saved-relation oracle
layer. Extend strict format readers/tests if the new serializers change.
Replay both fixed and actually reordered graphs, then recompute all counts,
partial-context answers and XOR results from the canonical relation.

Before a real timing pilot, the runner must pass these contract controls:

| Control | Required observation | Gap addressed |
| --- | --- | --- |
| Fresh cold objects after oracle work | First lowering/binding/materialization belongs to cold total | M01, M09 |
| Matched fresh/shared transition fixtures | Both marginal and lifetime outputs/times have equal obligations | M02, M09 |
| Count temperature sentinel | Cold CLI count cannot be grouped with warm popcount | M03 |
| Cached-answer corruption and fresh reload | Instruction replay remains correct; first-query/manager cost included | M04 |
| Component size and structural-counter check | Payload/cache/metadata and internal/serialized nodes remain distinct | M05 |
| Same-task memory fixture with child process | Native child high-water accounting and baseline labels retained | M06 |
| Fixed-order assertions and saved reordered graph | Configuration/counters/order retained; both graphs independently replay | M07, M08 |
| Unequal-history and duplicate fixtures | Equal-history summaries and leave-one-history-out sensitivity work | M10 |
| Source mutation during preparation/run | Refuse inconsistent preparation; executed snapshot identity retained | M11 |
| Unchanged, UNSAT, sparse and dense controls | No silent filtering or whole-model/projection claim | M12 |
| Fault-injected timeout/error/interruption | Every scheduled cell and attempt remains in the ledger | M13 |

Aggregate only comparable task, temperature, output and state contracts.
Report paired per-case ratios, per-history summaries, equal-history
aggregates, descriptive history-cluster intervals, and leave-one-history-out
sensitivity. Keep timeout/refusal/coverage counts beside every summary.
Seven selected histories do not justify population-wide confidence claims.
Do not turn single digits or noisy microsecond differences into a winner.

Break-even queries use full preparation and session costs. If a retained
method has no lower marginal cost, mark it never-break-even for that pair.
If slopes or one-time costs are too noisy, mark it unresolved. Memory and
output completeness constraints still apply even when a time crossover exists.

Only after these checks pass should the website link a **new**, immutable
run and describe exactly which M01-M13 gaps it addresses. Do not relabel or
replace the old timing series. Independent implementation replay is not
external replication: publish the non-secret runnable bundle and instructions
so another person can reproduce it, then report any genuinely external run
as separate evidence with its own environment and attribution.

## Immediate implementation order

1. Repair the producer's phase/lifecycle hooks and add the contract controls
   above in a new runner, leaving shared core code and historical producers
   unchanged wherever possible. Coordinate overlapping edits with the other
   task before changing its files.
2. Freeze a tiny synthetic contract suite; run its functional/failure tests
   locally. This is runner validation, not performance evidence.
3. Select a deterministic small bridge pilot before timing; verify all
   serialized forms and actual native-backend availability. Record missing
   backends explicitly. Pin resource limits in that pilot's run plan.
4. Run the full historical bridge only after pilot acceptance and any
   necessary compute authorization. Then separately implement cohort B.
5. Update the existing evidence page from the new audited run, preserving
   historical qualifications and negative findings.

No step above has been represented as executed by this protocol document.
