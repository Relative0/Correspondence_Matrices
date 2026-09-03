"""Exact arbitrary-lane batching for repeated Boolean restrictions.

Two development backends are provided:

``concatenated``
    Append every query's compatible complete assignments as contiguous packed
    lanes.  Duplicate complete assignments remain duplicated, but the source
    DAG is traversed once and each query result is a slice.

``union_care``
    Deduplicate compatible complete assignments across the query set, evaluate
    that care set once, then gather each query's canonical residual ordering.

Packed Boolean operators are exact for arbitrary lane assignments; a lane need
not belong to a Cartesian truth table.  These helpers do not select a backend
or change the C36 delivery contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any

from .gf2_restricted_evaluators import (
    PreparedRestriction,
    RestrictedArena,
    eval_restricted_r2,
)


BATCH_MODES = ("concatenated", "union_care")


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class MultiQueryBatchPlan:
    mode: str
    n_vars: int
    assignments: tuple[int, ...]
    query_lane_indices: tuple[tuple[int, ...], ...]
    requested_lane_count: int

    @property
    def lane_count(self) -> int:
        return len(self.assignments)

    @property
    def full_truth_lane_count(self) -> int:
        return 1 << self.n_vars


def complete_assignments_for_query(
    query: Mapping[str, Any], n_vars: int,
) -> tuple[int, ...]:
    """Return compatible complete-assignment indexes in residual-bit order."""
    fixed_rows = query.get("fixed")
    remaining = query.get("remaining_order")
    _require(isinstance(fixed_rows, list) and isinstance(remaining, list),
             "batch query fields")
    fixed = {int(row["variable"][1:]): row["value"] for row in fixed_rows}
    remaining_indices = tuple(int(name[1:]) for name in remaining)
    _require(
        fixed
        and remaining_indices
        and set(fixed).isdisjoint(remaining_indices)
        and set(fixed) | set(remaining_indices) == set(range(n_vars))
        and all(type(value) is int and value in (0, 1) for value in fixed.values()),
        "batch query variable partition",
    )
    assignments: list[int] = []
    for residual in range(1 << len(remaining_indices)):
        values = dict(fixed)
        for position, variable in enumerate(remaining_indices):
            values[variable] = (
                residual >> (len(remaining_indices) - 1 - position)) & 1
        complete = 0
        for variable in range(n_vars):
            complete = (complete << 1) | values[variable]
        assignments.append(complete)
    return tuple(assignments)


def build_multi_query_batch_plan(
    trace: Sequence[Mapping[str, Any]], n_vars: int, mode: str,
) -> MultiQueryBatchPlan:
    _require(mode in BATCH_MODES and 1 <= len(trace) <= 4096 and 1 <= n_vars <= 24,
             "invalid multi-query batch bounds")
    per_query = [complete_assignments_for_query(query, n_vars) for query in trace]
    requested = sum(len(assignments) for assignments in per_query)
    if mode == "concatenated":
        assignments: list[int] = []
        query_lanes: list[tuple[int, ...]] = []
        for values in per_query:
            offset = len(assignments)
            assignments.extend(values)
            query_lanes.append(tuple(range(offset, offset + len(values))))
    else:
        assignments = []
        lane_by_assignment: dict[int, int] = {}
        query_lanes = []
        for values in per_query:
            lanes: list[int] = []
            for assignment in values:
                lane = lane_by_assignment.get(assignment)
                if lane is None:
                    lane = len(assignments)
                    lane_by_assignment[assignment] = lane
                    assignments.append(assignment)
                lanes.append(lane)
            query_lanes.append(tuple(lanes))
    return MultiQueryBatchPlan(
        mode=mode,
        n_vars=n_vars,
        assignments=tuple(assignments),
        query_lane_indices=tuple(query_lanes),
        requested_lane_count=requested,
    )


def prepare_arbitrary_assignment_lanes(
    assignments: Sequence[int], n_vars: int,
) -> PreparedRestriction:
    """Build packed variable masks for arbitrary complete-assignment lanes."""
    normalized = tuple(assignments)
    _require(
        normalized
        and 1 <= n_vars <= 24
        and all(type(assignment) is int and 0 <= assignment < (1 << n_vars)
                for assignment in normalized),
        "invalid arbitrary assignment lanes",
    )
    byte_count = (len(normalized) + 7) // 8
    buffers = [bytearray(byte_count) for _ in range(n_vars)]
    for lane, assignment in enumerate(normalized):
        byte_index = lane >> 3
        bit = 1 << (lane & 7)
        for variable in range(n_vars):
            if assignment & (1 << (n_vars - 1 - variable)):
                buffers[variable][byte_index] |= bit
    environment = {
        f"x{variable}": int.from_bytes(buffer, "little")
        for variable, buffer in enumerate(buffers)
    }
    return PreparedRestriction(
        fixed={},
        remaining=tuple(environment),
        environment=environment,
        full_mask=(1 << len(normalized)) - 1,
    )


def evaluate_multi_query_batch(
    arena: RestrictedArena, plan: MultiQueryBatchPlan,
) -> tuple[int, ...]:
    prepared = prepare_arbitrary_assignment_lanes(plan.assignments, plan.n_vars)
    packed = eval_restricted_r2(arena, prepared)
    return gather_multi_query_batch(packed, plan)


def gather_multi_query_batch(
    packed: int, plan: MultiQueryBatchPlan,
) -> tuple[int, ...]:
    """Gather canonical per-query packed truths from evaluated batch lanes."""
    outputs: list[int] = []
    if plan.mode == "concatenated":
        offset = 0
        for lanes in plan.query_lane_indices:
            width = len(lanes)
            if lanes != tuple(range(offset, offset + width)):
                raise AssertionError("concatenated lanes lost contiguity")
            outputs.append((packed >> offset) & ((1 << width) - 1))
            offset += width
        return tuple(outputs)
    for lanes in plan.query_lane_indices:
        reduced = 0
        for residual, lane in enumerate(lanes):
            reduced |= ((packed >> lane) & 1) << residual
        outputs.append(reduced)
    return tuple(outputs)


def batch_plan_metrics(plan: MultiQueryBatchPlan) -> dict[str, Any]:
    return {
        "mode": plan.mode,
        "queries": len(plan.query_lane_indices),
        "requested_lane_count": plan.requested_lane_count,
        "evaluated_lane_count": plan.lane_count,
        "full_truth_lane_count": plan.full_truth_lane_count,
        "deduplicated_lane_count": plan.requested_lane_count - plan.lane_count,
        "care_coverage_numerator": plan.lane_count,
        "care_coverage_denominator": plan.full_truth_lane_count,
        "lane_mapping_entries": plan.requested_lane_count,
    }
