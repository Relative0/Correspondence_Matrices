"""Exact GF(2) rank and factor conversion in the ANF coefficient basis.

For a variable partition R|C, truth and ANF coefficient matrices satisfy
``T = Z_R A Z_C^T`` over GF(2).  The subset-zeta matrices are invertible, so
the matrices have identical rank.  This module also transforms an ANF-basis
rank factorization back to the canonical truth basis and verifies it exactly.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .gf2_decomposition import gf2_rank_factor
from .natural_decomposition import anf_coefficients, partitioned_bits


MAX_ANF_RANK_VARS = 10


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _partition(row_variables: Iterable[int], n_vars: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    row = tuple(row_variables)
    _require(
        2 <= n_vars <= MAX_ANF_RANK_VARS
        and row and len(row) < n_vars and len(set(row)) == len(row)
        and all(type(variable) is int and 0 <= variable < n_vars for variable in row),
        "invalid ANF-rank partition",
    )
    return row, tuple(variable for variable in range(n_vars) if variable not in row)


def packed_anf_from_truth(bits: int, n_vars: int) -> int:
    """Return natural truth-index-order ANF coefficients as one packed int."""
    return sum(coefficient << monomial for monomial, coefficient in enumerate(
        anf_coefficients(bits, n_vars)))


def normalize_source_anf(polynomial: int, n_vars: int) -> int:
    """Map source-ANF variable-mask indexing to natural truth-index indexing."""
    _require(
        type(polynomial) is int and polynomial >= 0
        and 2 <= n_vars <= MAX_ANF_RANK_VARS
        and polynomial.bit_length() <= (1 << n_vars),
        "invalid source packed ANF",
    )
    output = 0
    remaining = polynomial
    while remaining:
        selected = remaining & -remaining
        source_monomial = selected.bit_length() - 1
        natural_monomial = 0
        for variable in range(n_vars):
            natural_monomial |= (
                (source_monomial >> variable) & 1) << (n_vars - 1 - variable)
        output |= 1 << natural_monomial
        remaining ^= selected
    return output


def _local_assignment(mask: int, variables: tuple[int, ...], n_vars: int) -> int:
    output = 0
    for variable in variables:
        output = (output << 1) | ((mask >> (n_vars - 1 - variable)) & 1)
    return output


def anf_partition_rows(
    polynomial: int, n_vars: int, row_variables: Iterable[int],
) -> tuple[int, ...]:
    """Arrange packed ANF coefficients as row-major GF(2) matrix rows."""
    row, column = _partition(row_variables, n_vars)
    _require(type(polynomial) is int and polynomial >= 0
             and polynomial.bit_length() <= (1 << n_vars),
             "invalid packed ANF for rank")
    rows = [0] * (1 << len(row))
    remaining = polynomial
    while remaining:
        selected = remaining & -remaining
        monomial = selected.bit_length() - 1
        row_index = _local_assignment(monomial, row, n_vars)
        column_index = _local_assignment(monomial, column, n_vars)
        rows[row_index] |= 1 << column_index
        remaining ^= selected
    return tuple(rows)


def truth_partition_rows(
    bits: int, n_vars: int, row_variables: Iterable[int],
) -> tuple[int, ...]:
    row, column = _partition(row_variables, n_vars)
    arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
    if row_count != len(row) or column_count != len(column):
        raise AssertionError("truth partition dimensions changed")
    width = 1 << column_count
    mask = (1 << width) - 1
    return tuple((arranged >> (index * width)) & mask
                 for index in range(1 << row_count))


def _dimension_low_mask(size: int, stride: int) -> int:
    block = (1 << stride) - 1
    return sum(block << start for start in range(0, size, 2 * stride))


def local_subset_zeta(vector: int, dimensions: int) -> int:
    _require(type(dimensions) is int and 1 <= dimensions <= MAX_ANF_RANK_VARS
             and type(vector) is int and vector >= 0
             and vector.bit_length() <= (1 << dimensions),
             "invalid local subset-zeta vector")
    transformed = vector
    size = 1 << dimensions
    for dimension in range(dimensions):
        stride = 1 << dimension
        transformed ^= (transformed & _dimension_low_mask(size, stride)) << stride
    return transformed


@dataclass(frozen=True)
class ANFRankFactor:
    rank: int
    anf_row_coefficients: tuple[int, ...]
    anf_basis_rows: tuple[int, ...]
    truth_row_coefficients: tuple[int, ...]
    truth_basis_rows: tuple[int, ...]
    matrix_shape: tuple[int, int]

    def reconstruct_truth_rows(self) -> tuple[int, ...]:
        output = []
        for coefficient in self.truth_row_coefficients:
            value = 0
            for index, basis_row in enumerate(self.truth_basis_rows):
                if coefficient & (1 << index):
                    value ^= basis_row
            output.append(value)
        return tuple(output)


def anf_rank_factor_to_truth(
    polynomial: int,
    n_vars: int,
    row_variables: Iterable[int],
    *,
    expected_truth_bits: int | None = None,
) -> ANFRankFactor:
    """Rank in the ANF basis, then transform its factors to the truth basis."""
    row, column = _partition(row_variables, n_vars)
    anf_rows = anf_partition_rows(polynomial, n_vars, row)
    width = 1 << len(column)
    rank, coefficients, basis = gf2_rank_factor(anf_rows, width)

    truth_basis = tuple(local_subset_zeta(value, len(column)) for value in basis)
    transformed_columns = []
    for factor in range(rank):
        column_vector = sum(
            ((coefficient >> factor) & 1) << row_index
            for row_index, coefficient in enumerate(coefficients))
        transformed_columns.append(local_subset_zeta(column_vector, len(row)))
    truth_coefficients = tuple(sum(
        ((transformed_columns[factor] >> row_index) & 1) << factor
        for factor in range(rank)) for row_index in range(1 << len(row)))
    result = ANFRankFactor(
        rank=rank,
        anf_row_coefficients=coefficients,
        anf_basis_rows=basis,
        truth_row_coefficients=truth_coefficients,
        truth_basis_rows=truth_basis,
        matrix_shape=(1 << len(row), 1 << len(column)),
    )
    if expected_truth_bits is not None:
        expected_rows = truth_partition_rows(expected_truth_bits, n_vars, row)
        if result.reconstruct_truth_rows() != expected_rows:
            raise RuntimeError("ANF-basis factor conversion failed exact truth reconstruction")
        truth_rank = gf2_rank_factor(expected_rows, width)[0]
        if truth_rank != rank:
            raise RuntimeError("ANF/truth GF(2) rank invariant failed")
    return result


def anf_rank(polynomial: int, n_vars: int, row_variables: Iterable[int]) -> int:
    row, column = _partition(row_variables, n_vars)
    return gf2_rank_factor(
        anf_partition_rows(polynomial, n_vars, row), 1 << len(column))[0]
