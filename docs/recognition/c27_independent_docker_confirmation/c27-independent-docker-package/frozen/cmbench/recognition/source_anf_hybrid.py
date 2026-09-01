"""Bounded exact source-DAG ANF using packed coefficient bitsets.

For ``n <= 10`` the complete ANF coefficient vector has at most 1,024 bits.
Coefficient ``m`` is stored at bit position ``m`` of a Python integer.  XOR is
therefore integer XOR.  Multiplication in the Boolean quotient ring
``GF(2)[x] / (x_i^2 - x_i)`` is OR-convolution, evaluated exactly with a
subset-zeta transform rather than enumerating monomial pairs.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
from functools import lru_cache
from itertools import combinations
from typing import Any

from cm_expr_serde import expr_from_json

from .natural_decomposition import analyze_decomposition
from .portfolio import reference_bits
from .source_interaction import MAX_VARS, OPS, _partition, _validate_document


@dataclass
class AnfInstrumentation:
    nodes: int = 0
    multiplications: int = 0
    logical_product_pairs: int = 0
    executed_product_pairs: int = 0
    cache_saved_product_pairs: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    peak_terms: int = 0
    peak_polynomial_bytes: int = 0
    maximum_product_pairs: int = 0
    budget_limit: int | None = None
    fallback_reason: str | None = None

    def record_polynomial(self, polynomial: int) -> None:
        self.peak_terms = max(self.peak_terms, polynomial.bit_count())
        self.peak_polynomial_bytes = max(
            self.peak_polynomial_bytes, max(1, (polynomial.bit_length() + 7) // 8)
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProductBudgetExceeded(ValueError):
    """Raised before a cache-miss product would exceed the frozen budget."""

    def __init__(self, instrumentation: AnfInstrumentation):
        super().__init__("packed source ANF product-pair budget exceeded")
        self.instrumentation = instrumentation


class ProductCache:
    """Capacity-bounded exact LRU cache keyed by the complete operands."""

    def __init__(self, capacity: int = 1024):
        if type(capacity) is not int or not 0 <= capacity <= 16_384:
            raise ValueError("invalid source ANF product-cache capacity")
        self.capacity = capacity
        self._values: OrderedDict[tuple[int, int, int], int] = OrderedDict()
        self.evictions = 0

    def get(self, n_vars: int, left: int, right: int) -> int | None:
        key = (n_vars, min(left, right), max(left, right))
        value = self._values.get(key)
        if value is not None:
            self._values.move_to_end(key)
        return value

    def put(self, n_vars: int, left: int, right: int, result: int) -> None:
        if self.capacity == 0:
            return
        key = (n_vars, min(left, right), max(left, right))
        self._values[key] = result
        self._values.move_to_end(key)
        while len(self._values) > self.capacity:
            self._values.popitem(last=False)
            self.evictions += 1

    def __len__(self) -> int:
        return len(self._values)


@lru_cache(maxsize=MAX_VARS * MAX_VARS)
def _dimension_low_mask(size: int, stride: int) -> int:
    block = (1 << stride) - 1
    result = 0
    for start in range(0, size, 2 * stride):
        result |= block << start
    return result


def subset_zeta(polynomial: int, n_vars: int) -> int:
    """Return the subset-zeta transform of a packed GF(2) vector.

    Over GF(2), the subset-zeta transform is its own inverse.
    """
    if (type(polynomial) is not int or polynomial < 0 or type(n_vars) is not int
            or not 2 <= n_vars <= MAX_VARS or polynomial.bit_length() > (1 << n_vars)):
        raise ValueError("invalid packed ANF polynomial")
    size = 1 << n_vars
    transformed = polynomial
    for dimension in range(n_vars):
        stride = 1 << dimension
        transformed ^= (transformed & _dimension_low_mask(size, stride)) << stride
    return transformed


def multiply_packed(left: int, right: int, n_vars: int) -> int:
    """Exact Boolean-polynomial product as packed OR-convolution."""
    return subset_zeta(subset_zeta(left, n_vars) & subset_zeta(right, n_vars), n_vars)


def source_anf_packed(
    document: dict[str, Any],
    n_vars: int,
    *,
    cache: ProductCache | None = None,
    product_pair_budget: int | None = None,
) -> tuple[int, AnfInstrumentation]:
    """Propagate a packed exact ANF through a canonical expression DAG.

    ``product_pair_budget`` counts the monomial-pair expansion that a cache
    miss would require.  The packed implementation does not perform that
    expansion, but retaining the count gives a representation-independent,
    validation-freezable gate.  Cache hits have zero executed pair cost.
    """
    if (product_pair_budget is not None
            and (type(product_pair_budget) is not int or product_pair_budget < 0)):
        raise ValueError("invalid packed source ANF product-pair budget")
    nodes, root = _validate_document(document, n_vars)
    stats = AnfInstrumentation(nodes=len(nodes), budget_limit=product_pair_budget)
    polynomials: list[int] = []

    def multiply(left: int, right: int) -> int:
        stats.multiplications += 1
        pairs = left.bit_count() * right.bit_count()
        stats.logical_product_pairs += pairs
        stats.maximum_product_pairs = max(stats.maximum_product_pairs, pairs)
        cached = cache.get(n_vars, left, right) if cache is not None else None
        if cached is not None:
            stats.cache_hits += 1
            stats.cache_saved_product_pairs += pairs
            return cached
        if cache is not None:
            stats.cache_misses += 1
        if product_pair_budget is not None and stats.executed_product_pairs + pairs > product_pair_budget:
            stats.fallback_reason = "product_pair_budget"
            raise ProductBudgetExceeded(stats)
        stats.executed_product_pairs += pairs
        result = multiply_packed(left, right, n_vars)
        if cache is not None:
            cache.put(n_vars, left, right, result)
        return result

    for index, node in enumerate(nodes):
        if type(node) is not dict or node.get("op") not in OPS:
            raise ValueError("unsupported packed source ANF node")
        op = node["op"]
        if op == "var":
            variable = node.get("i")
            if type(variable) is not int or not 0 <= variable < n_vars or set(node) != {"op", "i"}:
                raise ValueError("invalid packed source ANF variable")
            value = 1 << (1 << variable)
        else:
            references = (node.get("a"),) if op == "not" else (node.get("a"), node.get("b"))
            if any(type(reference) is not int or not 0 <= reference < index for reference in references):
                raise ValueError("non-topological packed source ANF reference")
            if op == "not":
                value = polynomials[references[0]] ^ 1
            else:
                left, right = (polynomials[reference] for reference in references)
                if op == "xor":
                    value = left ^ right
                elif op == "eqv":
                    value = left ^ right ^ 1
                elif op == "and":
                    value = multiply(left, right)
                elif op == "or":
                    value = left ^ right ^ multiply(left, right)
                elif op == "imp":
                    value = 1 ^ left ^ multiply(left, right)
                else:  # pragma: no cover - guarded above
                    raise ValueError("unreachable packed source ANF operation")
        if value.bit_length() > (1 << n_vars):
            raise ValueError("packed source ANF term bound exceeded")
        stats.record_polynomial(value)
        polynomials.append(value)
    return polynomials[root], stats


def packed_monomials(polynomial: int, n_vars: int) -> tuple[int, ...]:
    if (type(polynomial) is not int or polynomial < 0 or type(n_vars) is not int
            or not 2 <= n_vars <= MAX_VARS or polynomial.bit_length() > (1 << n_vars)):
        raise ValueError("invalid packed ANF polynomial")
    result = []
    remaining = polynomial
    while remaining:
        bit = remaining & -remaining
        result.append(bit.bit_length() - 1)
        remaining ^= bit
    return tuple(result)


def packed_interaction_components(polynomial: int, n_vars: int) -> tuple[tuple[int, ...], ...]:
    parent = list(range(n_vars))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    for monomial in packed_monomials(polynomial, n_vars):
        variables = [variable for variable in range(n_vars) if monomial & (1 << variable)]
        for left, right in combinations(variables, 2):
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[max(left_root, right_root)] = min(left_root, right_root)
    groups: dict[int, list[int]] = {}
    for variable in range(n_vars):
        groups.setdefault(find(variable), []).append(variable)
    return tuple(sorted((tuple(group) for group in groups.values()), key=lambda group: group[0]))


def source_packed_partition(
    document: dict[str, Any],
    n_vars: int,
    *,
    cache: ProductCache | None = None,
    product_pair_budget: int | None = None,
) -> tuple[tuple[int, ...] | None, AnfInstrumentation]:
    polynomial, stats = source_anf_packed(
        document, n_vars, cache=cache, product_pair_budget=product_pair_budget
    )
    return _partition(packed_interaction_components(polynomial, n_vars), n_vars), stats


def source_hybrid_partition(
    document: dict[str, Any],
    n_vars: int,
    *,
    cache: ProductCache,
    product_pair_budget: int,
) -> tuple[tuple[int, ...] | None, str, AnfInstrumentation]:
    """Use packed source ANF, falling back exactly before a refused product."""
    try:
        partition, stats = source_packed_partition(
            document, n_vars, cache=cache, product_pair_budget=product_pair_budget
        )
        return partition, "packed_source_anf", stats
    except ProductBudgetExceeded as error:
        bits = reference_bits(expr_from_json(document), n_vars)
        analysis = analyze_decomposition(bits, n_vars)
        return analysis.row_variables, "truth_vector_anf_fallback", error.instrumentation


def packed_truth_bits(polynomial: int, n_vars: int) -> int:
    """Evaluate a packed source-order ANF independently for verification."""
    monomials = packed_monomials(polynomial, n_vars)
    result = 0
    for assignment in range(1 << n_vars):
        source_assignment = sum(
            ((assignment >> (n_vars - 1 - variable)) & 1) << variable
            for variable in range(n_vars)
        )
        value = 0
        for monomial in monomials:
            value ^= int((source_assignment & monomial) == monomial)
        result |= value << assignment
    return result
