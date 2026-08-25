# Correspondence Matrix Deep Performance Research and Implementation Audit

Audit date: 2026-08-24
Repository: `C:\Users\brian\Documents\CM_Computation`
Frozen starting revision: `main` at `6fe11d713cae39e56cd3251cca8e8ceb9cc5578f`

> **Correction, 2026-08-25:** B2 and EPFL are reused selection-validation data,
> not untouched held-out data. The original EPFL benchmark driver also failed to
> assert the frozen truth digest in the corpus's original variable order. The
> corrected 401-row replay verifies every frozen digest and all timed-arm outputs.
> A matched 264-row successor now uses sharing-aware CSE-flat as the primary
> comparator. See `deliverables_n22_24/corrections_2026_08_25/CM_BENCHMARK_AUDIT_CORRECTION_REPORT_2026-08-25.md`.

## Executive conclusion

The audit found one material routing defect and one small repeated-traversal cost worth changing. It did not find evidence for a new CM-specific kernel advantage, an algebraic shortcut for complete exact output, or a current reason to add JIT, native SIMD, e-graphs, GPU, multiprocessing, or a new cache policy.

Implemented:

1. Automatic packed-engine routing now keeps the flat Python-bigint kernel through `live_k=15` and selects NumPy `uint64` words at `live_k>=16`. The former `k>=6` rule incurred geometric-mean regret of 2.06 on frozen BX1 tuning and 2.72 on reused-validation raw-AST rows, with catastrophic regret (`>=2x`) on 39/80 and 197/307 rows. The `k>=16` policy reduced these to 1.011 and 1.014, with zero catastrophic rows. CM-node results tell the same story.
2. Immutable CM-IR roots cache their DAG node count. A call falls from a corpus-median 5.7/7.8/15.5 microseconds cold to 0.3-0.4 microseconds warm on BX1/B2/EPFL. The no-reinflate budget path also computes the count once instead of twice. This is an algorithmic removal of repeated full-DAG traversals; no noisy wrapper-level speedup is claimed.

The dominant unresolved cost remains CM preparation. Fresh phase instrumentation places interning at roughly 21-25% of compile time, live-variable analysis at 11-13%, hashing at 9-12%, lowering at 10-13%, rewriting at 7-9%, and canonicalization at 6-7%. No single duplicate pass dominates enough to justify a broad fusion rewrite. Accepted B3 evidence remains controlling: preparation tracks structural DAG size `s`, not unfolded tree size `t`, and is about 4.3x the fair comparison compiler in aggregate.

Complete exact truth-vector output remains output-bound. Returning the same packed artifact requires at least `2^k/w` machine words of work and storage; no tensor, BDD, SAT, cache, or compiler technique removes that lower bound. Those methods can win only for a different query artifact, decomposable inputs, repeated related inputs, or partial contexts.

## Repository preservation

The audit began on branch `main`, HEAD `6fe11d713cae39e56cd3251cca8e8ceb9cc5578f`. Pre-existing modified README and website/explainer files and the pre-existing untracked `.claude`, `external`, `tmp`, and website-UX items were recorded before work and left untouched. No secret file was read. No dependency was installed. Nothing was staged, committed, pushed, deployed, or sent externally.

The available project runtime was `.venv\Scripts\python.exe`, CPython 3.13.5, with NumPy 2.3.2, pandas 2.3.2, SymPy 1.14.0, `dd` 0.6.0, and Requests 2.34.2. The virtual environment had no pytest or Numba. Tests therefore used the already-installed global CPython 3.10.11/pytest 9.0.2; benchmarks used the project virtual environment.

## Authoritative starting evidence

The requested documents were read in the prescribed order. This audit preserves their accepted dispositions:

- On the accepted B1/E3 workload, CM and sharing-aware CSE-flat were at parity: external ratio 0.9998 with interval [0.9747, 1.0249]. This is workload-specific, not a universal equivalence claim.
- CM's earlier advantage over plain CSE was principally flattening/merging. The corrected B2/B4 successor finds a smaller additional CM reduction: bare CM/CSE-flat geomean 0.909 overall, accompanied by about 5% fewer instructions and 7% fewer primitive operations; at `k=16` the timing ratio is 0.979. The public CM wrapper remains much slower, so this is not an end-to-end dominance result.
- BitSet wins the measured whole-call exact-output workload through `live_k=16`.
- CM preparation is the leading CM cost and is about 4.3x the comparison compiler in accepted aggregate evidence.
- B3 shows structural-DAG scaling: an 8.39-million-occurrence shared ladder with 77 structural nodes compiled in 985 microseconds, while unshared trees grew approximately with structural nodes.
- BX1 directly sampled `k` in `{2,3,4,5,6,7,8,10,12,16}`. Flat was still 2.7x faster at `k=12`; words became fastest at `k=16`. There was no direct evidence for `k=13..15`.
- Family caching and partial contexts help relative to uncached CM but do not beat the strongest measured baseline. Shared-block family cache speedups reached 1.18-1.30x (up to 1.39x in a size sweep), while cached CM remained about 11.7-46.3x slower than BitSet. For 100 partial contexts, cached CM improved 2.05-4.39x over uncached CM, but BitSet and ROBDD restriction remained faster.
- CUDD construction, canonical BDD structure, restriction, and truth-table extraction are different artifacts and timing windows.
- CM quotient is a directional CM-feature artifact, not semantic XOR.
- Engineering keys under documented normalization are not a proof of global canonical CM equivalence.

No new result in this audit changes those statements.

## Execution and reuse map

| Stage | Main implementation | Cost frequency | Retained/reused state |
|---|---|---|---|
| Expression creation/parsing | `cmbench/expr`, `cm_exprlib.py`, benchmark corpus deserialization | Once per source expression | Expression DAG objects |
| Stable serialization | `cm_expr_serde.py` | Once per persistence/transport operation | JSON DAG text or bytes |
| Structural digest | `cm_ir.expr_structural_hash` | Once per persistent-cache probe/subtree | Digest keys |
| Adoption, normalization, canonicalization | `CMIRBuilder`, `compile_expr_to_cm_ir` in `cm_ir.py` | Once per cold expression; repeated for uncached variants | Intern tables during the build |
| Algebraic rewrite and interning | `CMIRBuilder._build_rec`, `make_*`, `_intern` | Once per visited structural node/subexpression | Shared immutable `CMNode` DAG |
| Live-variable analysis | CM-node construction and ordered live-variable tuples | Once per IR node/build | Tuples retained on nodes |
| Flat lowering | `compile_flat`, `compile_expr_flat`, `get_flat_program` in `bitset_backend.py` | Once per cold program; cached thereafter | `FlatProgram`, slot/liveness plan |
| Backend selection | `cmbench/backends/bitset_engine.py` | Once per evaluation/wrapper call | Constant-width policy; no learned model |
| Bigint evaluation | recursive and flat evaluators in `bitset_backend.py` | Once per evaluation | Environment LRU, bound-input cache |
| Word evaluation | `_eval_words`, raw/CM words wrappers | Once per evaluation | Four-entry words-env LRU; per-thread scratch by program/width |
| Materialization/conversion | `materialize_ir`, `materialize_hybrid_no_reinflate`, `cm_build.py` | Once per requested output | Returned dense, hybrid, or packed artifact |
| Output admission | `cmbench/output_budget.py` and no-reinflate wrapper | Once per requested output | Budget decision only |
| Process-local identity cache | compiled IR LRU | Once per cache lookup; reusable within process | 4,096 entries |
| Structural persistent cache | `compile_expr_to_cm_ir_persistent` | Per subtree probe across related expressions | 16,384 entries, process-local despite the name |
| Alignment/normalization caches | `cm_normalize.py`, CM alignment | Per alignment/key lookup | Bounded LRUs, including 4,096 alignment entries |
| Family workload | expression-family benchmark path | Once per family plus once per variant | Persistent subtree cache and optional shared backend state |
| Partial contexts | fixed bindings in no-reinflate and ROBDD `let` | Once per context plus evaluations within it | Compiled IR/BDD reused across contexts |
| Parallel/remote | `cm_parallel.py`, remote benchmark worker | Per submitted job/request | Process/thread state; words scratch is thread-local |

The complete path is:

```text
source/JSON DAG
  -> Expr DAG
  -> structural digest / cache probe
  -> CMIRBuilder adoption + canonicalization + rewrite + interning
  -> immutable CMNode DAG with live-variable metadata
  -> flat program and liveness/scratch plan
  -> output-budget admission and engine selection
  -> flat bigint or uint64-word kernel
  -> packed/dense materialization and conversion
  -> validation/serialization when requested
```

The flat program, CM node, node count, environments, and scratch plans are legitimate reuse units. A complete output vector is not reusable across changed expressions or contexts unless its exact semantic key and ordering match.

## Formal cost model

Definitions:

- `s`: structural DAG nodes.
- `t`: unfolded tree occurrences.
- `k`: semantic/live support.
- `m`: executed compiled Boolean operations.
- `q`: repeated evaluations of one compiled expression.
- `f`: related expressions/versions in a family.
- `c`: partial contexts.
- `w`: machine word width, 64 for the words path.
- `B`: cache or admitted-memory budget.

For one expression:

```text
T_prepare(s,t,m) = T_parse + T_hash + T_adopt + T_canonicalize
                 + T_rewrite + T_intern + T_live + T_lower

T_eval(k,m,w)    = T_dispatch + T_bind + T_kernel(k,m,w)
                 + T_materialize(k) + T_convert(k)

T_total          = T_prepare + T_cache_lookup/persist
                 + q * T_eval
```

For the current sharing-aware compiler, measured scaling supports treating `T_prepare` primarily as a function of `s` and operator arity, not `t`. For an explicit packed kernel, `T_kernel` is approximately `Theta(m * 2^k / w)` word/limb work, subject to interpreter/vector dispatch constants and buffer liveness.

For related expressions:

```text
T_family = T_prepare(base)
         + sum(i=1..f) [T_change_impact(i) + T_cache(i) + T_delta_prepare(i)]
         + sum(i=1..f) q_i * T_eval(i)
```

An incremental method is useful only if `T_change_impact + T_delta_prepare + T_cache` is smaller than cold preparation and the retained state fits `B`. Current family traces establish reuse but not a win over BitSet.

For partial contexts:

```text
T_contexts = T_prepare
           + sum(j=1..c) [T_restrict(j) + q_j*T_kernel(k_j,m_j,w)
                          + T_output(k_j) + T_context_cache(j)]
```

Break-even depends on original `k`, remaining `k_j`, overlap/locality, context count, requested output, and whether a BDD manager or compiled program is already warm. The accepted measurements show that compile-once CM amortizes, but BDD restriction and BitSet are still stronger at the tested sizes.

Memory separates retained and temporary components:

```text
M_retained = M_expr + M_ir + M_program + M_env_LRU + M_compiled_LRU
           + M_persistent_cache + M_thread_scratch

M_temporary_words = Theta((k + b) * 2^k / w) words
M_output_packed   = Theta(2^k / w) words
M_output_dense    = Theta(2^k) elements
```

Here `b` is the peak number of live scratch buffers determined by program liveness. A complete packed result requires `Omega(2^k/w)` work and storage simply to represent/return all bits. A dense result requires `Omega(2^k)` elements. A BDD, SAT solver, factorization, or query oracle can be sub-exponential for favorable structure only by returning a different artifact or answering selected queries rather than emitting the complete vector.

## Fresh research synthesis

The web review was performed on 2026-08-24. Full source-by-source decisions are in `CM-RESEARCH-LEDGER.md`.

### Preparation and incremental compilation

Rust's incremental compiler uses stable fingerprints and a dependency graph, while explicitly noting that stable hashing can itself make incremental compilation slower. Salsa's red-green query model similarly helps when tracked inputs change locally and repeated queries reuse dependency results. These mechanisms match a versioned family service, not isolated expressions, and need representative edit traces before implementation. See the [Rust incremental compilation guide](https://rustc-dev-guide.rust-lang.org/queries/incremental-compilation-in-detail.html) and [Salsa algorithm reference](https://github.com/salsa-rs/salsa/blob/master/book/src/reference/algorithm.md).

`egglog` combines equality saturation and Datalog-style incremental execution and is credible for workloads with many interacting rewrites. Current profiling does not show canonicalization/rewrite as a dominant isolated cost, and the corrected matched comparison shows only a workload-specific bare-kernel benefit that does not overcome the measured preparation/wrapper boundary. Integration is therefore rejected for the current output workload, not as a general compiler technique. See the [PLDI 2023 egglog paper](https://www.mwillsey.com/papers/egglog) and the newer speculative [persistent e-graph compiler preprint](https://arxiv.org/abs/2602.16707).

Content-addressed compiler caches such as LLVM ThinLTO combine compact summaries with bounded cache pruning. CM's structural cache has the content key but only entry-count limits and no disk artifact, byte telemetry, or pruning policy. The missing piece is a real multi-process/version working-set trace, not another cache algorithm in isolation. See [LLVM ThinLTO cache documentation](https://clang.llvm.org/docs/ThinLTO.html) and the foundational [TinyLFU admission paper](https://arxiv.org/abs/1512.00727).

### Exact packed evaluation

CPython implements integers as arbitrary-precision limb arrays, making the flat-bigint path a compact native C loop over a whole truth vector. This explains why it wins while only a few limbs are needed; the [CPython long implementation](https://github.com/python/cpython/blob/main/Objects/longobject.c) is the relevant maintained source.

NumPy supports runtime CPU dispatch and universal SIMD intrinsics, so current `uint64` ufuncs can already reach architecture-specific vector loops without handwritten CM intrinsics. Intel's instruction set includes ternary Boolean operations such as `VPTERNLOGQ`, but exploiting them requires fusing three-input instruction patterns and avoiding temporary arrays. The present profile does not show enough kernel time or a stable operator-mix payoff to justify a native extension. See [NumPy CPU/SIMD optimization](https://numpy.org/doc/stable/reference/simd/index.html), the [Intel Intrinsics Guide](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html), and [Intel ternary logical intrinsics](https://www.intel.com/content/www/us/en/docs/cpp-compiler/developer-guide-reference/2021-9/intrinsics-for-logical-operations.html).

Numba 0.66 supports this Python/NumPy range, but it maps arbitrary Python integers to fixed machine integers. A direct JIT of the current bigint artifact would therefore change semantics; only a word-array kernel is a candidate. Numba is not installed, and compilation/dispatch/conversion have not been amortized by a demonstrated batch workload. See the [Numba version support table](https://numba.readthedocs.io/en/latest/user/installing.html) and [integer semantic differences](https://numba.readthedocs.io/en/0.61.0/reference/pysemantics.html).

### CM layout and algebra

CM layout operations are exact reshape, lifting, alignment, and permutation operations over the truth tensor. NumPy's Kronecker product explicitly materializes a product-shaped array whose element count multiplies. Kronecker or block factorization helps only when a function decomposes across independent variable blocks and remains decomposed under the requested operation. Arbitrary Boolean composition destroys that condition, and detecting/factoring an arbitrary result is additional work. See [NumPy `kron`](https://numpy.org/doc/2.0/reference/generated/numpy.kron.html) and [SciPy sparse arrays](https://docs.scipy.org/doc/scipy/tutorial/sparse.html).

Therefore:

- lazy views and cached permutations are useful for avoiding intermediate copies and are already the appropriate direction;
- factorized outputs would be a different artifact unless the caller accepts a structured representation;
- approximate low-rank, mixed precision, BLAS, and numerical conditioning do not match exact Boolean semantics;
- there is no credible algebraic route around complete-output enumeration for arbitrary functions.

### Partial contexts and symbolic alternatives

CUDD provides shared reduced ordered BDDs, cofactoring/restriction, dynamic reordering, and computed caches. The maintained `dd` interface exposes `let` for cofactors and near-identical pure-Python/CUDD APIs. This is artifact-matched for symbolic build/restrict queries, not for exhaustive truth-vector extraction. See the [CUDD manual](https://add-lib.scce.info/assets/documents/cudd-manual.pdf) and [`dd` documentation](https://github.com/tulip-control/dd/blob/main/doc.md).

IPASIR assumptions support repeated SAT solves under changing assumptions while retaining a clause database. They answer satisfiability/model queries, not complete truth vectors, so they are relevant only if the product interface changes to queries. See the [IPASIR incremental interface](https://satcompetition.github.io/2021/track_incremental.html).

## Fresh profiling

The final replay contains 401 immutable-corpus expressions: BX1 80 tuning rows and B2+EPFL 321 reused selection-validation rows. Each preparation phase used three repetitions. Kernel comparisons used five alternating paired rounds and size-dependent batches. The corrected replay verifies every frozen digest and every eligible packed raw/CM flat/words and wrapper result.

Median phase fractions of cold external CM compilation:

| Corpus | hash | canonicalize | rewrite | intern | live vars | lower |
|---|---:|---:|---:|---:|---:|---:|
| BX1 | 11.7% | 5.7% | 7.6% | 22.7% | 10.6% | 12.8% |
| B2 | 10.2% | 6.2% | 8.9% | 21.5% | 12.3% | 10.9% |
| EPFL | approximately 9-10% | approximately 7% | approximately 8% | approximately 24-25% | approximately 11-12% | approximately 10-11% |

Absolute B2 medians were about 44 microseconds for hashing, 24 for canonicalization, 37 for rewriting, 93 for interning, 53 for live-variable analysis, and 43 for lowering in the stable instrumented replay. EPFL has a much wider tail: accepted raw corpus rows include structurally larger cones, and p90 phase costs are several hundred microseconds to over a millisecond.

The stored cProfile smoke trace is diagnostic rather than a benchmark timing source. It attributes the CM compile body primarily to `_build_rec`, `make_xor`, interning, shared-associative UID handling, and live-variable unions. Words evaluation executes NumPy kernels but pays fixed plan/environment/scratch overhead. CLI/import profiling from the prior audit remains relevant: imports and workflow discovery dominate very small command invocations, but lazy-importing the large benchmark CLI is broad and not justified by the scoped production paths.

A fresh allocation-instrumented B2 cache probe gives the cache boundary separately: 192 cold expressions created 1,368 entries with 1.31 MiB traced retained growth; an immediate second pass had 192 root hits, no misses, and a 0.263 warm/cold paired geomean. Absolute medians (2.887 ms cold, 0.810 ms warm) include tracemalloc overhead. This confirms warm reuse without supplying the real hit distribution or byte-budget enforcement needed for a production cache-policy change.

No phase contributes enough alone to support a risky compiler-pass fusion. Interning is the largest lane and remains the best preparation research target, but changing key representation or node layout needs a dedicated A/B implementation and retained-memory measurement.

## Ranked findings and decisions

| ID | Priority | Mechanism/evidence | Affected code | Expected effect | Risk | Decision |
|---|---|---|---|---|---|---|
| CM-DP-01 | P1 | Historical `k>=6` words dispatch causes 2-9x regret on many rows | `cmbench/backends/bitset_engine.py` | Remove catastrophic routing at current supported widths | Low; exact kernels already cross-check | Implemented at `k>=16` |
| CM-DP-02 | P2 | Output admission traverses immutable CM DAG repeatedly for node count | `cm_ir.py` | Save one or more `O(s)` traversals per warm root | Low; derived immutable metadata | Implemented |
| CM-DP-03 | P1 | Raw flat temporary arrays can exceed safe local memory when source protocol is ignored | audit harness; callers of raw evaluator | Fail closed before experimental allocation | Low in harness; production default-policy change is API-sensitive | Harness implemented; production policy deferred |
| CM-DP-04 | P1 | Preparation remains about 4x comparator; interning is largest measured phase | `CMIRBuilder`, canonical keys | Potential constant-factor compile reduction | High correctness/identity risk | Prototype compact key/node layout only with paired family/EPFL traces |
| CM-DP-05 | P2 | Persistent cache is entry-bounded, not byte-bounded; no disk/cross-process reuse | `cm_ir.py`, cache APIs | Better RSS control and cold reuse if real hits exist | Invalidation, storage, security, telemetry | Needs real version/edit trace |
| CM-DP-06 | P2 | Related-family cache helps CM 1.18-1.39x but is far behind BitSet | family benchmark and cache | Possible service workload benefit | Workload dependent | Defer pending real families |
| CM-DP-07 | P2 | Partial restriction amortizes compile but loses to BitSet/ROBDD at tested sizes | partial-context path | Possible win for much larger/context-heavy queries | Different artifacts; order sensitivity | Keep task-matched selector explicit; no CM change |
| CM-DP-08 | P3 | Numba/native SIMD may fuse word operations | word evaluator | Possible large-batch kernel gain | New dependency/toolchain; compile/conversion overhead | Needs a repeated batch with kernel-dominant profile |
| CM-DP-09 | P3 | E-graphs/incremental query systems can reuse edits | compiler/cache | Possible related-version preparation gain | Major architecture and memory cost | Reject for isolated exact-output work; research for real edit streams |
| CM-DP-10 | P3 | Tensor/Kronecker factorization | layout/materialization | Only decomposable functions/structured outputs | Changes artifact or adds factorization cost | Theoretically blocked for arbitrary complete output |
| CM-DP-11 | P3 | Multiprocessing/GPU/distributed execution | parallel/remote | Possible very large chunk workloads | Startup, copy, memory amplification | Rejected for current guard/workloads |

## Implemented improvements

### Width-safe backend selection

`WORDS_AUTO_MIN_VARS` is now 16. Explicit direct requests for the words evaluator retain the existing minimum representation behavior; only automatic routing changed. The selector remains a constant-time, zero-allocation width test.

The choice is intentionally conservative. BX1 directly measured `k=12` and `k=16` but not the gap. An initial `k=13` interpolation was tested and rejected after one reused-validation replay produced a raw-AST 2.18x misroute. The final implementation uses the directly observed endpoint rather than treating missing `k=13..15` tuning cells as evidence.

Final authoritative policy regret:

| Arm/role | Old `k>=6` geomean regret (cluster 95% CI) | Old catastrophic | New `k>=16` geomean regret (cluster 95% CI) | New catastrophic | New max |
|---|---:|---:|---:|---:|---:|
| raw / BX1 tuning | 2.06 [1.80, 2.16] | 39/80 | about 1.01 [about 1.00, 1.02] | 0/80 | below 1.5x in repeated final runs |
| raw / B2+EPFL reused validation | 2.72 [2.49, 2.99] | 197/307 | about 1.01 [about 1.00, 1.03] | 0/307 | below 2x in the authoritative run |
| CM / BX1 tuning | 1.89 [1.66, 2.00] | 38/80 | about 1.01 [about 1.00, 1.02] | 0/80 | about 1.3x |
| CM / B2+EPFL reused validation | 2.37 [2.19, 2.55] | 197/321 | about 1.01 [about 1.01, 1.02] | 0/321 | about 1.6x |

Ratios vary modestly between whole replays because kernels are short, but the old rule's failure and the conservative rule's direction are stable. All raw threshold results exclude 14 EPFL rows in accordance with explicit protocol/memory outcomes; CM has all 321 reused-validation rows.

### Immutable node-count memoization

`_cm_node_count` stores `_node_count` on the frozen root after the first traversal. The value is safe because `CMNode` arguments are immutable. `materialize_hybrid_no_reinflate` also binds the value once when constructing full/reduced estimates.

| Corpus | median IR nodes | cold count | warm count | warm/cold geomean |
|---|---:|---:|---:|---:|
| BX1 | 13 | about 5.7 us | 0.3-0.4 us | about 0.06 |
| B2 | 20 | about 7.8 us | 0.3-0.4 us | about 0.05 |
| EPFL | 53 | about 15 us | about 0.3 us | about 0.02 |

The regression test asserts that the first call sets the derived field and later calls return the same value. The optimization affects budget/wrapper overhead, not Boolean semantics or cache identity.

## Correctness, memory, and reliability validation

- Exact packed equality was asserted across raw flat, raw words, CM flat, CM words, and the no-reinflate wrapper for every eligible record.
- The final replay recorded 387 eligible raw rows, 10 source-protocol skips, and 4 explicit temporary-budget refusals. There were no silent omissions.
- EPFL syntactic support differing from semantic support is represented with fixed dead inputs; the harness refuses inconsistent mappings.
- The harness defaults to a finite 256 MiB experimental temporary budget and the final run used 8 MiB. It refuses overwrite and writes raw data, summary, phase, selector, and environment sidecars.
- At `k<=16`, exact packed output is at most 8,192 bytes. Recorded maximum estimated CM word scratch was roughly 57 KiB for BX1, 72 KiB for B2, and 468 KiB for EPFL; a `k=16` words environment is 128 KiB.
- A failed early research replay that ignored EPFL's source `raw_arm` protocol approached 2 GiB RSS. It was stopped without writing partial artifacts. The final harness honors protocol skips before raw lowering/evaluation and adds temporary admission. This validates the need for fail-closed experimental drivers.
- Production output budgets allow callers to specify temporary limits, but some defaults remain `None`. Changing that public policy could newly refuse existing callers, so it is documented as follow-up rather than silently imposed.

Focused tests pass. The first full-suite attempt produced 325 passes and 20 setup errors because sandboxed pytest could not access its default global temp root. The same suite with an audit-local writable `--basetemp` passed: 345 tests plus 4 subtests in 114.05 seconds.

## Negative and rejected experiments

- **`k=13` interpolation:** rejected. It was not a measured BX1 cell and showed unstable reused-validation tail behavior. `k=16` is the directly supported conservative endpoint.
- **Broad compiler-pass fusion:** rejected for now. Timing is distributed across interning, live-variable analysis, lowering, hashing, rewriting, and canonicalization; no duplicated traversal accounts for a dominant fraction.
- **CM-vs-CSE-flat residual optimization:** not justified end-to-end. The corrected successor finds a modest bare-kernel reduction on B2/B4, especially at small `k`, but near parity at `k=16`; preparation and wrapper costs still control the complete workflow.
- **JIT of Python bigints:** semantics mismatch because Numba uses fixed-width integers. A word-array JIT needs a separate batch crossover study and dependency approval.
- **Handwritten SIMD/ternary fusion:** not justified. NumPy already dispatches SIMD, and present workload sizes are dominated by fixed overhead until `k=16`.
- **Kronecker/tensor shortcut:** rejected for arbitrary complete outputs. Factorization requires decomposable inputs or a structured-output contract and does not remove the output lower bound.
- **E-graph canonicalization:** rejected for isolated expressions. It adds major state/maintenance for rewrite work that is not the dominant measured phase and has no demonstrated downstream kernel win.
- **New cache eviction policy:** deferred. TinyLFU/byte pruning cannot be judged without a real size-weighted access trace, cold/warm hit rates, and an RSS plateau.
- **CM family/partial-context advantage:** not established against task-matched baselines. Keep the existing negative results.
- **Multiprocessing, GPU, and distributed execution:** rejected for current exact-output sizes; earlier activation/amortization evidence is negative and memory duplication is hazardous.
- **Operator quotient as XOR:** rejected as an artifact mismatch.

## Remaining limitations

- Tuning has no direct BX1 observations for `k=13..15`; the selector deliberately waits until 16. A future corpus may support an instruction-count-aware crossover in the gap.
- Results are one Windows/AMD machine. The threshold must be revalidated before becoming a universal cross-platform rule.
- Cluster-bootstrap intervals cover formula/circuit clusters in this corpus, not hardware/process replication.
- Cache entry limits are not byte budgets and no cross-process persistent artifact exists.
- The final explicit-output guard is still `k<=16` in accepted studies; this audit makes no claim above it.
- CUDD available through the installed `dd` package was not re-benchmarked here; accepted task-matched reports remain authoritative.
- The benchmark virtual environment lacks pytest and the global test runtime differs from the performance runtime.

## Recommended next work

1. Capture a real service trace containing expression versions, repeated evaluations, partial contexts, output type, cold/warm state, and cache resident bytes. This is prerequisite to cache or incremental-compiler work.
2. If production sees many calls in `k=13..15`, create a frozen, cross-machine corpus at those exact widths and tune a low-cost feature model using `k`, executed operations, and peak live word buffers. Validate on a separate circuit corpus and report regret/tails.
3. Prototype a compact interning key/node representation in isolation. Gate it on exact structural hashes/truth vectors, cold compile time, allocations, and retained cache bytes across B2 plus EPFL.
4. Decide an explicit production temporary-memory contract. Once the refusal schema and default budget are agreed, apply it uniformly to raw, CM, local, and remote paths.
5. Consider native/JIT word fusion only after a real repeated batch makes kernel time dominant and dependency/toolchain approval is available.

The detailed category backlog and exact next-agent prompt are separate deliverables.
