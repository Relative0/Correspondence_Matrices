"""Sound early termination for non-compressing GF(2)-rank candidates."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .gf2_decomposition import (
    ExactGF2Analysis,
    GF2CandidateDescriptor,
    _cofactor_descriptors,
    _kronecker_descriptors,
    _partition,
    _validate_bits,
    candidate_partitions,
    truth_sha256,
    xor_component_artifact,
)
from .natural_decomposition import partitioned_bits


@dataclass(frozen=True)
class BoundedRankResult:
    pruned: bool
    rows_scanned: int
    total_rows: int
    rank_lower_bound: int
    rank: int | None
    coefficients: tuple[int, ...] | None
    basis: tuple[int, ...] | None


def gf2_rank_factor_bounded(
    rows: Iterable[int], width: int, noncompressing_rank: int,
) -> BoundedRankResult:
    """Stop when partial rank reaches a sound non-compression threshold."""
    values = tuple(rows)
    if (type(width) is not int or not 1 <= width <= 512 or not values
            or type(noncompressing_rank) is not int or noncompressing_rank <= 0
            or any(type(row) is not int or row < 0 or row.bit_length() > width
                   for row in values)):
        raise ValueError("invalid bounded GF(2) matrix")
    basis: list[int] = []
    pivot_to_index: dict[int, int] = {}
    coefficients = []
    for row_index, row in enumerate(values):
        residual, coefficient = row, 0
        for pivot in sorted(pivot_to_index, reverse=True):
            if residual & (1 << pivot):
                index = pivot_to_index[pivot]
                residual ^= basis[index]
                coefficient ^= 1 << index
        if residual:
            pivot = residual.bit_length() - 1
            index = len(basis)
            pivot_to_index[pivot] = index
            basis.append(residual)
            coefficient ^= 1 << index
        coefficients.append(coefficient)
        if len(basis) >= noncompressing_rank:
            return BoundedRankResult(
                pruned=True, rows_scanned=row_index + 1, total_rows=len(values),
                rank_lower_bound=len(basis), rank=None, coefficients=None, basis=None)
    for row, coefficient in zip(values, coefficients, strict=True):
        reconstructed = 0
        for index, basis_row in enumerate(basis):
            if coefficient & (1 << index):
                reconstructed ^= basis_row
        if reconstructed != row:
            raise RuntimeError("bounded GF(2) elimination recomposition failed")
    return BoundedRankResult(
        pruned=False, rows_scanned=len(values), total_rows=len(values),
        rank_lower_bound=len(basis), rank=len(basis), coefficients=tuple(coefficients),
        basis=tuple(basis))


def _matrix_rows(arranged: int, rows: int, columns: int) -> tuple[int, ...]:
    mask = (1 << columns) - 1
    return tuple((arranged >> (index * columns)) & mask for index in range(rows))


def screen_partition_bounded_rank(
    bits: int, n_vars: int, row_variables: Iterable[int],
) -> tuple[tuple[GF2CandidateDescriptor, ...], BoundedRankResult]:
    _validate_bits(bits, n_vars)
    row, _column = _partition(row_variables, n_vars)
    arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
    rows, columns = 1 << row_count, 1 << column_count
    full_bits = rows * columns
    cost_per_rank = rows + columns
    noncompressing_rank = (full_bits + cost_per_rank - 1) // cost_per_rank
    bounded = gf2_rank_factor_bounded(
        _matrix_rows(arranged, rows, columns), columns, noncompressing_rank)
    descriptors: list[GF2CandidateDescriptor] = []
    if not bounded.pruned and bounded.rank:
        factor_bits = bounded.rank * cost_per_rank
        if factor_bits < full_bits:
            descriptors.append(GF2CandidateDescriptor(
                "gf2_rank", factor_bits,
                {"rank": bounded.rank,
                 "row_coefficients": list(bounded.coefficients or ()),
                 "basis_rows": list(bounded.basis or ()),
                 "matrix_shape": [rows, columns]}, row))
    descriptors.extend(_cofactor_descriptors(arranged, rows, columns, row))
    descriptors.extend(_kronecker_descriptors(arranged, row_count, column_count, row))
    return tuple(descriptors), bounded


def analyze_screened_exact_gf2_bounded_rank(
    bits: int, n_vars: int, *, row_partitions: Iterable[Iterable[int]] | None = None,
    max_partitions: int = 64, materialize_budget: int = 4,
) -> tuple[ExactGF2Analysis, dict[str, int]]:
    _validate_bits(bits, n_vars)
    if type(materialize_budget) is not int or not 1 <= materialize_budget <= 64:
        raise ValueError("invalid GF(2) materialization budget")
    partitions = (candidate_partitions(bits, n_vars, max_partitions)
                  if row_partitions is None
                  else tuple(tuple(row) for row in row_partitions))
    if not partitions:
        raise ValueError("GF(2) analyzer requires at least one partition")
    candidates = []
    xor = xor_component_artifact(bits, n_vars)
    if xor is not None:
        candidates.append(xor)
    descriptors = []
    rank_results = []
    for row in partitions:
        found, bounded = screen_partition_bounded_rank(bits, n_vars, row)
        descriptors.extend(found)
        rank_results.append(bounded)
    unique: dict[str, GF2CandidateDescriptor] = {}
    for descriptor in descriptors:
        unique.setdefault(descriptor.digest(bits, n_vars), descriptor)
    ordered = sorted(unique.values(), key=lambda item: item.sort_key(bits, n_vars))
    candidates.extend(descriptor.materialize(bits, n_vars)
                      for descriptor in ordered[:materialize_budget])
    seen = set()
    exact = []
    for candidate in candidates:
        if candidate.digest in seen:
            continue
        if candidate.reconstruct() != bits:
            raise RuntimeError("bounded-rank candidate escaped exact reconstruction")
        seen.add(candidate.digest)
        exact.append(candidate)
    exact.sort(key=lambda item: (item.document["factor_bits"], item.kind,
                                 item.document["row_variables"], item.digest))
    analysis = ExactGF2Analysis(
        n_vars, truth_sha256(bits, n_vars), len(partitions), tuple(exact),
        descriptors_screened=len(unique), artifacts_materialized=len(exact))
    total_rows = sum(result.total_rows for result in rank_results)
    scanned_rows = sum(result.rows_scanned for result in rank_results)
    return analysis, {
        "rank_partitions": len(rank_results),
        "rank_partitions_pruned": sum(result.pruned for result in rank_results),
        "rank_rows_total": total_rows,
        "rank_rows_scanned": scanned_rows,
        "rank_rows_pruned": total_rows - scanned_rows,
    }
