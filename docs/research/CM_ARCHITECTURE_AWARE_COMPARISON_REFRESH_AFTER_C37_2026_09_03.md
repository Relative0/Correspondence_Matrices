# Architecture-aware CM comparison refresh after C37

Date: 2026-09-03  
Updated: 2026-09-04
Scope: exact, non-neural CM-family benchmarking and public evidence  
Status: corrected q-ladder verified across Linux/GCC and Linux/Clang; public task map prepared

## Current implementation status

The local functional-admission step is complete. The source now has a deterministic
four-lane harness covering all eight complete-relation paths, q1/q4/q16/q64 repeated
restrictions, sharing-aware and separate Python/native multi-root paths, and separate
count/SAT/witness/equivalence/persistence contracts. Its retained independent replay
reproduced the result byte-for-byte with zero exactness mismatch and deliberately used a
deterministic non-timing clock. The generic complete-relation smoke adapter also now
admits the current identity-memoized direct expression BitSet arm, so future source-closed
timing plans cannot silently omit that changed denominator.

P7 W5 is separately closed as an incomplete historical campaign. Its successful IR-A
shard remains source-bound historical evidence, while IR-B and both relation shards are
permanently unrun because the frozen package differs from current source in
`bitset_backend.py`, `cm_exprlib.py`, and `cmbench/comparative/contracts.py`. No combined
W5 conclusion is permitted and no old authorization may be reused.

The fresh corpus/schedule/arm/gate freeze and the separately authorized current-source
Linux/GCC comparison have now completed. The expert page now includes the resulting
task-labelled comparison map without replacing the historical Windows/MSVC headline.
The verified result is recorded in
`docs/recognition/architecture_comparison_execution_retry_20260903/VERIFIED_INTERPRETATION.md`.

## C38 result

The authorized Linux/GCC execution completed on 2026-09-03 and was deleted after
93.754 seconds of billed lifetime at an estimated compute cost of $0.001563. Both the
controller cleanup and a separate post-run inventory query found no remaining Pod.
The two independent verifiers replayed 954 sessions, 44,928 single-root queries, and
48,384 multi-root output queries with zero semantic, artifact, source, native-library,
binding, structure, summary, or decision mismatches.

The portable performance result is deliberately mixed:

- native fused single-root execution was 1.366x faster in aggregate than Python R2,
  but its minimum case was 0.840x, below the frozen 0.95x floor;
- all width aggregates remained above 1.0x and the p95 session speedup was 1.714x;
- native multi-root union execution was 1.260x faster than separate native roots, its
  minimum workload was 1.224x, and every multi-root gate passed;
- the Windows measurements remain 1.472x single-root and 1.285x multi-root, but those
  figures must remain identified as Windows/MSVC results rather than cross-platform
  constants.

Therefore C38 confirms the Linux/GCC implementation, exactness, and aggregate/multi-root
benefit. It does not confirm unconditional single-root performance. The native backend
remains guarded/opt-in; the comparison refresh must retain the individual Linux
regression and must not refit the frozen gate after seeing it.

## Current-source architecture comparison result

Retry 002 completed all 19,646 scheduled rows on the single authorized Secure CPU Pod.
The independent verifier found zero semantic, schedule, source, or artifact mismatches;
the Pod was deleted and both final inventories were empty. Estimated compute cost was
$0.003092.

The task-matched result is also mixed:

- for complete explicit relations, `cm_ir_recursive_packed` was 1.053x faster than dense
  CM but achieved only 0.930x against the current identity-memoized direct BitSet; BitSet
  won all 78 runnable case clusters;
- for 64 repeated restrictions, native fused slots were 1.055x over Python R2 overall
  and 1.179x on the 18 observed C36 cases, but only 0.997x on 36 fresh cases; the minimum
  case was 0.812x and failed the frozen 0.95 floor, so native remains guarded/opt-in;
- related-root union execution was consistently beneficial: 1.147x over separate Python
  roots and 1.238x over separate native roots across all 12 case clusters;
- the smaller count/SAT/witness/equivalence/persistence lanes favored their natural
  CNF/CSE/SAT controls rather than CM as a universal fixed backend.

Those two measurement limitations were corrected by the later architecture query-ladder
retry 002. It completed 27,648 distinct q1/q4/q16/q64 cells and independently verified
the isolated-child `wait4` RSS and pre-fork baseline fields. This supplies a one-host
setup-amortization curve, but not calibrated memory routing: the child peak was
below the inherited baseline—all 27,648 incremental values were zero. The later
separate physical-machine/compiler replication is now complete. The public source and
focused website checks are complete; deployment remains tied to an authorized push of
the reviewed branch.

## Corrected query-ladder result

The corrected retry completed all 27,648 scheduled cells, with 6,912 rows at each query
count and zero semantic, schedule, source/artifact, or memory-field mismatches. Estimated
retry cost was $0.002649; combined estimated cost with the incomplete attempt was
$0.011583. The Pod was deleted, and controller plus independent post-run inventories
were empty.

Python R2 was the best fixed arm at q1 and q4. CSE-flat bigint became the best fixed arm
at q16 and q64; at q64 it delivered a 1.100x case-cluster geomean over R2, won all 54
cases, and had a 1.031x minimum. Native fused slots first exceeded R2 at q64 by point
estimate (1.049x), but its 95% case-cluster interval was 0.969x–1.139x and its 0.567x
minimum failed the frozen 0.95 floor. Native was strong on the 18 observed C36 cases
(1.328x) and slower overall on the 36 fresh cases (0.933x). These data do not support a universal
native-default claim and do not authorize selector fitting. They also reinforce why
CSE-flat and other current controls must be rerun rather than left as historical fixed
denominators.

## Cross-machine query-ladder result

The exact ladder then completed on a different RunPod flavor, CPU model, and compiler:
`cpu5c`, AMD EPYC 9575F, and Debian Clang 14 instead of `cpu3c`, EPYC 9655, and GCC 12.
All 27,648 cells passed independent verification, and a local verifier reproduced the
verification byte-for-byte. The Pod was deleted; controller and later independent
inventories were empty. Estimated replication cost was $0.002916.

The fixed-arm map agreed at three of four query counts. R2 led q1/q4 on both hosts;
CSE-flat bigint led q64 on both. At q16, CSE-flat changed from 1.004x under GCC to
0.995x under Clang, which is a threshold-straddling sample rather than a portable
break-even claim. At q64, CSE-flat changed only from 1.100x to 1.090x, won every case on
both hosts, and retained minimums above 1.0. Native changed from 1.049x to 1.026x but
again failed the 0.95 minimum floor (0.567x and 0.549x); its observed cohort remained
favorable and fresh cohort unfavorable. The portable result is therefore task-specific
and favors CSE-flat for this q64 explicit-residual contract, not a universal native
default.

## Decision

Current public CM/BitSet/CSE-flat/CUDD figures remain valid historical records of their
frozen campaigns, but they are not assumed to describe the current working tree. Any
current headline or benefit claim must come from a task-matched rerun in which every
applicable arm is built from the same source freeze and returns the same required
artifact.

C37 does not supply that rerun. It supplies a new repeated-restriction and sibling-root
execution result. C38 first tests whether that result survives a Linux/GCC rebuild on a
second machine. The broader comparison refresh begins only after C38, under a separate
freeze and authorization.

## Architecture changes that can move comparative results

| Change | Methods potentially affected | Applicable task | Publication treatment |
|---|---|---|---|
| Identity memoization in direct expression BitSet evaluation | BitSet/direct AST, especially shared DAGs | Complete vector and repeated evaluation | Rerun BitSet; do not reuse an older BitSet denominator |
| Zero-safe identity memoization in CM-node packed evaluation | CM packed evaluators on shared false-valued subgraphs | Complete vector and restrictions | Rerun affected CM arms; preserve old result as historical |
| R2 topological/liveness restricted evaluator | CM-family resident restriction | Repeated partial contexts | New task-specific arm; not a full-materialization replacement |
| Confirmed bigint preference over NumPy words at residual widths 6, 8, and 10 | CM IR and CSE-flat execution | Repeated restrictions | Keep the current conservative selector; report both as ablation controls |
| Native fused C11 slots | Prepared CM-family/Boolean-DAG execution | Repeated partial contexts | Add only after cross-machine confirmation; charge compilation and binding |
| Native multi-root union arena | Related/sibling CM-family outputs | Repeated multi-output contexts | Separate multi-root result; compare with separate-root evaluation |
| Failed batch, trace-specialized, full-screen ANF, and bounded-rank candidates | Development-only arms | Their original narrow tasks | Preserve as negative evidence; do not place in a fastest-current pipeline |

The first two changes can benefit opposing sides of an older chart. Therefore even a
seemingly CM-only repair is not grounds for changing only the CM numerator, and a
BitSet improvement is not grounds for changing only its denominator.

## Required refresh lanes

### A. Complete explicit relation

Required artifact: the exact complete truth vector in one declared variable order,
plus digest and output byte count.

Required same-language arms:

- CM dense/full reinflation;
- CM packed bigint;
- CM packed words;
- CM hybrid no-reinflation, only when it still delivers the complete required vector;
- current ordered CM IR followed by the applicable evaluator;
- structural-CSE flat;
- raw flat;
- direct expression BitSet with current identity memoization.

Native CUDD may be included only when construction, any reordering, and complete-vector
extraction are all charged. SymPy remains a correctness oracle rather than a timed
headline competitor. Espresso remains outside this lane because a minimized cover is
not the required vector.

This lane is the one that can revise existing complete-vector CM/BitSet and CM/CSE-flat
figures. It must include the existing public corpus as an explicitly observed regression
cohort and a fresh, frozen structural cohort with both tree-like and high-sharing DAGs.

### B. Repeated exact restrictions

Required artifact per restriction: explicit residual relation, exact count, SAT flag,
canonical witness, and digest. Preparation is reported separately and also amortized
over a prespecified query-count ladder.

Required arms:

- Python R2 topological/liveness;
- CM IR bigint and CM IR words;
- CSE-flat bigint and CSE-flat words;
- current projection control;
- native fused slots, if C38 exact verification passes;
- direct BitSet restriction only if it returns the identical residual artifact.

Query counts should include at least q1, q4, q16, and q64. The C37 q64 cohort remains a
prospective portability/confirmation cohort, not data for choosing a selector.

Native CUDD restrict/cofactor and CaDiCaL assumptions belong only in separately declared
subtasks where their delivered result matches. SAT-only or count-only answers cannot be
ranked as if they had returned an explicit residual relation.

### C. Related multi-root outputs

Required artifact: the ordered explicit result for every declared root under every
restriction, with per-root counts, SAT flags, witnesses, and digests.

Required arms:

- one native union arena;
- separate native root arenas;
- one sharing-aware CSE/CM union control;
- separate sharing-aware CSE/CM roots.

The public result should show both time and structural reuse: unique nodes, avoided
duplicate nodes, workspace, preparation, execution, and delivery.

### D. Smaller-query benefits

Count, SAT, witness, equivalence, and persistence are separate lanes. Their strongest
natural controls are respectively model counters/CUDD, SAT solvers, SAT/BDD witness
paths, SAT miters/BDD comparison, and comparable serialized compiled artifacts. A CM
vector may be a bounded diagnostic arm but is not presented as the natural universal
method for a smaller query.

## Measurement and public-claim rules

Every timed cell records parse/normalization, representation construction, compilation,
binding, evaluation, extraction/delivery, serialization where required, cleanup, output
bytes, peak RSS, retained bytes, source hashes, compiler/interpreter identities, and
failure/refusal status. Complete-task caches are cleared between arms; reuse inside a
declared resident task is preserved and charged honestly.

Public presentation should lead with a task map rather than a single universal ratio:

- **complete relation:** fastest current CM-family arm versus current BitSet/CSE-flat and
  fully extracted symbolic controls;
- **repeated restrictions:** setup cost, break-even query count, q64 throughput, tails,
  and exact output contract;
- **related outputs:** benefit from cross-root sharing;
- **count/SAT/witness:** only task-matched comparisons;
- **limits:** widths, corpus composition, platform/compiler, memory/refusals, and any
  individual regressions.

An older number is superseded only by a source-hash-closed rerun of the same contract.
A new contract receives a new section. Both favorable and unfavorable cells remain in
the evidence and denominator.

## Execution order

1. **Complete:** C38 Linux/GCC rebuild and exact C37 replication.
2. **Complete:** because exactness passed, retain the native backend as guarded/opt-in regardless of whether
   the performance gate passes; its performance claim depends on the observed outcome.
3. **Complete:** implement and locally validate the four-lane comparison harness using current source
   on observed development/regression cohorts.
4. **Complete:** freeze a fresh comparison corpus, schedules, arm configurations, and publication
   gates before timing it.
5. **Complete:** obtain a separate exact authorization and execute the current-source Linux/GCC
   comparison; retry 002 completed and was independently verified.
6. **Complete on one Linux/GCC host:** after attempt 001 safely closed incomplete, the
   corrected retry completed all 27,648 separately timed q1/q4/q16/q64 cells. It uses
   isolated-child `wait4` peak RSS with a pre-fork inherited baseline, charges explicit
   cache clearing, delegates remaining heap release to child exit, and reports full
   isolation lifecycle separately. Independent verification found zero mismatches.
7. **Complete:** the exact 27,648-cell ladder replicated on a different RunPod flavor,
   CPU model, and compiler with zero verification mismatches and empty final inventories.
8. **Complete in source and locally verified:** `expert.html` has scoped current sections,
   retains historical results and dates, and passes the focused generated-site checks.
   External publication remains controlled by the authorized `origin/main` push.

The comparison refresh does not authorize another generic timing sweep. Its first
incremental-compilation successor is now complete: 3,000 source-closed local rows were
exact, but the digest-radix prototype was slower than the current persistent cache,
retained more Python-owned memory, remained behind CSE-flat through q64, and saw
normalized changes in only three of 42 confirmation cases. It is stopped without a
RunPod follow-up. Compact-key and dense-layout changes stay deferred until a better-
activated real revision workload identifies either cost as material.

This sequence highlights where a CM or CM-family architecture is useful without turning
a workload-specific advantage into a general claim.
