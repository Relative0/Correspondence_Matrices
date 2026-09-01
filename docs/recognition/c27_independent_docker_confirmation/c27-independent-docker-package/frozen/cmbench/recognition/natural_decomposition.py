"""Exact partition discovery for bounded natural Boolean functions.

For XOR decomposition, ``f(X) = g(A) xor h(B)`` for a nontrivial partition
``A | B`` exactly when no algebraic-normal-form monomial contains variables
from both sides.  Connected components of the ANF interaction graph therefore
give every admissible partition without enumerating every matrix layout first.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Iterable

MAX_NATURAL_VARS = 10


def anf_coefficients(bits: int, n_vars: int) -> tuple[int, ...]:
    if (type(n_vars) is not int or not 2 <= n_vars <= MAX_NATURAL_VARS
            or type(bits) is not int or bits < 0 or bits.bit_length() > (1 << n_vars)):
        raise ValueError("invalid bounded truth vector for ANF")
    coefficients = [(bits >> index) & 1 for index in range(1 << n_vars)]
    for bit_position in range(n_vars):
        bit = 1 << bit_position
        for mask in range(1 << n_vars):
            if mask & bit:
                coefficients[mask] ^= coefficients[mask ^ bit]
    return tuple(coefficients)


def interaction_components(bits: int, n_vars: int) -> tuple[tuple[int, ...], ...]:
    """Return canonical connected components of the ANF interaction graph."""
    coefficients = anf_coefficients(bits, n_vars)
    parent = list(range(n_vars))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: int, right: int):
        left, right = find(left), find(right)
        if left != right:
            parent[max(left, right)] = min(left, right)

    # Truth-vector indices use x0 as the most significant assignment bit.
    for monomial_mask, present in enumerate(coefficients):
        if not present or monomial_mask.bit_count() < 2:
            continue
        variables = [n_vars - 1 - position for position in range(n_vars) if monomial_mask & (1 << position)]
        for variable in variables[1:]:
            union(variables[0], variable)
    groups: dict[int, list[int]] = {}
    for variable in range(n_vars):
        groups.setdefault(find(variable), []).append(variable)
    return tuple(sorted((tuple(group) for group in groups.values()), key=lambda group: (group[0], len(group), group)))


def semantic_variables(bits: int, n_vars: int) -> tuple[int, ...]:
    """Return variables present in at least one nonzero ANF monomial."""
    present: set[int] = set()
    for monomial_mask, coefficient in enumerate(anf_coefficients(bits, n_vars)):
        if not coefficient:
            continue
        present.update(n_vars - 1 - position for position in range(n_vars)
                       if monomial_mask & (1 << position))
    return tuple(sorted(present))


def interaction_edges(bits: int, n_vars: int) -> tuple[tuple[int, int], ...]:
    """Return exact ANF variable-pair interactions in canonical order."""
    edges: set[tuple[int, int]] = set()
    for monomial_mask, coefficient in enumerate(anf_coefficients(bits, n_vars)):
        if not coefficient or monomial_mask.bit_count() < 2:
            continue
        variables = sorted(n_vars - 1 - position for position in range(n_vars)
                           if monomial_mask & (1 << position))
        edges.update((left, right) for left, right in combinations(variables, 2))
    return tuple(sorted(edges))


def interaction_target(bits: int, n_vars: int, max_vars: int = MAX_NATURAL_VARS) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return padded upper-triangle edge labels and a valid-universe mask."""
    if type(max_vars) is not int or not n_vars <= max_vars <= MAX_NATURAL_VARS:
        raise ValueError("invalid interaction target universe")
    edges = set(interaction_edges(bits, n_vars))
    labels, mask = [], []
    for left in range(max_vars):
        for right in range(left + 1, max_vars):
            valid = right < n_vars
            mask.append(int(valid))
            labels.append(int(valid and (left, right) in edges))
    return tuple(labels), tuple(mask)


def canonical_partition(bits: int, n_vars: int) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    """Choose the most balanced exact partition, with a deterministic tie break."""
    components = interaction_components(bits, n_vars)
    if len(components) < 2:
        return None
    variables = tuple(range(n_vars))
    candidates = []
    # Component zero must be in the row side, removing A|B/B|A duplicates.
    for count in range(1, len(components)):
        for selected_rest in combinations(range(1, len(components)), count - 1):
            selected = (0,) + selected_rest
            row = tuple(sorted(variable for index in selected for variable in components[index]))
            if not row or len(row) == n_vars:
                continue
            column = tuple(variable for variable in variables if variable not in row)
            candidates.append((abs(len(row) - len(column)), max(len(row), len(column)), row, column))
    if not candidates:
        return None
    _imbalance, _largest, row, column = min(candidates)
    return row, column


def partitioned_bits(bits: int, n_vars: int, row_variables: Iterable[int]) -> tuple[int, int, int]:
    """Reorder a truth vector into row-major bits for the declared partition."""
    row = tuple(row_variables)
    if (not row or len(row) == n_vars or len(set(row)) != len(row)
            or any(type(variable) is not int or not 0 <= variable < n_vars for variable in row)):
        raise ValueError("invalid nontrivial variable partition")
    column = tuple(variable for variable in range(n_vars) if variable not in row)
    result = 0
    for row_assignment in range(1 << len(row)):
        for column_assignment in range(1 << len(column)):
            original = 0
            for local, variable in enumerate(row):
                value = (row_assignment >> (len(row) - 1 - local)) & 1
                original |= value << (n_vars - 1 - variable)
            for local, variable in enumerate(column):
                value = (column_assignment >> (len(column) - 1 - local)) & 1
                original |= value << (n_vars - 1 - variable)
            destination = row_assignment * (1 << len(column)) + column_assignment
            result |= ((bits >> original) & 1) << destination
    return result, len(row), len(column)


def partition_witness(bits: int, n_vars: int, row_variables: Iterable[int]) -> dict[str, Any] | None:
    row = tuple(row_variables)
    arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
    rows, columns = 1 << row_count, 1 << column_count
    at = lambda row_index, column_index: (arranged >> (row_index * columns + column_index)) & 1
    corner = at(0, 0)
    row_factor = sum((at(index, 0) ^ corner) << index for index in range(rows))
    column_factor = sum(at(0, index) << index for index in range(columns))
    for row_index in range(rows):
        for column_index in range(columns):
            if at(row_index, column_index) != (((row_factor >> row_index) & 1)
                                                ^ ((column_factor >> column_index) & 1)):
                return None
    return {"partition": [row_count, column_count], "row_variables": list(row),
            "column_variables": [variable for variable in range(n_vars) if variable not in row],
            "row_factor_bits": row_factor, "column_factor_bits": column_factor,
            "stored_factor_bits": rows + columns, "full_truth_bits": rows * columns}


def compose_partition_witness(witness: dict[str, Any], n_vars: int) -> int:
    if type(witness) is not dict or set(witness) != {
            "partition", "row_variables", "column_variables", "row_factor_bits", "column_factor_bits",
            "stored_factor_bits", "full_truth_bits"}:
        raise ValueError("invalid partition witness")
    row = tuple(witness["row_variables"])
    column = tuple(witness["column_variables"])
    if (witness["partition"] != [len(row), len(column)] or sorted(row + column) != list(range(n_vars))
            or set(row) & set(column)):
        raise ValueError("partition witness variable identity mismatch")
    rows, columns = 1 << len(row), 1 << len(column)
    row_factor, column_factor = witness["row_factor_bits"], witness["column_factor_bits"]
    if (type(row_factor) is not int or type(column_factor) is not int or row_factor < 0 or column_factor < 0
            or row_factor.bit_length() > rows or column_factor.bit_length() > columns):
        raise ValueError("partition factor outside declared sides")
    arranged = 0
    for row_assignment in range(rows):
        for column_assignment in range(columns):
            value = ((row_factor >> row_assignment) & 1) ^ ((column_factor >> column_assignment) & 1)
            arranged |= value << (row_assignment * columns + column_assignment)
    result = 0
    for row_assignment in range(1 << len(row)):
        for column_assignment in range(1 << len(column)):
            source = row_assignment * (1 << len(column)) + column_assignment
            original = 0
            for local, variable in enumerate(row):
                original |= ((row_assignment >> (len(row) - 1 - local)) & 1) << (n_vars - 1 - variable)
            for local, variable in enumerate(column):
                original |= ((column_assignment >> (len(column) - 1 - local)) & 1) << (n_vars - 1 - variable)
            result |= ((arranged >> source) & 1) << original
    return result


def anchor_residual(bits: int, n_vars: int, row_variables: Iterable[int]) -> dict[str, Any]:
    """Return the exact anchored 2x2 violation map for an arbitrary partition."""
    row = tuple(row_variables)
    arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
    rows, columns = 1 << row_count, 1 << column_count
    at = lambda row_index, column_index: (arranged >> (row_index * columns + column_index)) & 1
    residual = 0
    for row_index in range(rows):
        for column_index in range(columns):
            value = at(row_index, column_index) ^ at(row_index, 0) ^ at(0, column_index) ^ at(0, 0)
            residual |= value << (row_index * columns + column_index)
    return {"residual_bits": residual, "violation_count": residual.bit_count(),
            "cell_count": rows * columns, "violation_fraction": residual.bit_count() / (rows * columns)}


@dataclass(frozen=True)
class DecompositionAnalysis:
    n_vars: int
    components: tuple[tuple[int, ...], ...]
    row_variables: tuple[int, ...] | None
    column_variables: tuple[int, ...] | None
    witness: dict[str, Any] | None

    @property
    def decomposable(self) -> bool:
        return self.witness is not None


def analyze_decomposition(bits: int, n_vars: int) -> DecompositionAnalysis:
    components = interaction_components(bits, n_vars)
    partition = canonical_partition(bits, n_vars)
    if partition is None:
        return DecompositionAnalysis(n_vars, components, None, None, None)
    row, column = partition
    witness = partition_witness(bits, n_vars, row)
    if witness is None or compose_partition_witness(witness, n_vars) != bits:
        raise ValueError("ANF partition discovery failed exact witness check")
    return DecompositionAnalysis(n_vars, components, row, column, witness)
