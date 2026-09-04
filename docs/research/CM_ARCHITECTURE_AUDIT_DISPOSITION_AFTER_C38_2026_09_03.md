# CM architecture-audit disposition after C38

Date: 2026-09-03  
Updated: 2026-09-04
Scope: exact, non-neural CM and CM-family implementation  
Status: recommendations reconciled; query-ladder verified across separate host/compiler pairs; public task map prepared

## Bottom line

The comprehensive architecture prompt has been incorporated as an investigation and
decision checklist, not treated as authority to run every proposed experiment. The
current exact-backend work closes the high-value correctness and execution items that
were supported by measurements: shared-DAG memoization, zero-safe caches, topological
restricted evaluation, explicit q1/q4/q16/q64 comparisons, projection variants, native
fused slots, related-root union execution, exact fallback, and source-bound
cross-machine replication. The public expert page now adds a task-labelled architecture
map while retaining the historical Windows/MSVC 1.472x headline and its original scope.

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
| H5 prepared/reused break-even | **Four-point separate-host ladder complete** | Both exact 27,648-cell runs verified q1/q4/q16/q64. R2 led q1/q4 on both hosts; q16 straddled the CSE-flat/R2 threshold; CSE-flat led q64 on both. Native crossed R2 only by aggregate point estimate at q64 and failed its minimum floor on both. This is an observed sampled ladder, not an interpolated universal threshold. |
| H6 representation-specific memory estimates | **Isolated measurement verified; routing change deferred** | Every retry cell ran in a fresh Linux fork child with peak RSS from `wait4`, an inherited `/proc/self/statm` baseline, and full isolation lifecycle reported separately. Child peak was below the inherited baseline in all 27,648 rows, making every nonnegative incremental value zero; absolute host peak data are descriptive and cannot calibrate a default memory router. |
| H7 native/fused words | **Implemented, cross-machine exact, guarded** | C37 confirmed Windows/MSVC and C38 rebuilt on Linux/GCC. Aggregate single-root and multi-root gains transferred, but one Linux case was 0.840x and failed the 0.95x floor. Native stays opt-in with SHA/ABI checks and Python R2 fallback. |
| H8 parallel/streamed CM | **Deferred by activation gate** | Existing multiprocessing evidence is overhead-bound and the current target tasks do not require a sufficiently large streamed/live-tensor contract. No new compute is justified. |
| H9 incremental compilation across edits | **Three local traces tested; none promoted** | The 120-case feature-model prototype lost to the existing persistent cache and CSE-flat, with only three activated confirmation cases. A first 48-transition hardware audit failed activation/coverage. A corrected behavior-change selector then screened 214 commits and replayed exactly: BlackParrot supplied 12 active/reusable transitions, but the second frozen confirmation project exhausted 42 commits with zero qualifying transitions. The corpus stops before Yosys, timing, or RunPod. |
| H10 task-matched external controls | **Timed, replicated, and scoped for public presentation** | The broad comparison's 19,646 verified rows kept unlike artifacts separate: direct BitSet led the complete-vector lane, shared multi-root union was consistently beneficial, and natural CNF/CSE/SAT controls led smaller tasks. Two corrected 27,648-cell Lane-B runs then showed R2 at q1/q4, a host-sensitive q16 boundary, robust CSE-flat q64 advantage, and a mixed native cohort result. The expert page presents these as task-specific results rather than a universal ranking. |

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
gates in the tested formulations. A selector remains stopped. Native won all 18 observed
C36 cases at q64 (1.328x geomean) but only 18 of 36 fresh cases (0.933x geomean), while
CSE-flat bigint won all 54 cases. These results do not prohibit different future tasks,
but they do prohibit training a router from this confirmation result.

## Next controlled boundary

1. **Complete:** corrected retry 002 is a source-bound one-host result retaining every
   favorable and unfavorable cell; all 27,648 cells passed exact verification.
2. **Complete:** Lane B gives q1/q4/q16/q64 separate timing cells rather than only prefix
   correctness digests.
3. **Complete for descriptive host data:** every decision-bearing cell has isolated-child
   RSS and lifecycle fields. The zero-floored incremental field cannot fit a memory router.
4. **Complete:** attempt 001 is closed incomplete, its 83% inherited-heap collection
   artifact is diagnosed, and corrected retry cleanup is only 0.23% of task time.
5. **Complete:** the frozen ladder replicated on a separate RunPod flavor, AMD EPYC
   9575F CPU model, and pinned Clang 14 compiler. All 27,648 cells passed, the local
   verifier reproduced the remote verification byte-for-byte, and final inventories
   were empty.
6. **Complete in the publication source:** task-labelled `expert.html` sections retain
   historical dates and the Windows-only 1.472x result rather than silently replacing
   it. Focused website checks passed. External deployment remains the effect of pushing
   the reviewed branch to `origin/main`.

The first H9 local gate stopped its digest-radix prototype, and the first hardware
feasibility audit stopped on activation/coverage. The corrected
[behavior-change corpus audit](CM_HARDWARE_BEHAVIOR_CHANGE_CORPUS_RESULT_2026_09_04.md)
then admitted and replayed BlackParrot strongly but stopped because the second frozen
confirmation history supplied zero qualifying transitions. H9 is deferred until a
genuinely independent active revision history or real workflow is identified before a
new freeze; repository replacement after observing this result is not admissible.
H2/H3 layout work remains gated on an admitted workload producing a profile that
identifies key construction or dense copying as a material cost.

The corrected result permits an observed four-point separate-host portability map and
descriptive host-memory reporting. It is not a universal break-even claim, a selector or
neural result, a routing change, or a claim that every research idea was implemented.
