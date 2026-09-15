# Wrapper, family, and Y02–Y05 source audit

## Evidence scope and terminology

This is a read-only source audit completed before new timing. **Code-supported inference** describes a reachable mechanism, not its measured share. **Measured** is reserved for recorded observations. **Unknown** means the available record cannot isolate the cost. No production file was changed.

Baseline code is commit `e334de594262059cc18cf37eaab56b0f79e94843` in the separate worktree. The requested `cmbench/comparative/sympy_cm_claim_cleanup.py`, `scripts/cm_sympy_development_gate.py`, and the September 11/15 audit directories are absent at that commit. Their supplied successor versions were read, without mutation, from `C:/Users/brian/Documents/CM_Computation`. They are predecessor evidence, not baseline implementation.

| Successor source | SHA-256 |
| --- | --- |
| `cmbench/comparative/sympy_cm_claim_cleanup.py` | `47ca5daf1d402e7c2c7e30140727699f0a67eb996f30d3688f219e803a666bd5` |
| `scripts/cm_sympy_development_gate.py` | `b65ee1016ca63b21909e7ac08227d0364db24a2370c5c837c6aab615416e95df` |

The final manifest binds all consulted predecessor files separately. Line references below are to the baseline unless marked **successor**.

## Public CM: what a bare kernel does not include

`cm_ir.py:2006` defines `materialize_hybrid_no_reinflate`. Its input is already compiled CM IR, not a parsed expression. The path contains:

1. `cm_ir.py:2030`: resolve flat/words policy and import engine selector.
2. `cm_ir.py:2033`: diagnostics-off fast branch, eligible only when `diagnostics is None`, a flat/words engine is requested, and `flat_fast_path=True`.
3. `cm_ir.py:2036`: normalize fixed context and output variable tuple; remove fixed names from retained node support.
4. `cm_ir.py:2043`: form effective output budget, choose packed versus uint8 representation using live support and threshold, and call `_cm_node_count` for estimated intermediate operation slots.
5. `cm_ir.py:2054`: estimate full/reduced explicit outputs and enforce output policy.
6. `cm_ir.py:2076`: if live support fits the hybrid threshold, select the actual packed engine using **requested output width**, execute, and create `FinalNoReinflateResult` including output order, status, and budget decision.
7. `cm_ir.py:2224`: otherwise call recursive/hybrid `materialize_ir`, align/broadcast output axes, create a full uint8 vector, and wrap it (`2238–2289`).

**Code-supported inference:** a comparison with `eval_cm_node_flat` isolates wrapper work only if the same engine, fixed context, output order, packed output contract, cache treatment, and diagnostics state are held constant. The wrapper's function default hybrid threshold is 7, whereas benchmark configuration defaults to 16 (`cmbench/config.py:40`). Above the selected threshold it changes execution and materialization, so the difference is not pure wrapper overhead. Declined/reduced output is not equivalent to complete output.

**Code-supported inference:** a non-`None` diagnostics dictionary forces the generic path (`cm_ir.py:2092`) even if no detailed profiling is requested. This path initializes and records diagnostics, estimates budget, executes, and wraps. Family benchmarking always supplies `{"ir_timing_enabled": 1}`. Consequently diagnostics-on family measurements cannot be subtracted directly from diagnostics-off bare timings to identify ordinary public API overhead.

`compile_expr` (`cm_ir.py:1294`) also computes a public `expr_structural_hash` before CM compilation, and retains it with the node. `evaluate_compiled` (`1314`) validates mode and delegates to the public wrapper. A direct `compile_expr_to_cm_ir` call does not carry that additional public hash contract.

## Family timing boundaries

`cm_bench.py:919–1007`, `_cm_family_workload(variants, n_vars, *, persistent_cache, tt_refs, sample_rng, config)`:

| Record/span | Included | Excluded | Additivity |
| --- | --- | --- | --- |
| `family_cm_*_total_time_s` | Variant loop, timed compile and evaluation, diagnostics bookkeeping, packed-to-array conversion, `np.array_equal` or sampled validation, final cache statistics | Initial persistent-cache clear and variable-name construction; outer reference creation; process/import/transport | Parent span; do not add compile or evaluation to it |
| `*_compile_total_s` | Sum of disjoint calls to `compile_expr_to_cm_ir(... persistent_cache=..., reuse_cache=False)` | Subsequent materialization and checks | Disjoint from evaluation total |
| `*_eval_total_s` | Sum of public `materialize_hybrid_no_reinflate` calls | Conversion to reference arrays and correctness comparison | Disjoint from compile total, but includes nested lowering, binding, kernel, wrapper, or fallback phases |
| Per-variant mean/median | Compile and evaluation plus intervening Python timing/bookkeeping | Result conversion and correctness check | Subset of total; medians do not reconstruct total |
| Persistent hit/miss/size | Counts reported by compilation and final entry count | Hit/miss latency, eviction latency, bytes retained, output reuse | Counts are not timing fractions |

The persistent cache is cleared once at the start of **each family arm**, outside its total timer (`929`). Thus enabled means intra-family reuse after a cold start, not a previously populated resident cache. The no-cache arm disables the persistent CM compilation cache; it does not promise to clear packed-mask caches or all per-object programs between variants. `reuse_cache=False` separately disables the whole-expression compile cache. These three caches must not be conflated.

`time_expression_family_workload` (`1041–1227`) constructs `tt_refs` with `eval_expr_tt` before any arm timer (`1063`). It also computes expression-family diagnostics before timing. These costs are part of a caller's invocation of the outer function but absent from all named arm totals. The BitSet arm picks words over flat over recursive (`1089–1105`), and any recursive bigint environment is built outside its family total. Its total includes result conversion and `np.array_equal`, while its per-variant time excludes them (`1110–1122`).

**Code-supported inference:** the residual `family total − compile total − eval total` is conversion, guards, loop/record handling, statistics, and timer overhead. It is not an isolated cache-management or wrapper measure. Comparing enabled and disabled totals mixes cache lookup/validation with avoided CM construction, changed object identity, retained programs, and warm positional masks. A paired incremental comparison plus separate profiles is appropriate; assigning every improvement to hit count is not.

The shared ROBDD family path (`1010–1038`) creates the manager, selects/declarations order before its timer, times expression-to-BDD construction only, and returns manager/node metadata rather than a packed relation. It has no analogous complete-output delivery phase. The per-variant ROBDD family aggregate (`1157–1187`) retains both sum of backend build times and outer wall time with manager lifecycle/checks. Neither is automatically contract-matched to explicit relation output.

## Restriction/cofactor boundaries

`_cm_partial_workload` (`cm_bench.py:396–497`) clears persistent cache before timing. With persistent cache and `reuse_compiled_ir=True`, it compiles a `CompiledExpr` once outside the context-loop timer and explicitly adds that compile-once duration to `partial_cm_cache_total_s`. Otherwise it compiles inside each context. Context normalization/output order, result conversion, and checks are within the context-loop total; per-context intervals start after normalization and end before conversion/checks.

`partial_cm_cache_compile_once_s` means compile-once elapsed when that path applies, otherwise a sum of per-context compile times (`480`). It must not be added again to an already inclusive `partial_cm_cache_total_s`. `partial_cm_cache_eval_contexts_total_s` is nested in the total.

`_robdd_partial_context_workload` (`cm_bench.py:500–622`) times BDD construction, then `manager.let` restriction, separately. `partial_robdd_total_s` is build plus restriction only (`602`); optional extraction is reported by another field. Manager construction, declaration/order setup, non-selected order sweeps, and result checks are not part of this sum. Native BDD restriction returns another compact function, whereas CM may return every remaining assignment. This is a contract comparison until identical outputs are charged.

## Existing diagnostics and overlaps

| Diagnostic | Valid interpretation | Invalid interpretation |
| --- | --- | --- |
| `cached_exec_fixed_handling_time_s` | Small fixed-map handling interval | All restriction/context work |
| `cached_exec_var_order_time_s` | Variable/live support selection **plus** output budget setup, node-count retrieval, output estimates/policy diagnostics (`cm_ir.py:2113–2150`) | Name mapping alone |
| `cached_exec_bitset_eval_time_s` | Engine selection/evaluation and associated instrumentation (`2158–2170`) | Pure bitwise kernel |
| `nr_bitset_eval_time_s` | Almost the same evaluation interval (`2157–2173`) | An independent phase to sum with `cached_exec_bitset_eval_time_s` |
| `cached_exec_result_wrap_time_s` | Result metadata/diagnostic recording and object construction | Output conversion alone |
| `cached_exec_total_time_s` | Generic wrapper span, excluding some entry policy/import work before `2093` | Whole caller time |
| `cached_exec_dispatch_time_s` | Residual of generic wrapper total after four named spans (`2205–2217`, `2275–2287`) | Pure dispatcher work: on fallback it also absorbs `materialize_ir`, alignment and vector construction |
| `final_truth_table_materialization_time_s` and `nr_tt_vector_build_time_s` | Same fallback array materialization interval (`2237–2252`) | Independent additive phases |
| `ir_compile_time_s` | Enclosing compile span | Sum with child canonicalize/rewrite/intern/support spans |

`scripts/cm_deep_performance_audit.py:212–232` records independent medians of nested compiler timers. Its `wrapper_current_ns_median` uses per-call timing, while `cm_flat_ns_median`/`cm_words_ns_median` use batched alternating rounds (`363–521`). These are useful descriptive records but their difference is not a measured exclusive wrapper span.

`scripts/cm_performance_audit.py:270` enables `tracemalloc` before its timing loop, and wall/process CPU samples are collected while allocation tracing runs (`280–287`). Those records are allocation-instrumented timings, not uninstrumented latency. Validation is outside each timed operation interval there (`292`).

## Successor Y02–Y05 mechanisms

All references in this section are to **successor** `cmbench/comparative/sympy_cm_claim_cleanup.py`, absent at the baseline commit.

| Task | CM path | Comparator path | Attribution boundary |
| --- | --- | --- | --- |
| Y02 complete relation | `_cm_truth`, `281`: CM compilation with reuse/persistent off and share-aware flatten, flat packed evaluation, unpack to Python list, caller repacks and hashes | `_sympy_truth`, `302`: AST-to-SymPy, lazy `truth_table` creation, exhaustive generator consumption | Same final bits, different execution algorithm and conversion chain; generator creation alone is not complete delivery |
| Y03 supplied assignment batch | `_cm_batch`, `342`: CM compilation; `_cm_batch_values`, `244`, memoized NumPy array evaluator over supplied rows; copy resulting Python list | `_sympy_batch`, `319`: AST-to-SymPy, `lambdify(...numpy,cse=...)`, evaluate, normalize vector | CM is not enumerating all `2**n` assignments here; its retained IR is used as a computation DAG |
| Y04 SAT | `_cm_sat`, `370`: create full relation and Python list, find first true row, construct witness | SymPy `dpll2` or PySAT Tseitin + solver (`358`, `380`) | Status/witness task is smaller than a full relation; algorithm mismatch survives identical status output |
| Y04 equivalence | `_cm_equivalence`, `414`: independently compile/evaluate/unpack both full relations, compare lists | Solve exclusive-or difference miter (`401`, `424`) | Complete relation work is unnecessary for a status-only contract |
| Y05 expression delivery | `_cm_truth_simplify`, `468`: full relation/list, minterm rows, SymPy `SOPform`/`POSform` | `simplify_logic` default/forced after AST-to-SymPy (`458`) | Different simplification algorithms; CM arm uses SymPy minimizer, not a CM-native expression-output algorithm |

Y03's `_cm_batch_values` includes assignment `frombuffer`, reshape and bool conversion; CM recursion/memo dictionary/temporary arrays; and final NumPy-to-Python-int-list conversion **inside** its `evaluate_ns` (`244–278`). Its named `deliver_ns` is only a second `list(values)` copy (`355`). The SymPy arm prepares assignment arrays between named timers, and its `evaluate_ns` excludes `_normalize_vector`, which is separately delivered (`327–339`). Therefore their evaluation phase labels do not define equal work.

### Important timer-contract discrepancy

**Code-supported inference, direct control-flow evidence:** `execute_worker` claims validation outside its timer (`533`) and its declared contract says `included_in_timing=False` (`217`), but `started` is set at `545`; `_result` computes `task_total_ns` at `503`, after Python has evaluated all call arguments. Therefore:

- All task totals include final artifact packing/hash work and validation digest comparison.
- SAT task totals include `scalar_truth_values(expr, n_vars)` and witness validation (`600–615`).
- Simplified-expression task totals include `sp.srepr`, exhaustive `_sympy_values`, semantic digest, and `expression_quality` (`653–671`).
- Equivalence task totals include parsing the right expression (`622`) while parsing the left expression occurs before the timer (`541`).
- Assignment task totals include deterministic supplied-row generation (`567`).
- Initial contract validation, left parse and `_preload_compared_runtimes` are outside task total (`537–544`). The preloader imports **all** compared runtimes including PySAT even for unrelated arms (`522–529`).

This finding corrects the interpretation of timing boundaries, not the archived outputs or scientific disposition. The scalar oracle used to construct frozen contracts remains separate preparation; worker validation is not consistently outside task timing. Historical phase residuals can be recomputed, but they cannot retrospectively split untimed guards, conversion, row generation, and Python overhead.

**Successor** `scripts/cm_sympy_claim_cleanup.py:378–403` times `subprocess.run` around a fresh worker for each cell, stopping before parent JSON parsing. Hence `caller_total_ns − task_total_ns` is a measured lifecycle residual containing process creation, imports, pre-task validation/parsing, worker result-dictionary completion and serialization, transport, and shutdown. It is not a pure import measurement or pure wrapper measurement. Parent work constructing/base64-encoding the command precedes the caller timer; parent parsing follows it. No process CPU phases were captured.

The gate script (`scripts/cm_sympy_development_gate.py:205–269`, successor) correctly declines isolated CM attribution because it lacks raw/structural input into the same candidate evaluator. It uses caller medians per instance. This audit does not change that no-go.

## Exposed development cases and eligible controls

Successor `docs/audits/2026-09-15-cm-sympy-claim-cleanup/FROZEN_INPUTS.json` contains four already measured development cases: `absorption-k4`, `contradiction-k4`, `majority-k6`, `balanced-k8`. Their supplied batch generator is `affine_xorshift_rows/v1`, 4096 rows. No held-out cases are needed. A small diagnostic subset covering rewrite, UNSAT, sharing and all tasks is absorption, contradiction and balanced; majority is useful only if a missing intermediate shape warrants it.

Eligible same-evaluator boundaries:

- **Complete relation, count/status derived from packed output:** baseline `compile_expr_flat` versus CM `compile_flat`, followed by the same packed program evaluator, output order, fixed context and byte delivery. Report differences in instruction graph caused by rewrites separately from representation construction.
- **Y03 supplied rows:** call the unchanged successor `_cm_batch_values(node, raw_rows, n_vars)` with either true CM IR or an audit-local lightweight object with the same `kind/op/args/var_name/const_value` interface built from raw AST. A structural-interning adapter can preserve repeated structure. This adapter adds no support, recursive public keys, semantic rewriting, or CM metadata. Its construction is charged, exact batch output verified, and its status is an eligible diagnostic ingress adapter, not a product backend or optimized implementation.
- **Y05 same minimizer:** direct packed evaluation and CM packed evaluation feed identical minterms into the same `SOPform`/`POSform` with identical form and delivery/quality checks. This isolates CM ingress; comparison to `simplify_logic` remains an algorithm comparison.

Do not run the original all-lane worker blindly: its mandatory preloader imports optional dependencies and its timing labels embed unlike work. Any isolated source load must bind the successor file hash, keep module resolution at the baseline worktree, and report that source provenance.

## Mechanisms supported before measurement

- **Inherent explicit-relation/output cost:** `2**k` result bits for complete packed relation, more bytes when a uint8/list/minterm contract is requested. CM's mathematical expressiveness does not require that a supplied-row evaluator materialize the complete relation; Y03 demonstrates a distinct task shape.
- **CM representation cost:** compilation, retained support/order/key metadata and semantic rewrites occur before a flat kernel needs only instructions and masks. Whether rewrites repay that construction is an empirical interaction with sharing and query count.
- **CM-family reuse-management cost:** persistent lookup/validation/retention can avoid subgraph reconstruction but does not imply reuse of masks, result arrays, guards or delivered outputs. Changes in object identity and downstream caches interact.
- **Wrapper/lifecycle cost:** budget estimation, node count, diagnostics, selected result structure, reference preparation and process/import transport have separate contracts and repeat boundaries.
- **Output conversion/delivery cost:** Y02/Y04 list expansion then packing, Y03 NumPy-to-list plus second list copy, family packed-to-uint8 checking, and Y05 minterm/expression encoding are real work outside—or ambiguously inside—named kernel fields.
- **Comparator-specific preparation:** SymPy conversion/lambdify, BDD declaration/order/manager setup, Tseitin encoding and solver lifecycle.
- **Unknown:** percentages of these costs cannot be inferred from code, cache counts, or nested span subtraction. Existing caller-minus-task and family residuals can bound aggregate omitted work only.

No optimization, routing change, new confirmation case, benchmark promotion, external resource, commit or push is proposed by this audit.
