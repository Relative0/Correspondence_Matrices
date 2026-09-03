# CM architecture-audit disposition after C38

Date: 2026-09-03  
Scope: exact, non-neural CM and CM-family implementation  
Status: recommendations reconciled; accepted work implemented and tested, speculative work gated

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
| H5 prepared/reused break-even | **Implemented and measured** | C35, C36, the multi-query q1/q4/q16/q64 study, the seven-arm native portfolio, and the four-lane harness charge setup separately from resident queries and isolate process-global input caches. |
| H6 representation-specific memory estimates | **Partially complete; routing change deferred** | Native workspace is bounded and confirmed; experiment memory sessions record Python peaks/RSS. Dense, bigint, and projection peak calibration is not yet conservative enough to change default guards. |
| H7 native/fused words | **Implemented, cross-machine exact, guarded** | C37 confirmed Windows/MSVC and C38 rebuilt on Linux/GCC. Aggregate single-root and multi-root gains transferred, but one Linux case was 0.840x and failed the 0.95x floor. Native stays opt-in with SHA/ABI checks and Python R2 fallback. |
| H8 parallel/streamed CM | **Deferred by activation gate** | Existing multiprocessing evidence is overhead-bound and the current target tasks do not require a sufficiently large streamed/live-tensor contract. No new compute is justified. |
| H9 incremental compilation across edits | **Open, lower priority** | Persistence and version-history contracts exist, but the audited project still lacks a realistic changed-version trace with measured changed-cone reuse and retained-memory accounting. This is a distinct future task, not part of the complete/restriction refresh. |
| H10 task-matched external controls | **Functionally admitted; timed campaign pending** | Current complete-relation, restriction, multi-root, count/SAT/witness/equivalence, and persistence contracts keep unlike artifacts separate. C34/C35 already exercise BDD/SAT controls where outputs match. A new public comparison requires a fresh frozen corpus and separate authorization. |

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

1. Freeze a fresh current-source comparison corpus that includes the public regression
   cohort plus new tree-like/high-sharing cases without using method timings for
   selection.
2. Freeze balanced schedules, exact arm configurations, source closure, failure rules,
   memory fields, and publication gates.
3. Validate the package locally and prepare one exact RunPod authorization request.
4. Run no timed cloud campaign until that separate authorization is granted.
5. If verified timing is later obtained, add new task-labelled sections to
   `expert.html`; retain historical dates and the Windows-only 1.472x result rather than
   silently replacing it.

This is the safe stopping point for architecture implementation before the comparison
freeze. It is not a claim that every research idea was implemented, nor that further
testing can never expose another useful architecture.

