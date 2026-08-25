# Correspondence Matrix Deep Performance Audit

Audit date: **2026-08-25**  
Repository: `C:\Users\brian\Documents\CM_Computation`  
Starting revision: `main` at `1ba3a7312fa99439b57ddb3b4433ead7e86b2c74`

## Executive conclusion

CM still has one credible general optimization surface: **preparation constant factors**. This audit measured and implemented one small, safe reduction. The default sharing-aware builder was maintaining an object-identity memo and a structural-UID memo over the same compile. Removing only the redundant identity layer reduced paired cold compile time by about **4.0% on BX1+B2** (`0.9601` candidate/baseline, circuit/family-cluster interval `[0.9510, 0.9721]`) and by a smaller/noisier **2.3% on reused EPFL** (`0.9768`, `[0.9547, 0.9995]`). Python-traced peak allocation fell about **11.8%** in the smoke. All 401 representative canonical-DAG and packed-output comparisons matched; the full suite passed (`359 passed, 4 subtests`).

No other production change survived the evidence gate:

- The `k>=16` flat/words selector remains a conservative default. Corrected full-corpus regret is low, but focused `k=13..15` and cross-machine evidence proves that support alone cannot express the crossover. No threshold retune is justified.
- Interning remains the largest measured preparation subphase (about 21–26%), followed by lowering, support analysis, hashing, rewrite, and canonicalization. The costs are distributed; broad pass fusion and an e-graph replacement are not supported.
- Flat Python bigints remain the correct default below the measured word crossover. Native/JIT/SIMD kernels require a real repeated batch in which kernel time dominates compilation, dispatch, copies, and output.
- Persistent cache, family, and partial-context reuse remain workload-distribution questions. Existing synthetic reuse helps CM relative to uncached CM but does not beat the strongest task-matched incumbent. No admission or persistence policy should be productized without real version/context/access traces.
- Kronecker/block structure exists only for genuinely independent variable blocks. Lazy permutations/lifts can remove intermediates, but no algebraic representation can avoid the `2^k` exact-output lower bound when the caller requests the complete vector.
- Multiprocessing, GPU, and distributed execution remain negative defaults because startup, serialization/copying, synchronization, and memory amplification are not amortized by admitted local workloads.

The current practical order is: preserve exactness and fail-closed budgets; continue reducing measured preparation allocations; obtain real cache/edit/context traces; then build a feature selector with a newly frozen untouched validation corpus. Hardware kernels come later, if a genuine repeated batch changes the cost balance.

## Repository preservation and evidence roles

No repository-level or ancestor `AGENTS.md` was present; the supplied global instructions governed the audit. Before production edits, the audit recorded branch, HEAD, complete `git status --short`, dependency versions, interpreter, affinity, source hashes, and corpus hashes in `baseline_smoke_environment.json`.

The worktree was already heavily dirty. Pre-existing modified files included `README.md`, `bitset_backend.py`, `cmbench/backends/bitset_engine.py`, Aug-24 reports and benchmark drivers, website templates/assets, and `tests/test_bitset_cse.py`; numerous correction, Runpod, external, temporary, and generated paths were untracked. Those bytes were preserved and are not attributed here. This audit changed only:

- `cm_ir.py`
- `tests/test_build_memo.py`
- new `scripts/cm_prepare_memo_ablation.py`
- new `docs/audits/2026-08-25-cm-deep-performance/` artifacts

No `.env*`, credential, token, or private configuration was read. No dependency was installed, no cloud job was launched, and no commit, stage, or push was performed.

Evidence roles are explicit:

- **BX1:** tuning.
- **B2 and EPFL:** reused validation; they have influenced prior decisions and are not untouched held-out data.
- **Aug-25 correction artifacts:** authoritative for frozen truth/order, selector regret, and strongest-comparator results.
- **This audit’s A/B:** acceptance evidence for the one-memo preparation change, with immutable listed-source snapshots.

## Authoritative starting evidence

The fifteen requested documents were read in order. The current claim map and its addendum supersede older V3/V4 claims. Newer Aug-24/Aug-25 audit and correction artifacts were then checked for revisions.

The following conclusions remain authoritative:

1. On accepted B1/E3 evidence, CM and sharing-aware CSE-flat are kernel-equivalent: external CM/CSE-flat `0.9998`, interval `[0.9747, 1.0249]`. The small residual is not an optimization target.
2. CM’s earlier win over plain structural CSE came mainly from safe flattening/merging. A comparator with the corresponding CSE-flat transformation closed that gap on the accepted parity workload.
3. The post-audit, exactly counterbalanced V3 B2/B4 study supersedes the V2 local headline. With one equal-weight contribution per formula, bare CM/CSE-flat was `0.890570` overall (formula-cluster 95% bootstrap interval `[0.874065, 0.907272]`) and `0.961234` at `k=16` (`[0.928974, 0.994177]`); public wrapper/CSE-flat was `3.094136` overall (`[2.883083, 3.310818]`). This is a workload- and machine-conditional structural result, not a universal claim, and it does not supersede B1/E3 parity on that distinct workload. The immutable V3 evidence is under `deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_*`.
4. At the whole-call boundary BitSet led every measured semantic support through `live_k=16`. CM preparation is roughly four times the comparison compiler on accepted studies and remains the leading raw opportunity.
5. B3 established structural-DAG scaling. Preparation follows `s`, not unfolded `t`; the remaining problem is a constant factor rather than a scaling catastrophe.
6. BX1 retracted the old `k>=6` words rule. Flat bigint won through `k=12`; words won at `k=16`. Aug-24/Aug-25 gap studies show material workload interaction at `k=13..15`.
7. Complete explicit output is inherently exponential in semantic support. The output guard is a safety contract; raising it is not an optimization.
8. Persistent-cache, family, and context experiments do not establish incumbent-beating reuse economics. Cache warmups must be separated from process cold starts, serialization, and task-matched baselines.
9. CM quotient/operator artifacts are not semantic XOR. CUDD construction, canonical BDD structure, restriction, and exhaustive extraction are separate artifacts and timing windows.
10. Structural digests and current normalized keys give engineering identity under documented normalization and collision assumptions. They do not prove global semantic canonicality.

No newer artifact changes these ten statements. The Aug-25 correction changes evidence labels and strength: B2/EPFL are reused validation, frozen EPFL order/digests are now verified, and CSE-flat—not raw AST—is the primary generic comparator.

## Execution and ownership map

### Code path

| Stage | Current implementation | State/reuse boundary | Dominant dimensions and notes |
|---|---|---|---|
| Parse / deserialize | `cm_expr_serde.expr_from_json`, including DAG form; expression classes in `cm_exprlib` and `cmbench/expr` | Once per loaded request/artifact unless caller retains the Expr DAG | O(`s`) for DAG serialization; a tree encoding can expose `t`. DAG serde preserves sharing. |
| Structural identity | `cm_ir._structural_digest` for associative/commutative external hash; `_persistent_digest` for association-preserving cache identity | Per cold key computation; digest memo scoped to one call | O(`s`) under identity memo. BLAKE2b-128 cache equality has an explicit collision assumption, not an equality fallback. |
| Sharing/fanout plan | `CMIRBuilder._shared_assoc_uids` | Once per sharing-aware compile | Walks the Expr DAG, assigns structural UIDs, and identifies shared associative classes whose flattening must be suppressed. |
| Adoption / interning | `CMIRBuilder._adopt_foreign`, `_intern`, compact `(op, child_uid...)` lookup | Builder-local per compile; persistent hits can be adopted | Compact lookup is O(arity); `CMNode.key` remains a deep structural tuple for stable ordering/identity. |
| Canonicalization / rewrite | `_canonicalize_commutative_args`, `make_and/or/xor/imp/eqv`, `negate` | Once per structural class on the structural-UID memo | Exact Boolean rewrites, commutative ordering, safe associative splice/suppression, constants, idempotence, complements. |
| Live support | `CMNode.vars`, `_live_vars_union`; selector is passed actual live support | Built per IR node, then retained | Tuple sorting/union cost scales with input support sets. Fixed syntactic axes are not counted as live output axes. |
| IR lowering | `bitset_backend.compile_flat`, `compile_expr_cse(flatten=True)`, cached `get_flat_program` | Once per retained CM node/expression, then reused in process | Iterative postorder, one slot per DAG node, last-use release plan, primitive operation metrics. `m` is flat operations/instructions, not Expr tree occurrences. |
| Backend selection | `cmbench/backends/bitset_engine.select_raw_ast_engine` / `select_cm_node_engine` | Once per wrapper evaluation | Current auto policy: words only when requested and `k>=16`, else flat if requested, else recursive. Support-only policy is conservative, not globally optimal. |
| Recursive bigint | `eval_expr_bitset`, `eval_cm_node_bitset` | Per evaluation; bitset environment cached by variable tuple | Lowest wrapper complexity but repeated Python recursion/dispatch. |
| Flat bigint | `PreparedFlatEvaluation`, `_eval_prepared_flat`, `eval_cm_node_flat`, `eval_expr_flat_cse` | Program and bound template can be reused; values list is copied per evaluation | One Python loop over `m`, each integer Boolean operation spans `2^k` bits in native CPython. Dead-slot clearing activates only for wide/large programs. |
| Word-packed | `_eval_words`, `eval_cm_node_words`, `eval_expr_words_cse` | Word environment cached; `word_plan` retained; scratch is per-thread | NumPy `uint64` kernels, preplanned buffer reuse, `out=` operations, exact tail masking. Dispatch/copy dominates small `k`; buffers scale with peak liveness. |
| Output conversion | `bitset_to_bool_array/hypercube`, `materialize_cm`, `materialize_hybrid_no_reinflate` | Per requested artifact | Packed return is smallest. Dense/table/CM conversion pays `Theta(2^k)` bytes/elements and any layout permutation. |
| Output admission | `cmbench/output_budget` | Per request before allocation | Representation-aware output and temporary estimates; statuses include `ok`, `reduced`, `refused`, `timeout`, `oom`, `unvalidated`. |
| Process-local caches | expression env LRU, words env, flat program/bind caches, `_PERSISTENT_IR_CACHE`, normalization/alignment caches | Process lifetime until explicit clear/eviction | Persistent-named IR cache is process-local LRU, max 10,000 entries, not a disk/cross-process cache. Entry count is not a byte budget. |
| Serialization / remote | `expr_to_json_dag` / `expr_from_json`; remote benchmark infrastructure | Per boundary unless retained worker state exists | Serialization and source/schema/version identity must be timed separately from kernel. |
| Partial contexts | `cmbench/expr/partial_contexts.py`, fixed bindings in flat/word evaluators, BDD `let` path | Compile may be once; restrict/bind/output once per context | Remaining live support `k_j`, overlap/locality, manager/cache lifetime, output kind, and per-context query count govern break-even. |
| Expression families | `cm_bench` family experiment and structural persistent cache | Base/family state once, delta/recompile per version | Existing synthetic families are independently generated variants, not a real edit trace. |
| Parallel | `cm_parallel.compile_expr_to_cm_parallel`, `ProcessPoolExecutor`, optional shared memory | Pool optionally per process; work per large combine | Thresholded by expression nodes and elements; still copies into/out of shared memory and amplifies process/cache state. |
| Pair/token path | `cm_build_pair` and `cm_token` | Per materialization | Exact constant-size 2x2 collapse for a one-row/one-column variable pair; conditional local transformation, not general factorization. |
| Numba | `numba_backend` | JIT compile/warmup then evaluate | Optional fixed-width array path; package absent in audit environment. Compile and conversion must be included. |

### When costs are paid

| Cadence | Costs |
|---|---|
| Once per expression load | parsing or DAG deserialization, schema validation |
| Once per cold expression compile | structural/fanout traversal, canonical rewrite, interning, support propagation, CM IR creation |
| Once per process and artifact | process-local cache lookup/fill, flat lowering, bound/environment fill; invalidated by key/schema/options or explicit clear |
| Once per family/version | change detection, affected-query validation, delta compilation, family cache lookup—if such a system is built |
| Once per partial context | restriction/fixed binding, remaining support computation, context cache lookup, and requested context output |
| Once per evaluation | selector/wrapper dispatch, values-template copy or word scratch checkout, `m` operations over the packed width |
| Once per returned artifact | packed conversion, truth-table/dense materialization, layout permutation/lift, serialization |

## Formal cost and memory model

Let:

- `s`: structural Expr/IR DAG nodes;
- `t`: unfolded tree occurrences;
- `k`: semantic/live support;
- `m`: flat instruction or primitive-operation count, stated explicitly per metric;
- `q`: repeated evaluations of one compiled expression;
- `f`: related expressions/versions;
- `c`: partial contexts;
- `w`: machine word width;
- `B`: cache or memory budget.

For one expression:

```text
T_prepare(s,k,m) = T_parse + T_digest + T_fanout
                 + T_canonicalize + T_rewrite + T_intern
                 + T_live + T_lower

T_evaluate(m,k,w) = T_dispatch + T_bind
                    + T_kernel(m,k,w) + T_materialize + T_convert

T_total = T_prepare + T_cache_lookup/persist + q * T_evaluate
```

For the flat-bigint executor, a useful machine-level approximation is `T_kernel = sum_i C_bigint(op_i, 2^k bits) + O(m)` Python dispatch. For word arrays, it is `sum_i C_word(op_i, ceil(2^k/w)) + T_ufunc_dispatch + T_buffer`, bounded below by the bytes each non-fused operation must read/write. These expressions explain why bigints win narrow cases even though word kernels expose SIMD.

For expression versions:

```text
T_family = T_prepare(base)
         + sum(i=1..f) [T_change_impact(i) + T_cache(i) + T_delta_prepare(i)]
         + sum(i=0..f) q_i * T_evaluate(i)
```

Cold rebuilding substitutes `T_prepare(i)` for each `T_delta_prepare(i)`. Incremental compilation wins only when validation plus affected work is reliably less than cold work and retained state fits `B`.

For partial contexts:

```text
T_contexts = T_prepare(base)
           + sum(j=1..c) [T_context_lookup(j) + T_restrict(j)
                          + q_j*T_kernel(m_j,k_j,w)
                          + T_output(k_j)]
```

Context overlap matters only if retained symbolic/compiled state reuses it; it is not a benefit by itself.

Memory is separated into retained and temporary components:

```text
M_retained = M_expr + M_ir + M_flat_program + M_bound_env
           + M_process_caches + M_persistent_artifacts

M_temporary = M_compile_memos + M_value_slots
            + M_word_scratch + M_materialization + M_serialization
```

With `b` peak live word buffers, a direct words environment/scratch model is approximately `Theta((k+b) * 2^k / w)` words. A packed output alone is `Theta(2^k/w)` words; a dense byte/bool table is `Theta(2^k)` bytes/elements.

### Lower bounds and semantic boundaries

- Returning every value of an arbitrary Boolean function over `k` variables requires `2^k` bits of information. A packed output therefore requires **Omega(`2^k/w`) words of storage and output work**; a byte-per-value table requires Omega(`2^k`) bytes.
- A BDD, SAT answer, factorized expression, quotient, iterator, or oracle may be sub-exponential for a particular function/query, but it is a different artifact until expanded.
- A Kronecker product of independent blocks still contains the product number of output entries when materialized.
- Preparation can be O(`s`) despite `t` being enormous; any verification, equality, or serialization step that recursively unfolds shared substructure can accidentally reintroduce O(`t`) behavior.

## Fresh profiling results

Full definitions, commands, dispersion, and raw files are in [CM-BENCHMARK-RESULTS.md](CM-BENCHMARK-RESULTS.md).

The clean 25-row smoke found median compile/end-to-end times of 153/173 us for BX1, 321/339 us for B2, and 725/810 us for EPFL. Instrumented median phase fractions were:

| Phase | BX1 | B2 | EPFL | Audit interpretation |
|---|---:|---:|---:|---|
| Intern | 21.9% | 21.1% | 26.2% | Largest phase and primary local prototype surface |
| Lower CM | 14.6% | 10.4% | 12.5% | Material, already iterative/id-memoized/cached |
| Live support | 10.0% | 10.3% | 11.0% | Material tuple/union allocation; exact support must remain |
| Structural hash | 10.7% | 8.9% | 11.8% | Separate key window; incremental digest only helps retained/versioned callers |
| Rewrite | 7.6% | 11.3% | 7.3% | Not dominant enough for e-graph/broad fusion |
| Canonicalize | 5.9% | 6.7% | 6.1% | Deep-key ordering is a future compact-rank prototype, not today’s bottleneck |

cProfile confirmed the same shape: 150 compiles consumed 0.370 s cumulative; `_build_rec` 0.296 s, `_intern` 0.089 s cumulative, `_shared_assoc_uids` 0.070 s, live-variable union 0.061 s, and canonicalization 0.031 s. The diagnostic path calls `_bump` and timers frequently, so phase percentages are directional. External compile timing is authoritative.

Cold/warm behavior is already visible in accepted cache experiments: a deliberately all-hit second pass can be much faster (`0.263` warm/cold paired geomean under `tracemalloc` in the Aug-24 B2 probe), but that is not a realistic hit-rate distribution and does not include cross-process persistence. The cache retained 1,368 entries and about 1.31 MiB traced in that probe; this is a working example, not a policy acceptance result.

## Ranked findings and decisions

| ID | Mechanism / symbols | Evidence and affected workload | Expected gain | Correctness / memory / maintenance risk | Dependency | Validation | Decision |
|---|---|---|---|---|---|---|---|
| DP25-01 | Remove default path’s redundant `state.memo`; `CMIRBuilder.build` | Two memos cover the same structural compile; `_build_rec` is dominant; 272-row paired ratio 0.9601 and peak ratio 0.882 | 2–4% cold prep; ~12% traced compile peak | Low: preserve structural memo and legacy identity path; reduces temporary memory | None | Exact O(`s`) DAG signature, packed truth, focused/full tests, reused EPFL | **Implemented** |
| DP25-02 | Compact canonical ordering/key ranks without changing `CMNode.key` semantics | Intern 21–26%; canonicalization 6%; deep key comparisons can unfold sharing | Possibly low-single-digit prep and reduced comparison tails | Medium: ordering and foreign adoption are canonicality-sensitive; retained-key compatibility | None | Paired B2/EPFL/high-sharing B3, key/order tests, allocation | **Prototype next** |
| DP25-03 | Fuse fanout/liveness/lowering traversals | Distributed phase costs; no measured duplicate traversal dominates | Unknown | High attribution/correctness cost; can damage sharing-aware flatten guard | None | Phase-specific ablation and exact IR signatures | **Reject broad fusion; prototype only a proven boundary** |
| DP25-04 | Feature selector using `k`, `m`, primitive ops, peak live buffers, cache state | Corrected full regret low but focused gap has 2.174x miss; cross-machine support-only interaction | Reduce tails near `k=13..15` where volume exists | Medium; catastrophic misrouting and transfer instability | None | Train on tuning only; newly frozen circuit-held-out corpus; second machine; selector overhead | **Defer pending new corpus/workload** |
| DP25-05 | Byte/cost-aware process/disk cache | Current cache entry-LRU; synthetic all-hit pass; no access/size trace | Potentially large cold-start/family savings under skew | Invalidation, collision assumptions, concurrency, stale artifacts, RSS/disk growth | None for prototype | Real trace, byte-LRU baseline, serialize/lookup timings, RSS plateau, adversarial invalidation | **Needs real workload** |
| DP25-06 | Red-green/Salsa-like incremental pass queries | Structural DAG scaling good; family variants lack edit trace | Potential large delta-compile savings for local edits | High architecture/state/invalidation cost | None or framework prototype | Real revisions, change-impact ground truth, CSE-flat incumbent, retained bytes | **Needs real workload** |
| DP25-07 | Context cache / BDD manager reuse | Existing partial-context CM loses to strongest BitSet/ROBDD baselines | Workload-dependent | BDD order/node blow-up, manager lifetime, extraction boundary | `dd.cudd` for native study | Locality/phase/adversarial traces; build/restrict/extract separate | **Needs real workload** |
| DP25-08 | Native/JIT fused `uint64` buffers; optional ternary SIMD | Words wins only at wide boundary; current kernels not dominant for one-off calls | Possible for large repeated batches | Fixed-width semantics, warmup, copying, CPU dispatch, toolchain | Numba/native approval | Whole-call crossover, held-out batch, AVX2 fallback, memory/concurrency | **Defer** |
| DP25-09 | Independent-block factorization and lazy lift/permutation views | Exact conditional algebraic structure; materialization lower bound remains | Avoid intermediate copies; query-specific reuse | Factor detection and layout correctness; no general guarantee | None | Block-independence proof, exact layout/output, memory | **Prototype only when profiler finds material lift/permutation** |
| DP25-10 | Multiprocessing/GPU/distributed packed kernels | Existing negative evidence; admitted kernels too small; output/memory dominate | None on current workload | Startup, copy, synchronization, memory amplification, contention | Hardware/cloud | Isolated large chunk stream with cost model | **Reject as default** |
| DP25-11 | O(`s`) audit signatures instead of deep `CMNode.key` equality | EPFL validation initially became `t`-scale | Reliability and bounded verification | Low; signature must preserve ordered edges and all semantic fields | None | Cross-arm exact output and DAG checks | **Implemented in audit tooling** |

## Implemented improvement

### Correctness argument

On the default `share_aware_flatten=True` path, `_shared_assoc_uids(expr)` creates `uid_by_id` for every visited Expr object and `memo_by_uid` is initialized before `_build_rec`. Every recursive call checks that structural UID memo and every result is stored there. Therefore the separate `memo[id(expr)] -> (expr,node)` can only return the same node that the structural memo would return; it cannot add a distinct structural equivalence class or affect `no_splice`.

Removing the identity map on that path preserves:

- DFS first-encounter semantics per structural class;
- canonical splice suppression for shared associative classes;
- builder interning and node UIDs;
- live support, node fields, child order, flat lowering, and packed output.

The root argument remains live for the complete `build()` call, so id-keyed entries in `uid_by_id` cannot outlive their referents. On `share_aware_flatten=False`, there is no UID plan/memo; the identity memo remains allocated and continues holding strong Expr references for lifetime safety.

### Results

The candidate/baseline compile ratio is 0.9581 on BX1 tuning, 0.9609 on B2 reused validation, and 0.9768 on EPFL reused validation. Exact canonical DAG and packed truth mismatches are zero. The change deletes a dictionary lookup/store and a retained `(expr,node)` tuple per visited object during compile; the observed ~11.8% traced peak reduction matches that mechanism.

This is a preparation-only result. It does not change kernel speed, wrapper selection, output size, retained compiled-artifact memory, or the CM/CSE-flat claim.

## Backend selection and autotuning verdict

The corrected 401-row current policy has regret geomeans 1.0047/1.0112 for raw tuning/reused validation and 1.0030/1.0100 for CM, with no `>=2x` misses. That is adequate evidence to retain `k>=16` as the current conservative rule on admitted evidence.

It is not evidence for a universal threshold. In the focused gap study, threshold 14 improves reused EPFL but creates catastrophic misses on balanced synthetic formulas; threshold 16 produces one 2.174x CM reused-validation miss and transfers differently across hosts. A useful selector must represent at least program work/liveness and cache state in addition to `k`.

Production acceptance protocol:

1. Freeze a tuning corpus with meaningful `k=13..15` volume and a **new** circuit-held-out corpus before fitting.
2. Eligible features: `k`, `s`, `m`, primitive-op counts/mix, peak live word buffers, sharing factor, output type, expected `q`, cache warmth, family/context reuse, and `B`.
3. Train only on tuning; validate regret, max regret, `>=2x` rate, selector overhead, blocked/round-robin stability, memory refusals, and cross-machine transfer.
4. Compare all eligible task-matched arms, including CSE-flat/BitSet; do not route to BDD/SAT when a complete vector is required without including exhaustive extraction.
5. Do not integrate if the untouched gate fails even when average regret improves.

## Cache, persistence, family, and incremental reuse

The process-local structural cache is technically sound under documented constraints but economically unvalidated:

- Its association-preserving digest distinguishes sharing-aware compile regimes, prefixes flatten options, and caches only roots when shared associative context makes subtree canonicalization context-dependent.
- BLAKE2b-128 equality is an engineering collision assumption. A production content-addressed disk artifact should include schema/compiler versions and preferably store enough metadata for validation; it must not be described as formal semantic canonicality.
- The LRU is entry-count bounded, so one large artifact and one small artifact have equal eviction weight. There is no serialize/deserialize, cross-process locking, disk corruption, age, byte, or RSS policy.

Current evidence says to add telemetry before policy. Required trace fields are structural/compiler key, artifact/retained bytes, build cost, lookup/serialize cost, hit/miss/evict, process boundary, family/version/context ID, subsequent `q`, output kind, and cache budget. Evaluate no-cache, current entry-LRU, byte-LRU, and only then size/cost-aware admission. Working-set and phase-change curves matter more than a single warm hit rate.

Family/version reuse needs actual edits. The current structural cache can reuse identical subtrees, but independently regenerated “related formulas” do not reveal dependency validation or change impact. Compare cold CM, current subtree/root cache, a minimal tracked-query prototype, and sharing-aware CSE-flat. Count hashing/validation and retained state.

## Partial contexts and decomposition

For context `j`, benefit comes from reducing `k` to `k_j`, reducing `m` to `m_j`, and reusing restriction/compiled state across `q_j`; overlapping assignments help only if the implementation captures that overlap.

A proper break-even surface must vary original `k`, remaining `k_j`, contexts `c`, queries per context, overlap/locality and phase changes, output type, cache/BDD manager lifetime, and `B`. Compare:

- BitSet fixed/restricted exact output;
- CM compile-once and per-context bind/restrict;
- BDD build-once, restriction, symbolic query, and exhaustive extraction as separate rows;
- IPASIR only for SAT/model interfaces, never as a packed-output equivalent.

Independent variable blocks admit exact decomposition. If `F(X,Y)=g(F_X(X),F_Y(Y))` with disjoint supports, evaluate factor outputs and combine them with an implicit broadcast/Kronecker layout. Correctness follows pointwise: every assignment `(x,y)` maps to `g(F_X(x),F_Y(y))`. This preserves the Boolean function and, after the documented layout permutation, the same full output. It can reduce redundant intermediate construction; it cannot reduce the final `2^{|X|+|Y|}` materialized bits. Arbitrary functions need not factor, and discovering a useful exact factorization is itself nontrivial.

## Exact evaluation, memory, and native kernels

The current implementation already contains the right first-order mechanisms:

- sharing-aware CSE-flat lowering;
- cached variable environments and bound templates;
- prepared flat evaluation;
- last-use release plans;
- per-thread word scratch to avoid cross-thread overwrite while NumPy releases the GIL;
- `out=` NumPy operations and tail masks;
- output and temporary admission estimates.

Flat bigints minimize dispatch by applying each Boolean instruction to one arbitrary-precision value. Word arrays add ufunc dispatch and memory traffic and therefore win only when width is sufficient. A native/JIT implementation is credible only for a real repeated batch where preparation and conversion are amortized. It should accept a flat opcode/operand array and preallocated `uint64` buffers, fuse safe binary/ternary patterns, include AVX2 as the portable x86 baseline, optionally use AVX-512 `VPTERNLOG`, and preserve an exact scalar/reference path. Compile, cache, dispatch, copying, and conversion belong in the comparison.

Direct Numba compilation of Python bigints is rejected: nopython integers are fixed width. A `uint64[]` kernel is the only semantically suitable JIT direction.

## Layout and linear-algebra verdict

CM layout operations are exact indexing operations, not floating-point numerical linear algebra. The relevant opportunities are:

- cache permutation/lift metadata;
- apply permutations as views/index plans until the output boundary;
- combine independent blocks without materializing broadcasted operands;
- retain small pair/token surrogates where the current exact two-variable condition holds;
- preserve block symmetry/repeated substructure in symbolic IR until a complete artifact is requested.

BLAS, conditioning, mixed precision, approximate low rank, numerical tensor decompositions, and generic sparse matrix multiplication do not match the artifact. A sparse index per one bit can exceed packed storage and does not accelerate general dense Boolean truth operations. A proposed factorization must state whether it preserves the CM layout, merely the Boolean function, or a symbolic query interface.

No current profile identifies lift/permutation materialization as a dominant accepted-path cost. Therefore no layout code changed.

## Parallelism and hardware verdict

`cm_parallel` activates only above expression/element thresholds and can reuse a process pool and shared memory. Even then it copies inputs into shared segments, schedules futures, synchronizes, and copies output back. Windows process startup is particularly material; each worker can duplicate interpreter and cache state.

Parallel work should be reopened only if:

```text
T_parallel_kernel_saved > T_startup + T_serialize/copy
                        + T_sync + T_cache_contention
```

and aggregate peak memory remains within `B`. The complete-output guard keeps current admitted tasks small enough that this inequality is not demonstrated. GPU/distributed paths add transfer and remote lifecycle costs and do not change output size. Streaming/chunked output could bound peak memory, but it is a different calling contract and still performs Omega(`2^k/w`) output work.

## Negative and rejected experiments

| Candidate | Finding | Status / reopen condition |
|---|---|---|
| Optimize CM/CSE-flat residual | Accepted B1 parity; corrected structural win is workload-specific and wrapper still loses | **Rejected.** Reopen only for task-matched end-to-end reuse that repays prep. |
| Support threshold 6, 14, or 15 | Old rule caused multiple-fold misses; gap evidence transfers poorly | **Rejected.** Feature selector plus untouched validation only. |
| Broad pass fusion | No dominant duplicate traversal; attribution and canonicality risk high | **Rejected for now.** Need allocation/profile evidence for one boundary. |
| E-graph replacement | Rewrite/canonicalize too small; extraction/memory cost and artifact risk | **Rejected.** Real heavy rewrite/edit stream required. |
| Deep-key equality in validation | Became unfolded-`t` scale on sharing-heavy EPFL | **Replaced** by exact O(`s`) ordered DAG signature. |
| Smoke-only timing | 25-row ratio interval spans material regression and win | **Inconclusive.** Use for correctness/allocation only. |
| New cache admission policy | All-hit synthetic warm pass is not an access distribution | **Deferred.** Real trace and byte telemetry required. |
| CM family/context dominance | Helps CM relative to itself but loses task-matched incumbents | **Rejected on current corpus.** Real workload break-even only. |
| Direct bigint JIT | Fixed-width semantic mismatch | **Rejected.** Word-array kernel only. |
| Sparse/numerical matrix representation | Artifact and storage/operation mismatch | **Rejected** absent proven exact block sparsity. |
| Multiprocessing/GPU/distributed default | No amortizing workload; memory/output dominate | **Rejected.** Large streamed, kernel-dominant workload required. |

## Reliability and validation

- Exact output: zero mismatches across 272 BX1+B2 and 129 EPFL A/B rows, plus smoke runs.
- Canonical IR: exact ordered child-index DAG signatures matched on every A/B row without unfolding sharing.
- Cache/build path: focused persistent-path and build-memo tests passed.
- Full suite: `359 passed, 4 subtests passed`.
- Memory: compile peak fell about 11.8% under `tracemalloc`; no retained-RSS claim is made.
- Output safety: no guard was weakened and no support limit was raised. The harness used an 8 MiB temporary estimate cap and recorded refusals/skips instead of forcing allocations.
- Benchmark integrity: immutable corpus hashes and frozen truth verification come from the corrected current driver; evidence writers refuse overwrite and capture listed run-defining source bytes. The current writers include the audited transitive project modules; historical snapshots remain authoritative only for their manifest entries.

## Remaining limitations

1. No newly frozen untouched corpus exists for selector or preparation acceptance. B2/EPFL are useful external/reused checks but not held out.
2. The one-memo EPFL run used five repetitions in bounded chunks; its per-root tails are wide. The conclusion is deliberately limited to “small/noisy confirmation.”
3. `tracemalloc` does not observe every NumPy/native allocation and is not an RSS plateau measurement.
4. No real service trace describes expression versions, evaluation counts, context locality, cache working set, output types, or process restarts.
5. No approved/installed native JIT dependency or AVX-512 audit host was available, and current profiling did not justify one.
6. Process-local persistent cache concurrency and cross-process serialization are not implemented or validated.
7. Global semantic canonicality remains unproven; keys have documented engineering scope and collision assumptions.

## Recommended next work

1. Prototype compact internal canonical ordering/ranks while leaving the public `CMNode.key`, digest contracts, and exact output unchanged. Measure B2, EPFL, and high-sharing B3 with allocation and paired scheduling.
2. Decide an explicit default temporary-memory policy for local/remote APIs. Add typed refusal tests before any allocation; this is an API decision because stricter defaults can newly refuse callers.
3. Capture real cache/version/context traces with bytes, costs, output kinds, process boundaries, and reuse counts. Only then test byte-LRU, incremental queries, BDD manager reuse, or admission policies.
4. If `k=13..15` traffic matters, freeze a new tuning and untouched circuit-held-out corpus and fit a feature selector. Keep the current threshold until it clears regret, catastrophe, overhead, schedule, memory, and cross-machine gates.
5. Pursue a fused `uint64` native/JIT kernel only if the trace contains a repeated batch that makes word-kernel time dominant after preparation/output. Dependency installation requires approval.

See [CM-OPTIMIZATION-BACKLOG.md](CM-OPTIMIZATION-BACKLOG.md) for gates and [NEXT-AGENT-HANDOFF.md](NEXT-AGENT-HANDOFF.md) for exact continuation state.
