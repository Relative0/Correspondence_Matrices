"""Sound source-level over-approximation of ANF variable interactions."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Any

MAX_VARS = 10
OPS = {"var", "not", "and", "or", "xor", "imp", "eqv"}
MULTIPLICATIVE_OPS = {"and", "or", "imp"}
MAX_PRODUCT_PAIRS = 8_000_000


@dataclass
class SourceAnfSentinelInstrumentation:
    """Optional bounded counters for the in-kernel set-ANF sentinel."""

    nodes: int = 0
    budget_limit: int = 0
    logical_product_pairs: int = 0
    executed_product_pairs: int = 0
    maximum_product_pairs: int = 0
    multiplications: int = 0
    switch_node: int | None = None
    peak_terms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SourceAnfPrefix:
    """Exact set-polynomial prefix returned before an optional packed switch."""

    nodes: list[dict[str, Any]]
    root: int
    polynomials: list[set[int]]
    switch_node: int | None
    executed_product_pairs: int
    instrumentation: SourceAnfSentinelInstrumentation | None


def _validate_document(document: dict[str, Any], n_vars: int):
    if type(n_vars) is not int or not 2 <= n_vars <= MAX_VARS:
        raise ValueError("source interaction universe outside 2..10")
    if type(document) is not dict or document.get("version") != 2 or set(document) != {"version", "nodes", "root"}:
        raise ValueError("source interaction requires canonical expression DAG v2")
    nodes = document.get("nodes")
    root = document.get("root")
    if type(nodes) is not list or not 1 <= len(nodes) <= 4096 or type(root) is not int or not 0 <= root < len(nodes):
        raise ValueError("invalid bounded source interaction DAG")
    return nodes, root


def source_interaction_edges(document: dict[str, Any], n_vars: int) -> tuple[tuple[int, int], ...]:
    """Return a syntactic superset of exact ANF interaction edges.

    XOR, equivalence, and negation only propagate child interactions. AND, OR,
    and implication can multiply child ANFs, so every cross-support pair is
    added. Cancellation may remove exact edges, making this conservative.
    """
    nodes, root = _validate_document(document, n_vars)
    supports: list[set[int]] = []
    interactions: list[set[tuple[int, int]]] = []
    for index, node in enumerate(nodes):
        if type(node) is not dict or node.get("op") not in OPS:
            raise ValueError("unsupported source interaction node")
        op = node["op"]
        if op == "var":
            variable = node.get("i")
            if type(variable) is not int or not 0 <= variable < n_vars or set(node) != {"op", "i"}:
                raise ValueError("invalid source interaction variable")
            supports.append({variable})
            interactions.append(set())
            continue
        references = (node.get("a"),) if op == "not" else (node.get("a"), node.get("b"))
        if any(type(reference) is not int or not 0 <= reference < index for reference in references):
            raise ValueError("non-topological source interaction reference")
        support = set().union(*(supports[reference] for reference in references))
        edges = set().union(*(interactions[reference] for reference in references))
        if op in MULTIPLICATIVE_OPS:
            left, right = references
            edges.update(
                tuple(sorted((first, second)))
                for first in supports[left]
                for second in supports[right]
                if first != second
            )
        supports.append(support)
        interactions.append(edges)
    if supports[root] != set(range(n_vars)):
        raise ValueError("source interaction root lacks full declared support")
    return tuple(sorted(interactions[root]))


def source_anf_monomials(document: dict[str, Any], n_vars: int) -> tuple[int, ...]:
    """Compute the exact bounded ANF polynomial directly over the source DAG."""
    nodes, root = _validate_document(document, n_vars)
    polynomials: list[set[int]] = []
    product_pairs = 0

    def xor(left: set[int], right: set[int]):
        return left ^ right

    def multiply(left: set[int], right: set[int]):
        nonlocal product_pairs
        product_pairs += len(left) * len(right)
        if product_pairs > MAX_PRODUCT_PAIRS:
            raise ValueError("source symbolic ANF product-pair budget exceeded")
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
            raise ValueError("unsupported source symbolic ANF node")
        op = node["op"]
        if op == "var":
            variable = node.get("i")
            if type(variable) is not int or not 0 <= variable < n_vars or set(node) != {"op", "i"}:
                raise ValueError("invalid source symbolic ANF variable")
            polynomials.append({1 << variable})
            continue
        references = (node.get("a"),) if op == "not" else (node.get("a"), node.get("b"))
        if any(type(reference) is not int or not 0 <= reference < index for reference in references):
            raise ValueError("non-topological source symbolic ANF reference")
        if op == "not":
            polynomials.append(xor(polynomials[references[0]], {0}))
            continue
        left, right = (polynomials[reference] for reference in references)
        if op == "xor":
            value = xor(left, right)
        elif op == "eqv":
            value = xor(xor(left, right), {0})
        elif op == "and":
            value = multiply(left, right)
        elif op == "or":
            value = xor(xor(left, right), multiply(left, right))
        elif op == "imp":
            value = xor(xor({0}, left), multiply(left, right))
        else:
            raise ValueError("unreachable source symbolic ANF operation")
        if len(value) > (1 << n_vars):
            raise ValueError("source symbolic ANF term bound exceeded")
        polynomials.append(value)
    return tuple(sorted(polynomials[root]))


def _source_anf_prefix_sentinel_fast(
    document: dict[str, Any],
    n_vars: int,
    product_pair_budget: int,
) -> tuple[list[dict[str, Any]], int, list[set[int]], int | None, int]:
    """Measurement-free sentinel loop; caller selects it before execution."""
    if type(product_pair_budget) is not int or not 0 <= product_pair_budget <= MAX_PRODUCT_PAIRS:
        raise ValueError("invalid source ANF sentinel product-pair budget")
    nodes, root = _validate_document(document, n_vars)
    polynomials: list[set[int]] = []
    product_pairs = 0
    for index, node in enumerate(nodes):
        if type(node) is not dict or node.get("op") not in OPS:
            raise ValueError("unsupported source ANF sentinel node")
        op = node["op"]
        if op == "var":
            variable = node.get("i")
            if type(variable) is not int or not 0 <= variable < n_vars or set(node) != {"op", "i"}:
                raise ValueError("invalid source ANF sentinel variable")
            value = {1 << variable}
        else:
            references = (node.get("a"),) if op == "not" else (node.get("a"), node.get("b"))
            if any(type(reference) is not int or not 0 <= reference < index for reference in references):
                raise ValueError("non-topological source ANF sentinel reference")
            if op == "not":
                value = polynomials[references[0]] ^ {0}
            else:
                left, right = (polynomials[reference] for reference in references)
                if op in MULTIPLICATIVE_OPS:
                    pairs = len(left) * len(right)
                    if product_pairs + pairs > product_pair_budget:
                        return nodes, root, polynomials, index, product_pairs
                    product_pairs += pairs
                    product: set[int] = set()
                    for first in left:
                        for second in right:
                            monomial = first | second
                            if monomial in product:
                                product.remove(monomial)
                            else:
                                product.add(monomial)
                else:
                    product = set()
                if op == "xor":
                    value = left ^ right
                elif op == "eqv":
                    value = left ^ right ^ {0}
                elif op == "and":
                    value = product
                elif op == "or":
                    value = left ^ right ^ product
                elif op == "imp":
                    value = {0} ^ left ^ product
                else:  # pragma: no cover
                    raise ValueError("unreachable source ANF sentinel operation")
        if len(value) > (1 << n_vars):
            raise ValueError("source ANF sentinel term bound exceeded")
        polynomials.append(value)
    return nodes, root, polynomials, None, product_pairs


def source_anf_prefix_with_sentinel(
    document: dict[str, Any],
    n_vars: int,
    *,
    product_pair_budget: int,
    measure: bool = False,
) -> SourceAnfPrefix:
    """Run the base set-ANF kernel until its next product would exceed a budget.

    The ordinary :func:`source_anf_monomials` implementation remains a separate
    no-sentinel path.  This function performs one cumulative-pair comparison per
    multiplicative node and returns every exact polynomial already computed so a
    packed continuation never reevaluates the source-DAG prefix.  Detailed
    counters are allocated and updated only when ``measure`` is true.
    """
    if type(product_pair_budget) is not int or not 0 <= product_pair_budget <= MAX_PRODUCT_PAIRS:
        raise ValueError("invalid source ANF sentinel product-pair budget")
    if type(measure) is not bool:
        raise ValueError("source ANF sentinel measurement flag must be Boolean")
    if not measure:
        nodes, root, polynomials, switch_node, product_pairs = (
            _source_anf_prefix_sentinel_fast(document, n_vars, product_pair_budget))
        return SourceAnfPrefix(
            nodes, root, polynomials, switch_node, product_pairs, None)
    nodes, root = _validate_document(document, n_vars)
    polynomials: list[set[int]] = []
    product_pairs = 0
    counters = (SourceAnfSentinelInstrumentation(
        nodes=len(nodes), budget_limit=product_pair_budget) if measure else None)

    for index, node in enumerate(nodes):
        if type(node) is not dict or node.get("op") not in OPS:
            raise ValueError("unsupported source ANF sentinel node")
        op = node["op"]
        if op == "var":
            variable = node.get("i")
            if type(variable) is not int or not 0 <= variable < n_vars or set(node) != {"op", "i"}:
                raise ValueError("invalid source ANF sentinel variable")
            value = {1 << variable}
        else:
            references = (node.get("a"),) if op == "not" else (node.get("a"), node.get("b"))
            if any(type(reference) is not int or not 0 <= reference < index for reference in references):
                raise ValueError("non-topological source ANF sentinel reference")
            if op == "not":
                value = polynomials[references[0]] ^ {0}
            else:
                left, right = (polynomials[reference] for reference in references)
                if op in MULTIPLICATIVE_OPS:
                    pairs = len(left) * len(right)
                    if counters is not None:
                        counters.logical_product_pairs += pairs
                        counters.maximum_product_pairs = max(counters.maximum_product_pairs, pairs)
                    if product_pairs + pairs > product_pair_budget:
                        if counters is not None:
                            counters.switch_node = index
                        return SourceAnfPrefix(
                            nodes, root, polynomials, index, product_pairs, counters)
                    product_pairs += pairs
                    if counters is not None:
                        counters.executed_product_pairs = product_pairs
                        counters.multiplications += 1
                    product: set[int] = set()
                    for first in left:
                        for second in right:
                            monomial = first | second
                            if monomial in product:
                                product.remove(monomial)
                            else:
                                product.add(monomial)
                else:
                    product = set()
                if op == "xor":
                    value = left ^ right
                elif op == "eqv":
                    value = left ^ right ^ {0}
                elif op == "and":
                    value = product
                elif op == "or":
                    value = left ^ right ^ product
                elif op == "imp":
                    value = {0} ^ left ^ product
                else:  # pragma: no cover
                    raise ValueError("unreachable source ANF sentinel operation")
        if len(value) > (1 << n_vars):
            raise ValueError("source ANF sentinel term bound exceeded")
        if counters is not None:
            counters.peak_terms = max(counters.peak_terms, len(value))
        polynomials.append(value)
    return SourceAnfPrefix(nodes, root, polynomials, None, product_pairs, counters)


def source_exact_interaction_edges(document: dict[str, Any], n_vars: int):
    edges: set[tuple[int, int]] = set()
    for monomial in source_anf_monomials(document, n_vars):
        variables = [variable for variable in range(n_vars) if monomial & (1 << variable)]
        edges.update(combinations(variables, 2))
    return tuple(sorted(edges))


def source_interaction_components(document: dict[str, Any], n_vars: int):
    return _components(source_interaction_edges(document, n_vars), n_vars)


def source_exact_interaction_components(document: dict[str, Any], n_vars: int):
    return _components(source_exact_interaction_edges(document, n_vars), n_vars)


def _components(edges, n_vars: int):
    parent = list(range(n_vars))

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    for left, right in edges:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)
    groups: dict[int, list[int]] = {}
    for variable in range(n_vars):
        groups.setdefault(find(variable), []).append(variable)
    return tuple(sorted((tuple(group) for group in groups.values()), key=lambda group: group[0]))


def source_partition_proposal(document: dict[str, Any], n_vars: int):
    """Return the canonical nontrivial cut implied by the sound over-approximation."""
    return _partition(source_interaction_components(document, n_vars), n_vars)


def source_exact_partition(document: dict[str, Any], n_vars: int):
    """Return the exact canonical ANF cut without materializing a truth vector."""
    return _partition(source_exact_interaction_components(document, n_vars), n_vars)


def _partition(components, n_vars: int):
    if len(components) < 2:
        return None
    candidates = []
    for count in range(1, len(components)):
        for selected_rest in combinations(range(1, len(components)), count - 1):
            selected = (0,) + selected_rest
            row = tuple(sorted(variable for index in selected for variable in components[index]))
            if len(row) == n_vars:
                continue
            column = tuple(variable for variable in range(n_vars) if variable not in row)
            candidates.append((abs(len(row) - len(column)), max(len(row), len(column)), row))
    return min(candidates)[2] if candidates else None
