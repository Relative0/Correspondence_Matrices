# Architecture-aware CM comparison refresh after C37

Date: 2026-09-03  
Scope: exact, non-neural CM-family benchmarking and public evidence  
Status: current-source Linux comparison executed; corrected q-ladder attempt 001 closed incomplete

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
Linux/GCC comparison have now completed. No public-site update has occurred. The verified
result is recorded in
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

Two measurement limitations block a public refresh. Lane B timed only the complete q64
trace; q1/q4/q16 were correctness digests of prefixes, not separately timed cells, so no
break-even ladder may be claimed from retry 002. Per-row RSS came from process-wide
`ru_maxrss`, so that run cannot support per-arm memory routing. A corrected follow-up is
now implemented, source-frozen, and locally replayed: q1/q4/q16/q64 are 27,648 distinct
timed cells, and every decision-bearing cell uses a fresh Linux child with peak RSS
collected by `wait4` and an inherited `/proc/self/statm` baseline. This is preparation,
not timing evidence; the exact RunPod request still requires fresh authorization. A
later separate-machine/compiler replication remains required for publication.

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
6. **Attempt 001 incomplete; retry correction in source:** Lane B gives q1/q4/q16/q64
   separate timed contracts and uses isolated-child `wait4` peak RSS with a pre-fork
   inherited baseline. The exact run safely closed after 11,744/27,648 rows at the
   420-second bound, with no decision-bearing result. Diagnostic stage totals showed
   that per-child `gc.collect()` spent 83% of accounted time scanning the inherited
   parent heap. The corrected source charges explicit cache clearing, delegates the
   remaining cell heap to child exit, and reports isolation lifecycle time separately.
   It requires a new freeze and fresh exact authorization.
7. **Pending:** replicate the corrected current-source comparison on a separate machine/compiler.
8. **Pending after those gates:** update `expert.html` with scoped current sections, retain historical
   results and dates, run generated-site consistency tests, and publish only under separate authorization.

This sequence highlights where a CM or CM-family architecture is useful without turning
a workload-specific advantage into a general claim.
