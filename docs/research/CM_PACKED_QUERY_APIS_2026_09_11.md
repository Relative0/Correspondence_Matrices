# Explicit packed query APIs

`cmbench.backends.packed_mask_cache` and `cmbench.backends.packed_queries` add
optional reusable facilities. Existing backend selection, serialization formats,
named-mask caching and output contracts keep their existing behavior. A caller
chooses a scalar count, existence decision or ordered packed stream explicitly.

```python
from cm_exprlib import And, Or, Var, Xor
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import IndependentCountPlan, PackedStreamPlan

names = tuple(f"x{i}" for i in range(24))
expr = And(Or(Var(0), Var(1)), Xor(Var(2), Var(3)))
pool = PackedMaskCache(max_bytes=2 << 20, max_width=16)

counts = IndependentCountPlan.from_expr(expr, names, cache=pool)
assert counts.count() == 6 * (1 << 20)
assert counts.count({"x0": 0, "x23": 1}) == 2 * (1 << 19)
assert counts.exists({"x2": 1, "x3": 1}) is False

stream = PackedStreamPlan.from_expr(expr, names, cache=pool)
chunks = stream.iter_chunks(chunk_vars=12, max_total_bits=1 << 24)
try:
    for chunk in chunks:
        consume(chunk.offset, chunk.valid_bits, chunk.data)
finally:
    chunks.close()
pool.clear()
```

Replace `consume` with the caller's writer or incremental processor. Calling
`list(chunks)` or joining the data deliberately retains the complete output.
The prepared program remains available for the next query. `from_cm_node` accepts
an existing CM IR node, including constants, and charges no repeated CM build.
An expression's variable `Var(i)` is named `xi` in the declared basis.

**Cache contract.** Positional columns depend on width and position, allowing
different variable names to share the same immutable Python integers. Each
`environment` returns an immutable mapping in the supplied order. Duplicate,
empty and non-string names are refused. The local LRU admits only entries whose
accounted column payload fits `max_bytes`. Payload accounting includes the width
key, column tuple and all column integers using `sys.getsizeof`; shared small
integers can be conservatively charged more than once. LRU node metadata, the
wrapper tuple and its size counter are excluded. Consequently this is a precise
admission budget, not a process-memory or allocator-RSS ceiling.

`max_width` bounds every build, including oversized entries that are returned
without admission. The largest allowed width is 30; a caller must choose an
affordable limit, since the number of bits is exponential. The default is 20.
Builds, eviction and `clear` are serialized with a reentrant lock. Readers retain
valid immutable columns after eviction or clearing; those external references
are outside the cache's budget. `stats()` reports admitted payload, hits, misses,
evictions and bypasses. Clearing resets the counters and releases owned columns.

**Count contract.** The plan peels the root conjunction into operands and joins
operands that share any syntactic support. Connected components are conservative:
overlap always merges, while semantic independence hidden inside another operator
is not discovered. Each component is evaluated exactly at its own live width.
Counts multiply across components; unused declared live axes contribute a power
of two. Fixing an unused axis removes that multiplicity. Zero-support constants
and an empty basis are valid. Existence uses exact nonzero component results and
can stop after a false component.

Every component width is checked before a query evaluates any component. A single
inseparable component follows the same exact packed evaluator; if it is wider
than `max_width`, the query raises `ValueError`. Partial assignments may bring a
wide component within budget. The current implementation does not repartition
after restriction, recognize arbitrary semantic independence, or count by SAT
approximation. This API returns an integer or Boolean, not a complete vector.

The count identity follows from a Cartesian product: once each factor has
disjoint support, choosing a satisfying assignment for one factor imposes no
condition on another. Partial assignments preserve that disjointness. Support
analysis and compilation still cost time and memory, and a single connected
factor retains the original exponential packed-table width.

**Streaming contract.** Bit `k` is assignment row `k`, with the first remaining
declared variable as the most significant assignment axis. The suffix uses
packed masks and the prefix is fixed for each chunk. Bytes are little endian;
chunk offsets and lengths are measured in bits. Chunks are byte aligned. When
the entire relation has fewer than eight bits, one byte is returned with zero
padding and its actual `valid_bits`. Fully fixed inputs return one truth bit.

`chunk_vars` must be at least three and no larger than the cache's `max_width`.
`max_total_bits` is mandatory and must admit the entire requested residual
vector. Invalid limits or fixed contexts raise when `iter_chunks` is called,
before a generator is returned. Fixed names must be in the declared basis and
values must be `0`, `1` or Python Booleans. Input mappings are copied, so later
caller mutations cannot change an active stream.

Ordering follows from `row = prefix_index * 2**suffix_width + suffix_index`.
Each chunk enumerates all suffix assignments for one prefix, and successive
prefix indices enumerate the next contiguous assignment ranges.

Each iterator has independent bindings, and bound contexts are not put in the
existing per-program cache. The working allocation scales with the selected
chunk width and program size; total enumeration time and delivered bytes still
scale with the complete output. Early consumers should close the generator.
Plans support concurrent queries while sharing the synchronized column cache;
callers must not mutate internal compiled programs.

**Validation and adoption.** The new tests exhaust all 256 Boolean functions on
three variables and all 27 partial assignments; random shared DAGs cover every
operator, CM normalization, reordered/unused variables, zero-width output,
chunk boundaries, concurrency, early close and cache release. The local panels
separate uninstrumented timing from allocation tracing, compare direct packed,
structural CSE-flat and portable `dd.autoref` controls, and preserve unfavorable
single-component and small-chunk outcomes. Synthetic wins alone do not admit a
new production selector or establish application prevalence. Final measured
results are recorded in the continuation report.
