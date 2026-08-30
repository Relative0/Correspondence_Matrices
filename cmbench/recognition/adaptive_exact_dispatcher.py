"""One-pass exact ANF dispatcher that changes representation in place.

Evaluation starts with sparse Python sets. Before the first product that would
exceed the frozen cumulative pair budget, every computed polynomial is
converted to packed coefficient bits and evaluation continues at that node.
No source-DAG prefix is evaluated twice.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Any

from .source_anf_hybrid import ProductCache, multiply_packed, packed_interaction_components
from .source_interaction import (
    MAX_PRODUCT_PAIRS, MULTIPLICATIVE_OPS, OPS, _partition,
    _source_anf_prefix_sentinel_fast, source_anf_prefix_with_sentinel,
)


@dataclass
class AdaptiveInstrumentation:
    nodes: int = 0
    product_pair_budget: int = 0
    final_representation: str = "set"
    switch_node: int | None = None
    set_multiplications: int = 0
    set_executed_product_pairs: int = 0
    packed_multiplications: int = 0
    packed_logical_product_pairs: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_saved_product_pairs: int = 0
    converted_polynomials: int = 0
    converted_terms: int = 0
    peak_terms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _pack(polynomial: set[int]) -> int:
    result = 0
    for monomial in polynomial:
        result |= 1 << monomial
    return result


def _set_components(polynomial: set[int], n_vars: int) -> tuple[tuple[int, ...], ...]:
    parent = list(range(n_vars))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    for monomial in polynomial:
        variables = [variable for variable in range(n_vars) if monomial & (1 << variable)]
        for left, right in combinations(variables, 2):
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[max(left_root, right_root)] = min(left_root, right_root)
    groups: dict[int, list[int]] = {}
    for variable in range(n_vars):
        groups.setdefault(find(variable), []).append(variable)
    return tuple(sorted((tuple(group) for group in groups.values()), key=lambda group: group[0]))


def _adaptive_exact_partition(
    document: dict[str, Any],
    n_vars: int,
    *,
    product_pair_budget: int,
    cache: ProductCache,
    measure: bool,
) -> tuple[tuple[int, ...] | None, str, AdaptiveInstrumentation | None]:
    if type(product_pair_budget) is not int or not 0 <= product_pair_budget <= MAX_PRODUCT_PAIRS:
        raise ValueError("invalid adaptive product-pair budget")
    if not isinstance(cache, ProductCache):
        raise ValueError("adaptive dispatcher requires a bounded product cache")
    prefix = source_anf_prefix_with_sentinel(
        document, n_vars, product_pair_budget=product_pair_budget, measure=measure)
    nodes, root = prefix.nodes, prefix.root
    set_polynomials, switch_index = prefix.polynomials, prefix.switch_node
    counters = prefix.instrumentation

    if switch_index is None:
        polynomial = set_polynomials[root]
        stats = (AdaptiveInstrumentation(
            nodes=len(nodes), product_pair_budget=product_pair_budget,
            set_multiplications=counters.multiplications,
            set_executed_product_pairs=prefix.executed_product_pairs,
            peak_terms=counters.peak_terms,
        ) if counters is not None else None)
        return _partition(_set_components(polynomial, n_vars), n_vars), "set_source_anf", stats

    stats = (AdaptiveInstrumentation(
        nodes=len(nodes), product_pair_budget=product_pair_budget,
        final_representation="packed", switch_node=switch_index,
        set_multiplications=counters.multiplications,
        set_executed_product_pairs=prefix.executed_product_pairs,
        converted_polynomials=len(set_polynomials),
        converted_terms=sum(map(len, set_polynomials)),
        peak_terms=counters.peak_terms,
    ) if counters is not None else None)
    packed_polynomials = [_pack(value) for value in set_polynomials]

    def packed_product(left: int, right: int) -> int:
        pairs = None
        if stats is not None:
            stats.packed_multiplications += 1
            pairs = left.bit_count() * right.bit_count()
            stats.packed_logical_product_pairs += pairs
        cached = cache.get(n_vars, left, right)
        if cached is not None:
            if stats is not None:
                stats.cache_hits += 1
                stats.cache_saved_product_pairs += pairs
            return cached
        if stats is not None:
            stats.cache_misses += 1
        result = multiply_packed(left, right, n_vars)
        cache.put(n_vars, left, right, result)
        return result

    for index in range(switch_index, len(nodes)):
        node = nodes[index]
        if type(node) is not dict or node.get("op") not in OPS:
            raise ValueError("unsupported adaptive packed source-ANF node")
        op = node["op"]
        if op == "var":
            variable = node.get("i")
            if type(variable) is not int or not 0 <= variable < n_vars or set(node) != {"op", "i"}:
                raise ValueError("invalid adaptive packed source-ANF variable")
            value_packed = 1 << (1 << variable)
        else:
            references = (node.get("a"),) if op == "not" else (node.get("a"), node.get("b"))
            if any(type(reference) is not int or not 0 <= reference < index for reference in references):
                raise ValueError("non-topological adaptive packed source-ANF reference")
            if op == "not":
                value_packed = packed_polynomials[references[0]] ^ 1
            else:
                left, right = (packed_polynomials[reference] for reference in references)
                product_packed = packed_product(left, right) if op in MULTIPLICATIVE_OPS else 0
                if op == "xor":
                    value_packed = left ^ right
                elif op == "eqv":
                    value_packed = left ^ right ^ 1
                elif op == "and":
                    value_packed = product_packed
                elif op == "or":
                    value_packed = left ^ right ^ product_packed
                elif op == "imp":
                    value_packed = 1 ^ left ^ product_packed
                else:  # pragma: no cover
                    raise ValueError("unreachable adaptive packed operation")
        if value_packed.bit_length() > (1 << n_vars):
            raise ValueError("adaptive packed source-ANF term bound exceeded")
        if stats is not None:
            stats.peak_terms = max(stats.peak_terms, value_packed.bit_count())
        packed_polynomials.append(value_packed)
    polynomial_packed = packed_polynomials[root]
    return (_partition(packed_interaction_components(polynomial_packed, n_vars), n_vars),
            "adaptive_set_to_packed", stats)


def adaptive_exact_partition(
    document: dict[str, Any],
    n_vars: int,
    *,
    product_pair_budget: int,
    cache: ProductCache,
) -> tuple[tuple[int, ...] | None, str, AdaptiveInstrumentation]:
    """Measured exact execution with bounded sentinel and conversion counters."""
    partition, path, instrumentation = _adaptive_exact_partition(
        document, n_vars, product_pair_budget=product_pair_budget, cache=cache,
        measure=True)
    if instrumentation is None:  # pragma: no cover - internal contract
        raise RuntimeError("measured adaptive execution omitted instrumentation")
    return partition, path, instrumentation


def adaptive_exact_partition_fast(
    document: dict[str, Any],
    n_vars: int,
    *,
    product_pair_budget: int,
    cache: ProductCache,
) -> tuple[tuple[int, ...] | None, str]:
    """Production candidate with no detailed counter allocation or updates."""
    if type(product_pair_budget) is not int or not 0 <= product_pair_budget <= MAX_PRODUCT_PAIRS:
        raise ValueError("invalid adaptive product-pair budget")
    if not isinstance(cache, ProductCache):
        raise ValueError("adaptive dispatcher requires a bounded product cache")
    nodes, root, set_polynomials, switch_index, _set_pairs = (
        _source_anf_prefix_sentinel_fast(document, n_vars, product_pair_budget))
    if switch_index is None:
        return (_partition(_set_components(set_polynomials[root], n_vars), n_vars),
                "set_source_anf")

    packed_polynomials = [_pack(value) for value in set_polynomials]

    def packed_product(left: int, right: int) -> int:
        cached = cache.get(n_vars, left, right)
        if cached is not None:
            return cached
        result = multiply_packed(left, right, n_vars)
        cache.put(n_vars, left, right, result)
        return result

    for index in range(switch_index, len(nodes)):
        node = nodes[index]
        if type(node) is not dict or node.get("op") not in OPS:
            raise ValueError("unsupported adaptive packed source-ANF node")
        op = node["op"]
        if op == "var":
            variable = node.get("i")
            if type(variable) is not int or not 0 <= variable < n_vars or set(node) != {"op", "i"}:
                raise ValueError("invalid adaptive packed source-ANF variable")
            value_packed = 1 << (1 << variable)
        else:
            references = (node.get("a"),) if op == "not" else (node.get("a"), node.get("b"))
            if any(type(reference) is not int or not 0 <= reference < index for reference in references):
                raise ValueError("non-topological adaptive packed source-ANF reference")
            if op == "not":
                value_packed = packed_polynomials[references[0]] ^ 1
            else:
                left, right = (packed_polynomials[reference] for reference in references)
                product_packed = packed_product(left, right) if op in MULTIPLICATIVE_OPS else 0
                if op == "xor":
                    value_packed = left ^ right
                elif op == "eqv":
                    value_packed = left ^ right ^ 1
                elif op == "and":
                    value_packed = product_packed
                elif op == "or":
                    value_packed = left ^ right ^ product_packed
                elif op == "imp":
                    value_packed = 1 ^ left ^ product_packed
                else:  # pragma: no cover
                    raise ValueError("unreachable adaptive packed operation")
        if value_packed.bit_length() > (1 << n_vars):
            raise ValueError("adaptive packed source-ANF term bound exceeded")
        packed_polynomials.append(value_packed)
    return (_partition(packed_interaction_components(packed_polynomials[root], n_vars), n_vars),
            "adaptive_set_to_packed")
