# Execution map: ingress to caller-visible completion

This map describes code at `e334de594262059cc18cf37eaab56b0f79e94843`. References are repository-relative, one-based source lines. Statements are **code-supported inference**. Timing observations belong in `PROFILE_RESULTS.json` and `TIME_LEDGER.md`; absence of a timer is not absence of work.

## 1. Caller boundary and phase ownership

There are three nested caller boundaries. A **fresh-process caller** includes process startup/imports, input loading/decode, operation and returned serialization. An **in-process caller** starts with already imported modules and a supplied Expr/DAG and finishes with the requested Python value. A **prepared evaluator caller** starts with a bound program or CMNode and finishes with an integer. A family caller may also include reference construction and correctness checking. These cannot be compared without naming exclusions.

Use the following exclusive phase vocabulary. A parent span is reported separately, never added to its children. For a profiler, assign each event to the innermost active phase; report uncovered elapsed time as residual. Where an operation combines arithmetic and allocation, do not invent a split: retain a joint execution/allocation phase and use a separate memory/call-count pass to describe it.

| Phase | Exclusive work owned | Representative source / applicability |
|---|---|---|
| `startup_imports` | Interpreter/process launch and module import before request ingress | External worker envelope; imports include NumPy and, for `cm_bench`, optional availability probes (`cm_bench.py:16`). No analogous work inside an already-running evaluator. |
| `input_load_parse_decode` | File read, text/JSON parse, integrity checks on input, Expr creation and DAG reference resolution | `cmbench/corpus.py:36`, `CorpusFormula.to_expr` at 20, `cm_expr_serde.py:152`, DAG decoder at 202. No analogous work when Expr supplied directly. |
| `source_traversal_uid` | Walking source objects and assigning compact structural equivalence classes/fanout | CM sharing prepass `cm_ir.py:1052`; CSE first pass `bitset_backend.py:614`. Raw recursion traverses during execution, so has no separate preparation analogue. |
| `canonicalize_rewrite` | Associative splice decisions, operand order, constant/identity/complement/parity rewrites | CM builder `cm_ir.py:740`, `775`, `836`, `895`, `947`, `1007`. CSE has optional sharing-aware splice but no Boolean rewrite or commutative reorder. |
| `keys_hash_sort_intern` | Deep/compact key construction, hashing, sorting and node/UID interning outside another explicit phase | CM intern `cm_ir.py:635`; digest `235`; CSE keys within its UID pass. When UID construction and interning are inseparable in a measured helper, report a joint span instead of double counting. |
| `support_propagation` | Building sorted retained variable tuples | `cm_ir.py:723`. No analogue in raw AST/CSE flat compilation. |
| `cache_management` | Lookup, hit/miss accounting, validation actually performed, update/eviction; excludes cache-miss construction assigned elsewhere | IR caches `cm_ir.py:323`, `1247`; root program accessors; env/bound caches. Digest cache has no equality validation. Missing validation time must be null or zero-with-code-evidence, not estimated. |
| `lowering` | Emitting flat loads/ops and release schedule after source/CM traversal | CM lowering `bitset_backend.py:329`; raw occurrence lowering `546`; CSE emission `680`; `FlatProgram` constructor `235`. |
| `variable_basis_mapping` | Establish requested output variable order, map names to positions, align metadata | No-reinflate wrapper `cm_ir.py:2113`; alignment-plan `1345`; program load variables `bitset_backend.py:239`. Positional convention is MSB-first assignment rows. |
| `mask_environment` | Constructing input bit columns/word views, full-width mask, bound input slot template on misses | `bitset_backend.py:16`, `374`, `818`. A cache hit replaces construction with lookup; does not delete its historical cost. |
| `restriction_binding` | Normalize fixed context and bind fixed input values under chosen output-variable contract | `cm_bench.py:428`; `_partial_output_vars` at `cmbench/expr/partial_contexts.py:95`; flat binding at `bitset_backend.py:374`; word `resolve` at 891. No analogue for unrestricted calls beyond empty-map handling. |
| `execution_kernel` | Logical operations and required per-instruction dispatch, with inseparable runtime allocation/release reported jointly | Memo AST `bitset_backend.py:65`; memo CM `120`; prepared flat `423`; word loop `905`. |
| `intermediate_allocation_release` | Separately observable slot copies, scratch allocation/reuse and reference clearing | Bigint template copy/release `bitset_backend.py:425`, `451`; word scratch `880`; last-use/word plan `252`, `836`. Bigint payload allocation within logical operations remains joint with kernel. |
| `reinflation_materialization` | Build complete dense output, broadcast omitted axes and force owned output where contract requires it | Dense CM `cm_ir.py:1931`, `1968`; no-reinflate fallback `2224`, `2237`. Packed paths have no dense reinflation analogue. |
| `output_conversion` | Packed word array to bytes/int, integer to unpacked vector, dtype/layout conversion | `bitset_backend.py:941`, `106`, `115`; `cm_ir.py:2241`; family check conversion `cm_bench.py:969`. |
| `api_guards` | Required output-budget, mode/width/input validity checks; distinguish reference correctness checks in harness | `cm_ir.py:2044`, `2055`, `2126`, `2143`; engine width validation `cmbench/backends/bitset_engine.py:81`. Bare kernel does not have public budget guard. |
| `serialization_delivery_cleanup` | Result-object construction, optional serialization/transport, releasing caller/session objects and final aggregation | `FinalNoReinflateResult` creation `cm_ir.py:2081`, `2188`; family return `cm_bench.py:978`. Local integer evaluators have no serialization or network-delivery analogue. |
| `unresolved_residual` | Work or interactions not isolated by available measurement | A named, quantified remainder when possible. Never distribute proportionally merely to force a sum. |

Source parsing integrity checks belong to ingress; output-budget validation belongs to API guards; benchmark reference comparison belongs to explicitly identified harness correctness work. These are different validation contracts.

## 2. Raw AST recursive evaluation

1. Receive Expr and ordered environment (ingress already complete).
2. Compute full mask from environment width.
3. Recursively dispatch each occurrence, load input by name, execute Python bigint primitives and return integer.
4. Caller optionally converts or serializes the output.

The existing no-memo restricted helper is `_eval_expr_bitset_fixed` (`cmbench/expr/partial_contexts.py:126`), including fixed-value loads. There is no CM compilation, support propagation, canonicalization, interning, flat lowering, root program cache, separate restriction simplification or dense output materialization. Traversal, dispatch, arithmetic and recursive lifetime are interleaved. A repeated source reference is recomputed. New instrumentation must label any diagnostic equivalent rather than pretending the memoized production function is raw recursion.

## 3. Memoized AST / direct BitSet

`build_bitset_env(order)` → `eval_expr_bitset(expr, env)` → optional output conversion.

The environment is a process LRU and can be prepared outside or inside a caller span (`bitset_backend.py:16`, `57`). The evaluator creates an identity-keyed per-call memo, dispatches unique source objects, retains each result through the call, and returns a Python integer (`65`). There is no semantic canonicalization, source structural UID prepass, CM support set, flat lowering or inter-call result memo. Structurally equal separately allocated subtrees do not hit an identity memo.

“Direct BitSet” is an engine family, not one algorithm: `select_raw_ast_engine` (`cmbench/backends/bitset_engine.py:68`) chooses memoized raw recursion when neither packed flat flag is requested, no-CSE raw flat when flat is requested or words requested below 16 output variables, and no-CSE words at 16 or more. Explicit words evaluators have a separate six-variable physical-width fallback. These thresholds are part of current routing and were not changed.

## 4. Raw no-CSE flat ablation

Expr root-attached program lookup → on miss occurrence-expanding `compile_expr_flat` → construct loads/ops/release schedule → `_bind_flat_program` cache lookup/mask setup → template copy → binary flat loop → optional last-use clearing → integer return (`bitset_backend.py:546`, `585`, `758`).

This emits each subtree occurrence and can discard useful source-DAG sharing. There is no structural interning or CM rewrite/support phase. It is an explicitly labelled ablation, not the strongest generic flat comparator.

## 5. Structural CSE-flat

Expr root-attached CSE-flat program lookup → on miss iterative structural UID/intern/fanout pass → sharing-aware associative single-consumer splice → topological slot emission/release schedule → same bound-template cache and mask construction as CM-flat → `PreparedFlatEvaluation` → `_eval_prepared_flat` → integer return (`bitset_backend.py:599`, `697`, `729`).

No CMNode graph, deep CM key, support tuple per node, Boolean simplification or commutative sorting is constructed. Structural sharing survives into a program by UID slot reuse. Unflattened structural CSE is an optional neighboring control; it preserves sharing but retains binary chains. Word CSE swaps the final executor to `_eval_words` and shares all packed word primitives with CM (`bitset_backend.py:707`). Program size can differ from CM because CM rewrites alter the logic graph; those differences must be recorded.

## 6. Raw CM IR through the same packed primitives

Expr → `compile_expr_to_cm_ir` → optional IR-cache lookup → CM sharing UID prepass → canonical recursive build (rewrite/support/key/intern) → CMNode graph → `compile_flat` → `FlatProgram` → `_bind_flat_program` → `PreparedFlatEvaluation` → same `_eval_prepared_flat` used for CSE → integer return.

This boundary includes CM IR construction and lowering but avoids public result wrapping/dense materialization. Its output can be identical to CSE's. The differences are compilation representation, rewrite-induced program shape and retained state; the logical execution primitive implementation is held constant. The CM graph and flat program may both stay resident.

The alternative recursive CM evaluator uses `eval_cm_node_bitset` with a fresh identity memo (`bitset_backend.py:120`). It has no separate flat-lowering/release-plan phase and retains results until return. Its n-ary AND/OR/XOR loop starts from an identity value and combines every argument, whereas the flat loop starts from the first operand; primitive counts for the flat executor must not be silently assigned to this recursion.

## 7. Bare CM-flat versus prepared CM-flat

* **Bare CM-flat:** an existing CMNode enters `eval_cm_node_flat` (`bitset_backend.py:493`), which obtains/caches its flat program, obtains/caches bound input masks, copies slots, runs the flat loop, optionally clears dead references and returns an integer. Compile-to-IR and public wrapper guards are absent. A cold attached-program cache still incurs lowering.
* **Prepared CM-flat:** an existing `PreparedFlatEvaluation` enters `.evaluate()` (`bitset_backend.py:419`). Lowering, name/context binding and mask construction are absent from this boundary; slot copy, execution and release recur.
* **CM words:** existing CMNode → attached flat program → first-use word plan → words env cache → per-thread scratch cache → load/fixed resolution + NumPy `out=` loop → `.tobytes()` + `int.from_bytes` (`bitset_backend.py:944`, `873`). No dense reinflation, but the whole function is broader than the word arithmetic kernel.

## 8. Public CM boundaries

### Public no-reinflate evaluator

Existing CMNode → defaults/import → threshold/output-budget and variable checks → root-count cache → select output order/reduction contract → packed engine if retained live width fits threshold → `FinalNoReinflateResult`; otherwise hybrid NumPy materialization → alignment/broadcast/uint8 vector conversion → result (`cm_ir.py:2006`).

Diagnostics-free flat/words calls can use the fast branch (`2033`); diagnostics force the generic branch (`2092`). Packed output performs no dense reinflation. It still retains required metadata/budget decisions in a result object. The threshold is not a universal speed selector: the caller can request enough threshold to exercise a particular evaluator, but any such override must be declared as a diagnostic treatment.

### Public reusable compile/evaluate API

`compile_expr` first computes an additional associative structural hash, builds or retrieves IR and returns `CompiledExpr` (`cm_ir.py:1292`). `evaluate_compiled` delegates to the public no-reinflate evaluator (`1310`). A resident session can amortize compilation; all requested evaluation and delivery work recurs. The digest itself is outside internal `ir_compile_time_s`.

### Public dense CM

`compile_expr_to_cm` (`cm_build.py:26`) → compile IR → `materialize_cm` (`cm_ir.py:1899`) → budget → hybrid/NumPy materializer → support alignment and broadcast to row+column order → final dense `.copy()` → ndarray return. This output differs from a packed integer by layout and bytes; comparison with packed output alone is a contract comparison. All requested rows and columns are produced even for a constant result.

## 9. CM-family and q1/q64 contexts

`time_expression_family_workload` normalizes variant list, builds dense truth references when enabled and computes family diagnostics **before** measured backend totals (`cm_bench.py:1058`). Direct BitSet then chooses engine and, for recursion, prepares the shared environment before its total (`1082`). Each direct variant evaluator returns integer; conversion/reference check occurs inside family total but outside per-variant evaluator time (`1097`).

Each `_cm_family_workload` clears persistent IR cache before starting total (`cm_bench.py:928`) → per variant diagnostic dict → compile (ordinary or persistent) → public no-reinflate evaluator with diagnostics → collect counters → convert to reference format/check → aggregate return (`919`). Persistent cache disabled still permits process environment and object-attached caches. Persistent cache enabled performs per-call sharing/digest work, root/subtree lookup, hit adoption or compilation, LRU handling and retains nodes across variants. Shared associative classes trigger root-only caching; absence permits subtree reuse (`cm_ir.py:344`). Entry count and hit ratio do not specify saved bytes or saved computation.

For contexts, `_cm_partial_workload` optionally performs reusable `compile_expr` once and adds that duration back to overall total (`cm_bench.py:419`, `481`). Every context normalizes fixed names/values, chooses remaining-vars or full-vars output, binds, evaluates, converts and checks (`428`, `440`, `457`). At q64 a compiled program/mask cache can amortize across contexts, but new fixed-value keys can miss the binding cache; fixed axes remain broadcast if `full-vars` was requested. Exact reference construction is separate (`cmbench/expr/partial_contexts.py:103`). Changing q changes amortization; changing remaining-vars to full-vars changes output contract exponentially.

## 10. Task matched controls and phases with no counterpart

| Requested task | Complete-relation route | Smaller task-matched route and missing phases |
|---|---|---|
| Complete packed relation | Direct BitSet, CSE and CM must deliver same ordered `2^k` result bits | SAT/BDD construction alone has no corresponding complete-output delivery and is not a same-task comparator. A BDD must enumerate/extract to match. |
| Supplied assignment batch | Build complete relation then index assignments | Evaluate only supplied assignment lanes; no all-assignment environment or complete-relation materialization. This is an algorithm/output-work comparison unless both ingresses feed the same batch evaluator. |
| Restriction/cofactor q1/q64 | Bind fixed values and produce remaining-variable relation, or full broadcast relation if requested | A BDD restrict operation returns a graph; it has no packed-output extraction unless added. Supplied residual relation and graph are different deliverables. |
| Exact count | Build relation then population count | Counting solver/BDD counting can return a scalar without explicit relation delivery. They add encoding/manager/compiler preparation of their own. |
| SAT status | Build relation then test nonzero | SAT solver may stop after one witness; no complete relation phase. Unsatisfiability still needs proof/complete search appropriate to solver. |
| Equivalence status | Build both relations or a miter relation, then compare/test | SAT miter unsatisfiability or canonical BDD root comparison after encoding/build; no mandatory truth-table extraction. |
| Simplified expression | Symbolic CM rewrites then any necessary conversion to requested expression | SymPy simplification builds/delivers symbolic form. A relation-only answer is not an equivalent delivery contract; reconstruction and expression growth can be material. |
| Expression families | Rebuild/cache CM per variant and deliver each requested answer | CSE retained programs or BDD shared manager have their own reuse scopes. A manager-only build timer excludes extraction/checks and cannot isolate CM cost. |

These are algorithmic possibilities and code-supported boundary distinctions, not measured superiority claims. Worker-specific direct-versus-CM ingress, serialization and downstream evaluator paths are separately documented in predecessor/worker evidence auditing; no held-out inputs are needed to determine these contracts.

## 11. Frozen-timer interpretation

The full overlap/validity table is in `CODE_AUDIT.md`. Key prohibitions: do not add `ir_compile_time_s` to builder timers; do not add `nr_bitset_eval_time_s` to `cached_exec_bitset_eval_time_s`; do not add boundary final alignment to the identical final CM-copy timer; do not call fallback residual “dispatch”; do not use instrumented generic-wrapper phase percentages as measured percentages of the diagnostics-free fast wrapper. Unavailable CPU or phase allocation remains unknown. No scientific disposition changes.
