"""Exact C16-style screening with an ANF-basis rank pre-screen.

The ANF rank is used only to reject non-compressing rank candidates before
truth-basis elimination.  Any compressing rank descriptor is still produced
by the existing truth-basis routine, so candidate payloads and deterministic
global-best artifacts remain byte-identical.  Cofactor and Kronecker screens
are unchanged.
"""
from __future__ import annotations

from collections.abc import Iterable

from .gf2_anf_rank import anf_rank, packed_anf_from_truth
from .gf2_decomposition import (
    ExactGF2Analysis,
    GF2CandidateDescriptor,
    _cofactor_descriptors,
    _kronecker_descriptors,
    _partition,
    _rank_descriptor,
    _validate_bits,
    candidate_partitions,
    truth_sha256,
    xor_component_artifact,
)
from .natural_decomposition import partitioned_bits


def screen_partition_anf_rank(
    bits: int,
    polynomial: int,
    n_vars: int,
    row_variables: Iterable[int],
) -> tuple[GF2CandidateDescriptor, ...]:
    """Screen one partition with a sound ANF rank rejection first."""
    _validate_bits(bits, n_vars)
    row, _column = _partition(row_variables, n_vars)
    known_rank = anf_rank(polynomial, n_vars, row)
    arranged, row_count, column_count = partitioned_bits(bits, n_vars, row)
    rows, columns = 1 << row_count, 1 << column_count
    result: list[GF2CandidateDescriptor] = []
    if known_rank and known_rank * (rows + columns) < rows * columns:
        descriptor = _rank_descriptor(arranged, rows, columns, row)
        if descriptor is None or descriptor.payload["rank"] != known_rank:
            raise RuntimeError("ANF rank pre-screen disagreed with truth rank")
        result.append(descriptor)
    result.extend(_cofactor_descriptors(arranged, rows, columns, row))
    result.extend(_kronecker_descriptors(arranged, row_count, column_count, row))
    return tuple(result)


def analyze_screened_exact_gf2_anf_rank(
    bits: int,
    n_vars: int,
    *,
    row_partitions: Iterable[Iterable[int]] | None = None,
    max_partitions: int = 64,
    materialize_budget: int = 4,
    polynomial: int | None = None,
) -> ExactGF2Analysis:
    """Return the same bounded global-best artifact using ANF rank rejection."""
    _validate_bits(bits, n_vars)
    if type(materialize_budget) is not int or not 1 <= materialize_budget <= 64:
        raise ValueError("invalid GF(2) materialization budget")
    partitions = (candidate_partitions(bits, n_vars, max_partitions)
                  if row_partitions is None
                  else tuple(tuple(row) for row in row_partitions))
    if not partitions:
        raise ValueError("GF(2) analyzer requires at least one partition")
    if polynomial is None:
        polynomial = packed_anf_from_truth(bits, n_vars)

    candidates = []
    xor = xor_component_artifact(bits, n_vars)
    if xor is not None:
        candidates.append(xor)
    descriptors = [
        descriptor
        for row in partitions
        for descriptor in screen_partition_anf_rank(bits, polynomial, n_vars, row)
    ]
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
            raise RuntimeError("ANF-screened candidate escaped exact reconstruction")
        seen.add(candidate.digest)
        exact.append(candidate)
    exact.sort(key=lambda item: (item.document["factor_bits"], item.kind,
                                 item.document["row_variables"], item.digest))
    return ExactGF2Analysis(
        n_vars, truth_sha256(bits, n_vars), len(partitions), tuple(exact),
        descriptors_screened=len(unique), artifacts_materialized=len(exact))
