# Memory-path map

## Measurement vocabulary

Output bytes are logical artifact bytes, excluding Python headers. Legacy temporary bytes are an admission heuristic. Tracemalloc measures allocations visible to Python, including NumPy allocations only insofar as that build exposes them. RSS/current working set includes interpreter, libraries, allocator arenas, native storage and retained caches. OS lifetime high-water is not a window peak; its delta must not be called temporary allocation.

s is unique CM DAG nodes; expression_s is serialized structural nodes; m is flat instructions. The driver also records argument edges, primitive operations, scratch-buffer count, fixed support and live_k. Its k is requested output width after the declared context, which can exceed simplified live_k.

## Boundaries

| Boundary | Check and storage behavior | Coverage / limitation |
|---|---|---|
| compile_expr_to_cm_ir / compile_expr | Structural compilation, intern/memo/cache allocations precede output admission | Output policy does not budget preparation; a successful compiled cache entry retained after output refusal is not a failed artifact |
| materialize_cm | Estimate/check before _materialize_ir_tagged; target R+C fixes explicit width | Dense memo arrays, alignment views, ufunc results and final copy exceed the old two-buffer model |
| materialize_hybrid_no_reinflate | Fast and diagnostic paths check full/reduced output before engine or dense fallback | Packed vs dense depends on hybrid threshold, not merely words flag; refusal diagnostics corrected |
| eager/lazy public builders | Compile then forward budget to materialize_cm | Tiny sentinel tests prove refusal before material arrays |
| pair builder | One public dense check; internal fallback deliberately passes None | Estimator ignores pair recursion/operator slots; internal fallback is protected only by outer check |
| parallel builder | Delegates to materialize_cm before combine callback creates a pool | Refusal-before-pool tested with sentinels; no per-call temporary parameter or aggregate worker-memory model |
| flat bigint | Bound masks/template cache; values copy, bigint temporaries; optional last-use release | Direct evaluator has no OutputBudget; driver guards it explicitly and labels that boundary |
| words | Bigint masks plus read-only word views, per-thread scratch by width, constants, tobytes and PyLong return | Direct words calls below k=6 are bigint fallback; automatic public routing still switches at k=16 |
| materialize_ir | Memoized arrays and views, exact fixed contexts | Lower-level public function has no independent budget parameter |
| bitset_to_bool_array/hypercube | Packed bytes, unpackbits storage, optional Boolean copy | No independent budget; guarded parent or caller preflight required |
| equivalence | Existing benchmark refusal status handling | Tiny existing refusal test retained; no equivalence performance claim |
| result_payload / dumps_json | Hex string or list/summary; JSON bytes are separate allocations | Result guard does not cap serialization expansion or request-body bytes |
| remote worker / mock | Validates limits, compiles, evaluates, then serializes; refuses with no result | Numeric validation now precedes compile. No pod needed for protocol fixtures |

## State and failure findings

Confirmed before the fix: reused diagnostics could still say ok and report a previous bitset after refusal. Dense calls updated budget status but retained prior final-output fields. Also, a full-output refusal could report the unused reduced estimate even when reduction was disabled. Both are corrected without changing decisions.

Tests guard allocation/binding/pool/serialization entry points with failure sentinels. Refused packed calls do not fill bound masks, word plans or word scratch. Compile-derived node-count metadata and successfully compiled IR are intentionally distinct from a retained failed evaluation memo.

No full regression or aggregate RSS plateau was run. Arbitrary malformed-program cache behavior, independent low-level conversion budgets, parallel memory amplification and HTTP body admission remain explicit gaps; no blanket all-boundaries safety claim is made.
