# Frozen diagnostic plan — 2026-09-15

## Scope and provenance

Study implementation: detached clean worktree `tmp/cm-time-attribution-20260915`,
base `e334de594262059cc18cf37eaab56b0f79e94843`. No production implementation,
routing, defaults, existing evidence, dirty root, or consolidation worktree edits.
All additions live in this audit directory. No commits, pushes, cloud jobs,
optional dependency installation, confirmation inputs, or scientific promotion.
This plan is frozen before adding diagnostic instrumentation or timing cases.
Requested predecessor files absent at this commit are read from the original
root as separately hashed evidence, never imported into the measured baseline.

## Read-only audit finding before measurement

`eval_expr_bitset` already memoizes by identity. Raw recursion is therefore an
explicit diagnostic ablation. `raw_ast_flat` in engine selection still uses
tree-occurrence lowering; structural CSE requires `compile_expr_cse` explicitly.
`ir_compile_time_s` is a parent span, not a summand beside its child timers;
persistent-cache structural UID preparation lies outside that compile timer.
Family total includes conversion/verification that variant compile/eval spans
omit; the outer family wrapper also constructs references and family diagnostics.
Y02–Y05 task totals include several output verification/delivery steps despite
the worker docstring; caller totals include process/import/transport overhead.
Frozen q64 prefix hashes do not constitute separately measured q1 timings.

## Cases (development only)

Use existing unit-test fixtures and exposed development records, not new unseen
seeds or corpus cases. Primary packed ladder:

1. `tests/test_bitset_cse.py::_random_expr`, seeds 0 and 1, n=8, steps=20;
   existing n=3,8,12,16 seed=1000+n/steps=24 cases for observed scaling.
2. Exact shared-subtree and separately allocated equal-subtree examples from
   `test_cse_compiles_each_distinct_subtree_once`; 12-variable XOR chain from
   `test_fanout1_chains_do_flatten`.
3. `tests/test_prepared_flat_evaluation.py` implication fixture, output bases
   k=4,8,16; optionally k=18 as a diagnostic output-width extension of the same
   disclosed expression (no new mathematical instance).
4. Existing expression-family unit-test seed=2 shared-block family (n=4, size=8),
   seed=3 composition family (n=4,size=5), and disclosed mutation variants from
   existing generators with the same seed (rates 0,0.15,1). Exact duplicate,
   partially reused, and independently disclosed fixture sequences distinguish
   high/partial/negligible cache reuse; these are diagnostic treatments of
   existing inputs, not confirmation cases. Record actual hit rates.
5. Existing exposed Y02–Y05 development inputs may be inspected; timing them is
   permitted only through baseline APIs or audit-local adapters with full source
   provenance. No root production overlay. Cover supplied assignment batches,
   restriction q1/q64, exact count, SAT, equivalence, simplified-expression
   delivery. Frozen task-matched SAT/counting/ROBDD/SymPy records provide controls
   when an installed baseline evaluator cannot execute the same task.

## Controlled ladder and boundaries

Raw recursive AST; identity-memo AST; raw occurrence-flat ablation; sharing-aware
CSE-flat; CM IR through the identical `PreparedFlatEvaluation` packed executor;
bare production CM-flat; public no-reinflate CM; persistent family off/on;
direct/CM ingress to the same eligible evaluator. Use identical expression,
ordered basis, restrictions, primitives, output bytes and verification for
attribution. Dense CM versus packed output and enumeration versus SAT/count/BDD
are explicitly contract/algorithm comparisons. Separate compile/setup-inclusive
and prepared/resident execution. No default or routing modifications.

Phase partition: process/import; ingress JSON load/parse/DAG decode; source UID
traversal; canonicalization/rewrite; keys/hash/sort/intern; support propagation;
cache lookup/validation/eviction; lowering; basis/name mapping; positional masks;
restriction binding; execution; allocation/release; complete materialization;
conversion; API guards; serialization/delivery/cleanup; unresolved remainder.
Use exclusive nested spans in a separate phase pass. Parent inclusive timings
are diagnostic annotations and never summed with children. Helpers combining
mechanisms remain grouped (e.g. binding lookup and fixed-key validation; Python
kernel and bigint allocation); report unresolved separation instead of zeros.
Absent phases are marked not applicable. Startup/import are measured only for
fresh-process delivery; resident-library callers have no such per-call phase.

## Passes and analysis

1. Whole-call uninstrumented wall/process CPU repeats, no profiler/tracemalloc or
   monkey patches. Cold = cleared process-local caches and freshly decoded input;
   warm = same object/state repeated; resident = setup charged once with q calls.
   Counterbalance arm order by deterministic rotation/reversal across repeats.
   Keep every sample; do not select favorable repetitions.
2. Separate exclusive phase/call-count pass; preserve production algorithms.
   Phase shares use that pass's own caller total, never the faster uninstrumented
   denominator. Quantify instrumentation dilation; small-helper timings are
   perturbed, not unbiased estimates.
3. Separate cProfile pass: self and cumulative costs/calls, never additive
   cumulative percentages. Separate tracemalloc pass: current/peak/net retained
   Python-traced bytes, not cumulative allocations or process RSS. Record
   retained graph/cache size where practical and limitations for NumPy/native.
4. Structural metrics outside timing: source unique nodes/edges/unfolded size,
   sharing, CM nodes/support sizes, flat instructions/primitive operations,
   live buffers, materializations, output bytes, cache counters/state.
5. Exact correctness after full output consumption; common guards charged in
   caller scopes where appropriate. Independent scalar/TT oracle outside timed
   setup; retain failures. Existing public guards stay inside their real spans.

Scaling includes output width on a fixed expression, disclosed source/sharing
examples, support width, instruction count, query count, and family reuse. These
small correlated observations do not identify independent causal slopes.
Use paired/incremental effects and representation-by-residency interactions;
do not force additive attribution across different outputs or preparation.

## Bounds and stop conditions

Local only, existing `.venv/Scripts/python.exe`, `-B`, explicit baseline cwd.
At most 2 hours total diagnostic execution, 30 minutes per suite, 60 seconds per
worker/cell, 7 uninstrumented repeats, 3 phase repeats and 1 profile/memory pass
per selected cell; q <=64, n<=18, families<=8, unfolded AST<=100,000, output
<=32 MiB per cell and stored diagnostic artifacts<=100 MiB (excluding external
predecessors). Structural/output caps are enforced by harness checks; there is
no claim of an OS-enforced memory ceiling. Stop a cell on mismatch, timeout,
unexpected dependency/import origin, unbounded growth, or contract mismatch;
retain its status and continue independent cells. No widening to repair an
unfavorable result. Debug/retry harness defects within these bounds with a
separate run identity; never overwrite measured evidence.

## Deliverables and decision language

EXECUTION_MAP, PROFILE_RESULTS.json, TIME_LEDGER, ROOT_CAUSE_MATRIX, REPORT,
AUDIT_MANIFEST plus reproducible audit-local scripts/tests and supporting data.
Classify material costs as inherent explicit output, task/algorithm mismatch,
CM representation, family reuse management, implementation/runtime,
wrapper/lifecycle, conversion/delivery, comparator preparation, or unresolved.
Use measured / code-supported inference / hypothesis / unknown consistently.
No optimization recommendations. End with meaningful diagnostic tests, Git
status/diff review, predecessor hash verification and unchanged disposition.
