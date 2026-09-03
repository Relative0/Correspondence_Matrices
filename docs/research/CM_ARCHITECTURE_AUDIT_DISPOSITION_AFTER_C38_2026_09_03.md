# CM architecture-audit disposition after C38

Date: 2026-09-03  
Scope: exact, non-neural CM and CM-family implementation  
Status: recommendations reconciled; corrected query-ladder follow-up frozen, locally verified, and awaiting authorization

## Bottom line

The comprehensive architecture prompt has been incorporated as an investigation and
decision checklist, not treated as authority to run every proposed experiment. The
current exact-backend work closes the high-value correctness and execution items that
were supported by measurements: shared-DAG memoization, zero-safe caches, topological
restricted evaluation, explicit q1/q4/q16/q64 comparisons, projection variants, native
fused slots, related-root union execution, exact fallback, and source-bound
cross-machine replication.

The remaining large ideas are not missing accidental TODOs. They are explicitly
deferred because the prerequisite profile or task contract is absent, an earlier exact
candidate missed its gate, or the present fixed native backend leaves no routing
headroom. This avoids combining speculative changes before their individual causal
value can be measured.

## H0-H10 disposition

| Hypothesis | Disposition | Evidence / reason |
|---|---|---|
| H0 current source truth | **Closed for the current checkpoint** | C34-C38 and the native portfolio have source/artifact manifests and independent replay. P7 W5 is now formally closed incomplete because three frozen inputs differ from current source. This commit is the new coherent source checkpoint. |
| H1 shared-DAG memoization | **Implemented and retained** | `eval_expr_bitset`, restricted R1, and CM-node packed evaluation memoize by object identity with zero-safe lookups. Shared/false-valued and low-sharing controls pass. The current direct BitSet path is now an explicit complete-relation arm. |
| H2 compact CM IR keys | **Deferred** | The dossier identifies possible structural-hash/key cost, but no current profile establishes it as a top cost after native fusion. A key redesign would affect canonicalization, interning, serialization, and cache identity and should not be mixed into the comparison freeze. |
| H3 dense CM layout/copy fusion | **Measured path retained; new rewrite deferred** | Dense CM is present in the eight-arm functional lane and matches the independent vector oracle. No caller-visible profile yet isolates one safe layout/copy change with a predeclared benefit; representation-specific memory calibration remains required. |
| H4 no-reinflation boundaries | **Implemented and retested; no promotion claim** | Full and reduced no-reinflation paths are exact and included where they return the same artifact. Historical results show wrapper/conversion overhead can erase the avoided dense rebuild, so it remains an arm rather than a universal default. |
| H5 prepared/reused break-even | **Corrected follow-up prepared** | C35/C36 and the q64 architecture run remain evidence for their declared contracts. The follow-up now schedules q1/q4/q16/q64 as separate cells across the same 54-case Lane-B cohort and eight arms. Local exact replay passed; no corrected Linux timing exists until separately authorized execution. |
| H6 representation-specific memory estimates | **Isolated measurement implemented; routing change deferred** | The follow-up runs each timed cell in a fresh Linux fork child, records child peak RSS from `wait4`, and subtracts the inherited `/proc/self/statm` baseline. This provides descriptive per-cell evidence after execution, but is not yet conservative cross-machine calibration for a default routing change. |
| H7 native/fused words | **Implemented, cross-machine exact, guarded** | C37 confirmed Windows/MSVC and C38 rebuilt on Linux/GCC. Aggregate single-root and multi-root gains transferred, but one Linux case was 0.840x and failed the 0.95x floor. Native stays opt-in with SHA/ABI checks and Python R2 fallback. |
| H8 parallel/streamed CM | **Deferred by activation gate** | Existing multiprocessing evidence is overhead-bound and the current target tasks do not require a sufficiently large streamed/live-tensor contract. No new compute is justified. |
| H9 incremental compilation across edits | **Open, lower priority** | Persistence and version-history contracts exist, but the audited project still lacks a realistic changed-version trace with measured changed-cone reuse and retained-memory accounting. This is a distinct future task, not part of the complete/restriction refresh. |
| H10 task-matched external controls | **Timed on one Linux host; correction prepared** | Retry 002 completed 19,646 verified rows with unlike artifacts kept separate. Direct BitSet led the complete-vector lane; native fused slots were mixed across restriction cohorts; shared multi-root union was consistently beneficial; natural CNF/CSE/SAT controls led smaller-task lanes. A source-frozen correction for separately timed q1/q4/q16/q64 cells and isolated memory is locally verified but not yet authorized; cross-machine replication remains required before a public update. |

## Accepted architecture changes

- direct expression evaluation is DAG-aware and its current result must be rerun rather
  than used only as an unchanged historical denominator;
- restricted R2 compiles DAG-v2 directly to a topological/liveness arena;
- CSE and CM bigint/word paths, projection, and native slots share one canonical
  residual-relation/count/SAT/witness output contract;
- native activation is disabled by default and fails closed to exact Python R2 on
  configuration, identity, ABI, compile, or runtime failure;
- sibling roots can use one union arena while preserving ordered per-root outputs;
- comparison arms clear cross-task input caches while retaining reuse inside the
  declared resident lifecycle;
- count, SAT, witness, equivalence, and persistence are separate lanes rather than
  being credited as complete-vector wins.

## Tested negatives and stopped branches

Multi-query concatenation/union-care batching, trace-specialized caching, full-screen
ANF, bounded-rank routing, and broad projection rewrites did not pass their continuation
gates in the tested formulations. A selector is also stopped: native won all 18 exposed
C36 portfolio cases, giving exactly 1.0000x per-case-oracle headroom. These results do
not prohibit different future tasks, but they do prohibit spending confirmation data or
training a router for the present q64 contract.

## Next controlled boundary

1. **Complete:** treat retry 002 as the completed, source-bound one-host result; retain
   every favorable, unfavorable, and refused cell.
2. **Complete in source:** Lane B now gives q1/q4/q16/q64 separate timing cells rather
   than only prefix correctness digests.
3. **Complete in source:** every decision-bearing cell now has an isolated-child memory
   contract; retry 002's process-wide `ru_maxrss` remains non-comparable.
4. **Frozen and locally verified; execution pending:** the corrected source closure and
   27,648-row schedule are immutable, and the exact one-Pod request requires fresh user
   authorization rather than reusing retry 002's authorization.
5. **Pending after that run:** replicate on a separate machine/compiler. Only then add task-labelled sections to
   `expert.html`; retain historical dates and the Windows-only 1.472x result rather than
   silently replacing it.

No corrected timing, break-even, or per-cell memory result is claimed at this boundary.
It is not a claim that every research idea was implemented, nor that further testing
can never expose another useful architecture.
