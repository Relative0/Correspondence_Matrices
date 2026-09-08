# Independent active CM workflow profile gate

Date: 2026-09-08  
Scope: exact, non-neural CM architecture on one provenance-independent active workflow  
Status: protocol drafted before decision-bearing timing or memory execution

## Source and binding dispositions

The source checkpoint is remote branch `origin/codex/cm-h2-h3-h6-gates-20260908`
at exact commit `43fffcfaa53aab0d2ce95ca902c11e8f23484dfe`. A 2026-09-08 fetch confirmed
that this commit is not an ancestor of `origin/main`, so the isolated worktree is
detached at the reviewed branch commit. The original checkout remains untouched.
Its pre-existing tracked and untracked paths are recorded by name only in
`CHECKPOINT.json`; no secret, credential, private-database, or unrelated file content
is read.

The September 3 architecture disposition and the September 4 hardware-corpus stop are
binding. The September 8 H2/H3 no-go and H6 estimator no-go are not reopened or
refitted. H6 fresh spawning is used only as memory-measurement infrastructure. H9,
Yosys, replacement repositories, incremental hardware work, selectors, native
activation, RunPod, production defaults, and public claims are outside this phase.

## Discovery and admission rule

Before any timing or memory result is opened, inventory maintained local candidates
using tracked source history, caller contracts, and original-checkout path metadata.
Admit exactly one workflow only if all of these are true:

1. its task and caller-visible artifact were committed for a non-benchmark purpose
   before this investigation;
2. current reviewed source contains the executable task and exact artifacts;
3. the task has explicit inputs, output ordering, semantics, and stable hashes;
4. repeated real call sites or an explicit reuse lifecycle exist;
5. an oracle independent of the CM implementation exists; and
6. selection does not use CM timing, memory, key shape, dense-layout favorability,
   native eligibility, or a stopped-panel outcome.

The admitted task is the deep-series chapter compiler's `truth_layout_payload`
subworkflow. It produces the exact expression/matrix data embedded in executable
render contracts. The discovery artifact freezes every tracked chapter/scene call
whose primitive actually invokes that function, including calls that retain the full
payload and calls that take only its matrix. The independent oracle is the already
caller-visible render-contract data plus a separate standard-library Boolean replay.

Benchmark campaigns and the remote benchmark worker are excluded because they were
created to measure CM; the learning handoff is excluded because it does not execute a
CM representation; the stopped hardware and revision panels are excluded by binding
disposition. No public or generated replacement workload is allowed.

## Frozen task and arms

The occurrence list, source paths and hashes, video/chapter/scene identities, primitive,
exact artifact, ordering, and oracle hash are copied into `FREEZE.json`. The two source
expressions are `(A AND B) XOR (C OR D)` and `(A AND B) XOR C` in fixed ambient order
`A,B,C,D`, rows `AB=00,01,10,11`, and columns `CD=00,01,10,11`.

Exactly one unchanged-current-source arm is measured: deserialize the frozen DAG-v2
expression, compile canonical CM-IR with current defaults explicitly disabled for
persistent/reuse cache, establish the fixed layout, materialize the dense CM, convert
it to the caller's row-major bit string, deliver the exact caller-retained payload, and
canonically serialize it. The source compiler's scalar Boolean construction is the
independent oracle, not a timed competitor.

Cold lifecycle starts at DAG-v2 deserialization and includes construction, canonical
keys/hashing/interning, layout, dense lifting/allocation/copies, conversion, delivery,
and serialization. Reused lifecycle retains parsed expression, compiled CM-IR, and
layout but rebuilds and serializes every required output; output caching is forbidden.
There are two warmups and seven uninstrumented repetitions per occurrence/lifecycle.
All failures, refusals, zero-duration stages, and unfavorable rows are retained.

Attribution is a separate one-shot `cProfile` pass using the unchanged September 8
mutually exclusive categories: key creation/order preparation, hashing, interning,
serialization, dense lifting/alignment, allocation, conversion, and temporary copies.
Profile time is never substituted for caller-visible time.

Fresh-process memory uses three spawned interpreters for every distinct
primitive/expression/lifecycle task. Imports occur before the common baseline. Cold
execution reconstructs each real occurrence; reused execution records a separate
prepared-state boundary and reuses that state while rebuilding outputs. The external
controller samples Windows working set/private usage and process peaks every 1 ms;
the child reports matching `tracemalloc` current/peak endpoints. Signed prepared,
retained, and post-release deltas and nonnegative peaks are all preserved.

## Correctness, validity, and controls

Every result must equal the frozen caller artifact, retain exact row/column and ambient
ordering, and preserve stable output and structure hashes. Validation includes all
Boolean functions through three variables, the two admitted functions over all 16
ambient assignments, identity-shared versus tree-expanded metamorphics, commutative
ordering, low-sharing controls, cold/reused agreement, and the maintained exact suite.
The independent verifier replays oracle construction and the complete summary with the
standard library and does not call the profiling summarizer.

Measurement is valid only with complete schedules, seven timing repetitions, three
distinct fresh child PIDs per memory cell, complete handshakes, at least one execution
sample, exact oracle agreement, stable hashes/order, internally ordered absolute
memory endpoints, signed retained fields, intact source closure, and zero independent
replay mismatches.

## Materiality, prevalence, and continuation

H2 applies only to cold calls. H3 applies to cold and reused dense calls. A component
passes only if all frozen conditions hold:

- at least six applicable exact cells;
- at least 15% aggregate exclusive profile share;
- at least 10% median per-cell share;
- at least 50 microseconds median exclusive component time;
- at least 50% of cells individually reach 10%;
- both the main four-live-variable and ambient-variable-control cohorts reach 10%
  aggregate share; and
- allocation/copy components also show a valid fresh-process median task peak at least
  25% above required retained output bytes.

If no component passes, close with no implementation candidate. If more than one passes,
close because the instruction permits a candidate only when exactly one component is
eligible. If exactly one passes, freeze one small reversible research-only candidate
against unchanged current source before implementing it. It must preserve every oracle,
order/hash, and structural signature; improve targeted caller-visible geomean by at
least 3% and the targeted component by at least 5%; regress no applicable call by more
than 5%, no low-sharing control by more than 3%, and no retained or peak memory endpoint
by more than 5%.

A RunPod authorization request may be prepared only after valid local measurement,
exactly one material component, a passing separately frozen candidate, every regression
floor, focused and maintained tests, and independent replay all pass. Preparation would
not itself authorize RunPod.
