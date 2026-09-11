# Exact counts with bounded CNF elimination

`BucketCNFCountPlan` counts all satisfying assignments to a declared basis. It supports overlapping clauses when an admitted elimination order keeps intermediate tables narrow. It returns an arbitrary-precision integer; `exists` returns a Boolean. It is opt-in and does not produce a truth vector or select a backend automatically.

```python
from cmbench.backends.bucket_counts import BucketCNFCountPlan

# a implies b, b implies c, and c implies a: all values must agree.
plan = BucketCNFCountPlan([(-1, 2), (-2, 3), (-3, 1)], ('a', 'b', 'c'))
assert plan.count() == 2
assert plan.count({'a': 1}) == 1
assert not plan.exists({'a': 0, 'c': 1})
```

Literal `i` means the positive variable at basis position `i-1`; `-i` means its negation. Zero is a DIMACS terminator, not a constructor literal. Names must be unique nonempty strings. Fixed values must be Boolean 0/1, and every fixed name must be declared. Unused free variables multiply the count; fixed unused variables do not. Contradictory clauses/units return zero, and an empty conjunction has one model per assignment of its free basis.

`from_cnf(clauses, names, **limits)` is equivalent to the constructor. `from_expr(expr, names, **limits)` and `from_cm_node(node, names, **limits)` accept syntactic CNF: a conjunction of disjunctions of literals/constants. They recognize existing AND/OR flattening and simple negated literals, but do not distribute arbitrary formulas or introduce auxiliary variables. Non-CNF expressions are refused. Expression/CM compilation precedes clause admission and has its own costs.

`parse_dimacs(text, max_bytes=1<<20, max_vars=2048, max_clauses=16384)` returns `(variable_count, clauses)`. It supports comments, clauses spanning lines, and multiple terminated clauses on one line. It checks the header, literal range, declared clause count and incomplete records. It counts every declared CNF variable, including auxiliaries and unused positions; this does not automatically equal a projected count of product configurations.

The constructor performs exact unit propagation and retains forced values. It then chooses either `order='natural'` or the default `'min_fill'`, with basis-position tie-breaks. Min-fill is a heuristic; it does not promise an optimal treewidth. `stats['width']` counts all variables in the largest elimination bucket, including the eliminated variable. It is one greater than that bucket's neighbor count.

Every clause starts as a Boolean table. At each scheduled step, input factors are multiplied at matching assignments and the eliminated variable is summed out. A fixed value selects only its corresponding branch. All intermediate values are exact Python integers. Consumed query intermediates are released; the original tables and schedule remain in the plan. Queries do not change the schedule, mutate input tables, share scratch, or cache answers, so independent read calls can use the same plan concurrently.

Resource admission is explicit:

| Constructor option | Default | Meaning |
| --- | ---: | --- |
| `max_width` | 14 | Maximum clause or elimination bucket width; at most 20 may be requested |
| `max_cells` | 1,048,576 | Bound on retained input cells plus live query intermediate cells, including the next output |
| `max_work` | 16,777,216 | Conservative table/projection work estimate for the static schedule |
| `max_order_checks` | 2,000,000 | Bound on candidate neighbor-pair checks during min-fill ordering |
| `max_vars` | 2,048 | Declared basis limit |
| `max_clauses` | 16,384 | Input clause limit before deduplication |

Total input literal consumption is additionally capped at 1,048,576. `CountPlanLimit`, a `ValueError` subclass, reports an admission failure. The complete schedule is checked before allocating truth/count tables. Limits count table entries and ordering work, not allocator RSS, Python container bookkeeping or expression-ingress memory. Integer entries can grow with the number of eliminated variables; the variable limit bounds their possible bit length. Larger limits can increase both preparation and query costs sharply.

The research campaign intentionally uses tighter table/work settings than the constructor defaults. It compares full model counts against native CUDD and preserves models that exceed the limits. See the [prospective plan](CM_BUCKET_COUNT_PLAN_2026_09_11.md) and its audit report for measured applicability; narrow overlap is a prerequisite, not a guarantee that this Python implementation beats a symbolic counter.

The independent research helper `exact_cudd_count(manager, root)` in `cmbench/comparative/exact_cudd_count.py` traverses CUDD with arbitrary-precision arithmetic and explicit complemented-edge handling. It counts all manager-declared variables and requires the manager to remain stable during traversal. Its visited-node memory is linear in the traversed diagram and needs a separate native/process bound. It avoids rounding counts such as `2**100 - 1` through floating point.

## Optional object-array execution

`NumpyBucketCNFCountPlan` in `cmbench/backends/bucket_numpy.py` implements the same exact count/fixed-context contract and the same `from_cnf`, `from_expr` and `from_cm_node` factories. It can also wrap an existing `BucketCNFCountPlan` directly:

```python
from cmbench.backends.bucket_numpy import NumpyBucketCNFCountPlan

array_plan = NumpyBucketCNFCountPlan(plan, max_array_cells=1 << 18)
assert array_plan.count({'a': 1}) == 1
```

This explicit adapter shares the underlying plan and its private schedule format. Treat both plans as immutable after construction. It converts the initial tables into read-only NumPy object arrays once, then uses broadcasting and reduction in private query workspaces. Each array entry holds a Python integer, so intermediate counts are not restricted to 64-bit integers. Fortran-order reshape preserves the existing least-significant-bit row convention. Fixed-axis selection allocates its result rather than retaining a view of the larger joint table.

The additional `max_array_cells` limit defaults to 262,144. Before any NumPy array conversion, it checks a conservative bound: twice the original table cells, plus live intermediate cells, plus four times the largest joint allocation at each step. `stats['array_cells_bound']` records that bound. The base plan's admission and allocations happen first and retain their separate limits. Neither bound is a promise about total process memory, Python object sizes, NumPy iterator buffers, expression compilation or simultaneous queries. Each concurrent query needs its own workspace budget at the service boundary.

Array conversion and per-bucket calls add overhead on small factors. This is an opt-in prototype with measured workload limits, not an automatic replacement for the Python plan or native symbolic counting. See [the completed audit](../audits/2026-09-11-cm-bucket-counts/REPORT.md) for full cold/warm and refusal evidence.
