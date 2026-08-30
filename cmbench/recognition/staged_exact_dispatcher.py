"""Exact set-first representation portfolio with an early product budget."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .source_anf_hybrid import ProductCache, source_packed_partition
from .source_interaction import MAX_PRODUCT_PAIRS, OPS, _partition, _validate_document


@dataclass
class SetGuardInstrumentation:
    nodes: int = 0
    multiplications: int = 0
    logical_product_pairs: int = 0
    executed_product_pairs: int = 0
    maximum_product_pairs: int = 0
    peak_terms: int = 0
    budget_limit: int = 0
    fallback_reason: str | None = None

    def to_dict(self):
        return asdict(self)


class SetProductBudgetExceeded(ValueError):
    def __init__(self, instrumentation: SetGuardInstrumentation):
        super().__init__("set ANF product-pair budget exceeded")
        self.instrumentation = instrumentation


def source_set_partition_guarded(document: dict[str, Any], n_vars: int, *, product_pair_budget: int):
    """Run exact set ANF but stop before the first product beyond the budget."""
    if type(product_pair_budget) is not int or not 0 <= product_pair_budget <= MAX_PRODUCT_PAIRS:
        raise ValueError("invalid guarded set-ANF product-pair budget")
    nodes, root = _validate_document(document, n_vars)
    stats = SetGuardInstrumentation(nodes=len(nodes), budget_limit=product_pair_budget)
    polynomials: list[set[int]] = []

    def multiply(left: set[int], right: set[int]):
        pairs = len(left) * len(right)
        stats.multiplications += 1
        stats.logical_product_pairs += pairs
        stats.maximum_product_pairs = max(stats.maximum_product_pairs, pairs)
        if stats.executed_product_pairs + pairs > product_pair_budget:
            stats.fallback_reason = "product_pair_budget"
            raise SetProductBudgetExceeded(stats)
        stats.executed_product_pairs += pairs
        result: set[int] = set()
        for first in left:
            for second in right:
                monomial = first | second
                if monomial in result:
                    result.remove(monomial)
                else:
                    result.add(monomial)
        return result

    for index, node in enumerate(nodes):
        if type(node) is not dict or node.get("op") not in OPS:
            raise ValueError("unsupported guarded set-ANF node")
        op = node["op"]
        if op == "var":
            variable = node.get("i")
            if type(variable) is not int or not 0 <= variable < n_vars or set(node) != {"op", "i"}:
                raise ValueError("invalid guarded set-ANF variable")
            value = {1 << variable}
        else:
            references = (node.get("a"),) if op == "not" else (node.get("a"), node.get("b"))
            if any(type(reference) is not int or not 0 <= reference < index for reference in references):
                raise ValueError("non-topological guarded set-ANF reference")
            if op == "not":
                value = polynomials[references[0]] ^ {0}
            else:
                left, right = (polynomials[reference] for reference in references)
                if op == "xor":
                    value = left ^ right
                elif op == "eqv":
                    value = left ^ right ^ {0}
                elif op == "and":
                    value = multiply(left, right)
                elif op == "or":
                    value = left ^ right ^ multiply(left, right)
                elif op == "imp":
                    value = {0} ^ left ^ multiply(left, right)
                else:  # pragma: no cover - guarded above
                    raise ValueError("unreachable guarded set-ANF operation")
        if len(value) > (1 << n_vars):
            raise ValueError("guarded set-ANF term bound exceeded")
        stats.peak_terms = max(stats.peak_terms, len(value))
        polynomials.append(value)
    components = []
    parent = list(range(n_vars))

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    for monomial in polynomials[root]:
        variables = [variable for variable in range(n_vars) if monomial & (1 << variable)]
        for variable in variables[1:]:
            left, right = find(variables[0]), find(variable)
            if left != right:
                parent[max(left, right)] = min(left, right)
    groups = {}
    for variable in range(n_vars):
        groups.setdefault(find(variable), []).append(variable)
    components = tuple(sorted((tuple(group) for group in groups.values()), key=lambda group: group[0]))
    return _partition(components, n_vars), stats


def staged_exact_partition(document: dict[str, Any], n_vars: int, *, product_pair_budget: int,
                           cache: ProductCache):
    """Prefer guarded set ANF, then restart exactly with cached packed ANF."""
    try:
        partition, set_stats = source_set_partition_guarded(
            document, n_vars, product_pair_budget=product_pair_budget)
        return partition, "set_source_anf", set_stats, None
    except SetProductBudgetExceeded as error:
        partition, packed_stats = source_packed_partition(document, n_vars, cache=cache)
        return partition, "cached_packed_source_anf", error.instrumentation, packed_stats
