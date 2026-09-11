# Opt-in exact scalar query APIs

These APIs return an arbitrary-precision model count or Boolean existence answer. They do not materialize a correspondence matrix or complete truth vector, and do not change dispatch defaults. Both accept raw expressions or compiled CM nodes. Basis names must be unique, nonempty strings; fixed assignments must use declared names with Boolean 0/1 values. Unused declared variables contribute their free assignments.

## Support-factorized counts

```python
from cm_exprlib import Or, Xor, Var
from cmbench.backends.factorized_counts import FactorizedCountPlan
from cmbench.backends.packed_mask_cache import PackedMaskCache

pool = PackedMaskCache(max_bytes=1 << 20, max_width=16)
plan = FactorizedCountPlan.from_expr(
    Or(Xor(Var(0), Var(1)), Var(2)),
    ('x0', 'x1', 'x2'), cache=pool,
)
assert plan.count() == 6
assert plan.count({'x2': 0}) == 2
assert plan.exists({'x0': 0, 'x1': 0, 'x2': 0}) is False
```

`from_cm_node(node, names, cache=pool)` provides CM ingress. `component_supports` lists the packed fallback components. Compilation calculates syntactic supports, groups overlapping arguments of associative operators, and retains disjoint groups as arithmetic nodes. Shared DAG instructions are reused; duplicate XOR arguments retain their multiplicity. Construction and count traversal are iterative after the existing expression/CM compilation step.

Each node carries `(zero_count, one_count)` over its own remaining support. For disjoint children, total assignments multiply. AND multiplies one counts; OR subtracts the product of zero counts from the total; XOR uses the product of `(zero_count - one_count)` to obtain even/odd counts. NOT swaps the pair. IMP and EQV use their two-input truth tables. This OR rule depends on independent supports; it does **not** assume mutually exclusive disjuncts or sum overlapping models.

An inseparable component executes through the existing exact flat packed engine. Every remaining component width is checked against `pool.max_width` before any mask construction or cache mutation. Fixed assignments can shrink components but do not cause repartitioning. A cheap false component does not bypass the preflight for a later oversized component. Cache byte accounting has the same limitations as `PackedMaskCache`: it bounds admitted column payload, not complete process memory or caller-held references. Support metadata and integer count arithmetic also consume space. Deep syntactic supports can make preparation expensive; this is not a general polynomial-time model counter.

## Affine constraints over GF(2)

```python
from cmbench.backends.affine_constraints import AffineConstraintPlan

# x0 XOR x1 = 0; x1 XOR x2 = 1. Row bit i means names[i].
plan = AffineConstraintPlan([0b011, 0b110], [0, 1], ('x0', 'x1', 'x2'))
assert plan.count() == 2
assert plan.count({'x0': 0}) == 1
assert not plan.exists({'x0': 0, 'x2': 0})
```

The row constructor checks nonnegative integer masks, matching Boolean right-hand sides and explicit admission limits (`max_width=8192`, `max_rows=16384` by default). Row/RHS iterable consumption is bounded. Empty systems and redundant/contradictory zero rows have their usual algebraic meanings. Fixed-variable validation uses the prepared name index, avoiding a full basis scan for each supplied name. Partial assignments adjust the right-hand side and remove fixed coefficients; packed Gaussian elimination checks consistency and rank. A consistent residual system returns `2 ** (remaining_variables - rank)`, otherwise zero. Each query owns its elimination state, so a prepared plan can serve concurrent reads without shared mutable scratch.

`from_expr(expr, names, **limits)` and `from_cm_node(node, names, **limits)` recognize a conjunction of affine constraints built from variables, constants, NOT, XOR and EQV. Each conjunct must evaluate to true. XOR cancellations and affine constants are exact. OR, IMP or an internal nonlinear AND are conservatively refused, even if an expensive semantic rewrite might make a particular input affine. Expression compilation precedes row admission; these limits are not a universal bound on arbitrary expression ingress.

`parse_alist(text, max_width=8192, max_rows=16384)` returns `(column_count, row_masks)` after checking degrees, duplicate edges and agreement between row and column adjacency. This is a matrix parser; it cannot tell whether a user supplied a parity-check matrix or a generator matrix. The research corpus explicitly excludes generator files. Text tokenization precedes dimension validation, so callers accepting untrusted external text must impose their own input-byte limit.

## Verification and scope

Small correctness checks: `.venv\Scripts\python.exe -B -m pytest tests/test_scalar_research.py -q -p no:cacheprovider`.

The [prospective research plan](CM_SCALAR_RESEARCH_PLAN_2026_09_11.md) describes the separate RunPod campaign, corpus admission and timing controls. These are general Boolean/algebraic techniques made available at CM query boundaries; a benefit through CM ingress is not evidence of a CM-specific algorithmic advantage. Preparing a scalar plan once and reusing it is a separate contract from charging conversion on every query.
