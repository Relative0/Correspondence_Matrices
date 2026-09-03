"""Development-only exact projection variants for repeated GF(2) restrictions.

The frozen C36 implementation deliberately remains unchanged.  This module
isolates the projection-internal candidates proposed after C36:

* the narrowest safe NumPy index dtype;
* one contiguous index arena instead of 64 separately owned arrays; and
* packed-integer cofactoring, which avoids expanding the full truth table to
  one byte per row.

All helpers preserve C36's MSB-first variable order and little-endian packed
truth-bit convention.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def minimum_projection_dtype(n_vars: int) -> np.dtype[Any]:
    """Return the narrowest unsigned dtype that can address ``2**n_vars`` rows."""
    _require(type(n_vars) is int and 1 <= n_vars <= 63, "invalid projection width")
    if n_vars <= 8:
        return np.dtype(np.uint8)
    if n_vars <= 16:
        return np.dtype(np.uint16)
    if n_vars <= 32:
        return np.dtype(np.uint32)
    return np.dtype(np.uint64)


def projection_indices_typed(
    n_vars: int,
    fixed: Mapping[str, int],
    remaining: Sequence[str],
    *,
    dtype: np.dtype[Any] | type[np.unsignedinteger[Any]] | None = None,
    out: np.ndarray | None = None,
) -> np.ndarray:
    """Compile one exact restriction to original truth-vector row indices."""
    index_dtype = minimum_projection_dtype(n_vars) if dtype is None else np.dtype(dtype)
    _require(index_dtype.kind == "u", "projection indices require an unsigned dtype")
    _require((1 << n_vars) - 1 <= np.iinfo(index_dtype).max,
             "projection index dtype is too narrow")
    remaining_indices = tuple(int(name[1:]) for name in remaining)
    fixed_indices = {int(name[1:]): value for name, value in fixed.items()}
    _require(
        len(remaining_indices) >= 1
        and len(set(remaining_indices)) == len(remaining_indices)
        and all(type(value) is int and value in (0, 1)
                for value in fixed_indices.values())
        and set(remaining_indices).isdisjoint(fixed_indices)
        and set(remaining_indices) | set(fixed_indices) == set(range(n_vars)),
        "invalid projection axis partition",
    )
    size = 1 << len(remaining_indices)
    if out is None:
        indices = np.zeros(size, dtype=index_dtype)
    else:
        _require(
            isinstance(out, np.ndarray)
            and out.dtype == index_dtype
            and out.ndim == 1
            and out.size == size
            and out.flags.writeable,
            "invalid projection output buffer",
        )
        indices = out
        indices.fill(0)
    scalar = index_dtype.type
    rows = np.arange(size, dtype=index_dtype)
    for index, value in fixed_indices.items():
        if value:
            indices |= scalar(1 << (n_vars - 1 - index))
    for position, index in enumerate(remaining_indices):
        values = (rows >> scalar(len(remaining_indices) - 1 - position)) & scalar(1)
        indices |= values << scalar(n_vars - 1 - index)
    if out is None:
        indices.flags.writeable = False
    return indices


@dataclass(frozen=True)
class FlatProjectionPlan:
    """One immutable index arena with an offset pair for every query."""

    indices: np.ndarray
    offsets: tuple[int, ...]
    dtype_name: str

    @property
    def query_count(self) -> int:
        return len(self.offsets) - 1

    @property
    def index_bytes(self) -> int:
        return int(self.indices.nbytes)

    def query_indices(self, query: int) -> np.ndarray:
        _require(type(query) is int and 0 <= query < self.query_count,
                 "projection query out of range")
        return self.indices[self.offsets[query]:self.offsets[query + 1]]


def compile_flat_projection_plan(
    n_vars: int,
    queries: Sequence[Mapping[str, Any]],
    *,
    dtype: np.dtype[Any] | type[np.unsignedinteger[Any]] | None = None,
) -> FlatProjectionPlan:
    """Compile all query indices directly into one exactly sized arena."""
    index_dtype = minimum_projection_dtype(n_vars) if dtype is None else np.dtype(dtype)
    lengths = [1 << len(query["remaining_order"]) for query in queries]
    offsets = [0]
    for length in lengths:
        offsets.append(offsets[-1] + length)
    arena = np.empty(offsets[-1], dtype=index_dtype)
    for query, start, stop in zip(queries, offsets, offsets[1:]):
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        projection_indices_typed(
            n_vars,
            fixed,
            query["remaining_order"],
            dtype=index_dtype,
            out=arena[start:stop],
        )
    arena.flags.writeable = False
    return FlatProjectionPlan(
        indices=arena,
        offsets=tuple(offsets),
        dtype_name=index_dtype.name,
    )


@dataclass(frozen=True)
class CofactorStep:
    """One packed cofactor operation after earlier fixed axes were removed."""

    stride: int
    block_count: int
    source_offset: int
    chunk_mask: int


@dataclass(frozen=True)
class PackedCofactorPlan:
    """Precomputed exact packed-bit extraction schedule for one restriction."""

    n_vars: int
    remaining: tuple[str, ...]
    steps: tuple[CofactorStep, ...]

    @property
    def plan_bytes_estimate(self) -> int:
        # Deterministic payload estimate, not Python allocator accounting.
        return sum(24 + max(1, (step.chunk_mask.bit_length() + 7) // 8)
                   for step in self.steps)


def compile_packed_cofactor_plan(
    n_vars: int,
    fixed: Mapping[str, int],
    remaining: Sequence[str],
) -> PackedCofactorPlan:
    """Compile a restriction into ascending-axis packed cofactor steps."""
    _require(type(n_vars) is int and 1 <= n_vars <= 63, "invalid cofactor width")
    remaining_tuple = tuple(remaining)
    remaining_indices = tuple(int(name[1:]) for name in remaining_tuple)
    fixed_indices = {int(name[1:]): value for name, value in fixed.items()}
    _require(
        remaining_tuple
        and all(type(value) is int and value in (0, 1)
                for value in fixed_indices.values())
        and set(remaining_indices).isdisjoint(fixed_indices)
        and set(remaining_indices) | set(fixed_indices) == set(range(n_vars)),
        "invalid cofactor axis partition",
    )
    current_width = n_vars
    removed = 0
    steps: list[CofactorStep] = []
    for original_index in sorted(fixed_indices):
        position = original_index - removed
        stride = 1 << (current_width - 1 - position)
        steps.append(CofactorStep(
            stride=stride,
            block_count=1 << position,
            source_offset=fixed_indices[original_index] * stride,
            chunk_mask=(1 << stride) - 1,
        ))
        current_width -= 1
        removed += 1
    _require(current_width == len(remaining_tuple), "cofactor residual width")
    return PackedCofactorPlan(
        n_vars=n_vars,
        remaining=remaining_tuple,
        steps=tuple(steps),
    )


def project_packed_truth(bits: int, plan: PackedCofactorPlan) -> int:
    """Apply a compiled cofactor schedule without expanding truth bits to bytes."""
    _require(type(bits) is int and bits >= 0, "invalid packed truth")
    value = bits
    for step in plan.steps:
        source = value >> step.source_offset
        if step.block_count == 1:
            value = source & step.chunk_mask
            continue
        result = 0
        destination_shift = 0
        source_advance = step.stride << 1
        for _ in range(step.block_count):
            result |= (source & step.chunk_mask) << destination_shift
            source >>= source_advance
            destination_shift += step.stride
        value = result
    residual_rows = 1 << len(plan.remaining)
    return value & ((1 << residual_rows) - 1)
