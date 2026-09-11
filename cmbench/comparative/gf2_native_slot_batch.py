"""Exact successor batching for the native one-root fused-slot evaluator.

The original fused-slot source and ABI remain frozen.  This module binds an
additive successor entry point which evaluates equal-width restrictions in one
native call.  Different residual widths are grouped without changing query or
output order.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
import ctypes
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .gf2_native_slots import NativeSlotArena, NativeSlotLibrary


MAX_BATCH_QUERIES = 4096


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def configure_native_slot_batch(library: NativeSlotLibrary) -> int:
    """Validate and bind the additive batch ABI on an already loaded library."""
    handle = library.handle
    _require(
        hasattr(handle, "cm_fused_slots_batch_abi_version")
        and hasattr(handle, "cm_fused_slots_eval_batch"),
        "native fused-slot library lacks the successor batch ABI",
    )
    handle.cm_fused_slots_batch_abi_version.argtypes = []
    handle.cm_fused_slots_batch_abi_version.restype = ctypes.c_uint32
    abi = int(handle.cm_fused_slots_batch_abi_version())
    _require(abi == 1, "unsupported native fused-slot batch ABI")
    handle.cm_fused_slots_eval_batch.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_int16),
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_int16),
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_uint64),
    ]
    handle.cm_fused_slots_eval_batch.restype = ctypes.c_int
    return abi


def prepare_bindings_many(
    arena: NativeSlotArena,
    queries: Sequence[tuple[Mapping[str, int], Sequence[str]]],
) -> tuple[np.ndarray, tuple[int, ...]]:
    """Prepare a contiguous binding matrix while preserving query order."""
    normalized = tuple(queries)
    _require(
        1 <= len(normalized) <= MAX_BATCH_QUERIES,
        "invalid native fused-slot batch size",
    )
    expected = {f"x{index}" for index in range(arena.variable_count)}
    bindings = np.empty(
        (len(normalized), arena.variable_count), dtype=np.int16,
    )
    live_counts: list[int] = []
    for row_index, (fixed, remaining) in enumerate(normalized):
        fixed_map = dict(fixed)
        remaining_tuple = tuple(remaining)
        remaining_positions = {
            name: position for position, name in enumerate(remaining_tuple)
        }
        _require(
            fixed_map
            and remaining_tuple
            and len(remaining_positions) == len(remaining_tuple)
            and set(fixed_map).isdisjoint(remaining_positions)
            and set(fixed_map) | set(remaining_positions) == expected
            and len(remaining_tuple) < 31
            and all(
                type(value) is int and value in (0, 1)
                for value in fixed_map.values()
            ),
            "invalid native fused-slot batch restriction",
        )
        for variable in range(arena.variable_count):
            name = f"x{variable}"
            if name in fixed_map:
                bindings[row_index, variable] = -2 if fixed_map[name] else -1
            else:
                bindings[row_index, variable] = remaining_positions[name]
        live_counts.append(len(remaining_tuple))
    bindings.flags.writeable = False
    return bindings, tuple(live_counts)


@dataclass
class NativeSlotBatchExecutor:
    """Batch-capable exact executor over an existing native slot arena."""

    arena: NativeSlotArena
    batch_abi_version: int = field(init=False)
    _workspaces: dict[int, np.ndarray] = field(
        default_factory=dict, init=False, repr=False,
    )
    _outputs: dict[tuple[int, int], np.ndarray] = field(
        default_factory=dict, init=False, repr=False,
    )

    def __post_init__(self) -> None:
        self.batch_abi_version = configure_native_slot_batch(self.arena.library)

    def evaluate_queries(
        self,
        queries: Sequence[tuple[Mapping[str, int], Sequence[str]]],
    ) -> tuple[int, ...]:
        bindings, live_counts = prepare_bindings_many(self.arena, queries)
        return self._evaluate_prepared(bindings, live_counts, validate_rows=False)

    def evaluate_prepared(
        self,
        bindings: np.ndarray,
        live_counts: Sequence[int],
    ) -> tuple[int, ...]:
        return self._evaluate_prepared(bindings, live_counts, validate_rows=True)

    def _evaluate_prepared(
        self,
        bindings: np.ndarray,
        live_counts: Sequence[int],
        *,
        validate_rows: bool,
    ) -> tuple[int, ...]:
        counts = tuple(live_counts)
        _require(
            isinstance(bindings, np.ndarray)
            and bindings.dtype == np.int16
            and bindings.ndim == 2
            and bindings.shape == (len(counts), self.arena.variable_count)
            and 1 <= len(counts) <= MAX_BATCH_QUERIES
            and all(type(value) is int and 1 <= value < 31 for value in counts),
            "invalid prepared native fused-slot batch",
        )
        if validate_rows:
            for row, live_count in zip(bindings, counts, strict=True):
                values = tuple(int(value) for value in row)
                _require(
                    all(
                        value in (-2, -1) or 0 <= value < live_count
                        for value in values
                    )
                    and {value for value in values if value >= 0}
                    == set(range(live_count)),
                    "invalid prepared native fused-slot binding row",
                )

        grouped: dict[int, list[int]] = defaultdict(list)
        for index, live_count in enumerate(counts):
            grouped[live_count].append(index)
        results = [0] * len(counts)
        pointer = ctypes.POINTER
        handle = self.arena.library.handle
        for live_count, indexes in grouped.items():
            word_count = max(1, ((1 << live_count) + 63) // 64)
            group_bindings = np.ascontiguousarray(bindings[indexes], dtype=np.int16)
            workspace = self._workspaces.get(word_count)
            if workspace is None:
                workspace = np.empty(
                    self.arena.node_count * word_count, dtype=np.uint64,
                )
                self._workspaces[word_count] = workspace
            output_key = (word_count, len(indexes))
            outputs = self._outputs.get(output_key)
            if outputs is None:
                outputs = np.empty((len(indexes), word_count), dtype=np.uint64)
                self._outputs[output_key] = outputs
            status = handle.cm_fused_slots_eval_batch(
                self.arena.opcodes.ctypes.data_as(pointer(ctypes.c_uint8)),
                self.arena.child_a.ctypes.data_as(pointer(ctypes.c_int32)),
                self.arena.child_b.ctypes.data_as(pointer(ctypes.c_int32)),
                self.arena.variable_indices.ctypes.data_as(pointer(ctypes.c_int16)),
                ctypes.c_size_t(self.arena.node_count),
                ctypes.c_size_t(self.arena.root),
                group_bindings.ctypes.data_as(pointer(ctypes.c_int16)),
                ctypes.c_size_t(len(indexes)),
                ctypes.c_size_t(self.arena.variable_count),
                ctypes.c_size_t(live_count),
                ctypes.c_size_t(word_count),
                workspace.ctypes.data_as(pointer(ctypes.c_uint64)),
                outputs.ctypes.data_as(pointer(ctypes.c_uint64)),
            )
            if status != 0:
                raise RuntimeError(
                    "native fused-slot batch evaluator failed "
                    f"with status {status}"
                )
            for group_index, original_index in enumerate(indexes):
                results[original_index] = int.from_bytes(
                    outputs[group_index].tobytes(), "little",
                )
        return tuple(results)
