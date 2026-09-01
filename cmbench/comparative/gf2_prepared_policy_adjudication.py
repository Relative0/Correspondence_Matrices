"""Prospective cross-machine adjudication for the frozen C30 q8 experiment."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import statistics
from typing import Any

from .gf2_prepared_policy_experiment import (
    BASELINE,
    CANDIDATE,
    METHODS,
    C30Config,
    build_schedule,
    summarize,
)
from .gf2_resident_session_experiment import N_VARS


BLOCKS = 16
CONFIDENCE_LEVEL = 0.95
AGGREGATE_POINT_FLOOR = 1.0
MINIMUM_WIDTH_POINT_FLOOR = 0.90
AGGREGATE_PAIRED_LOWER_FLOOR = 1.0
MINIMUM_WIDTH_PAIRED_LOWER_FLOOR = 0.90


def _positive_finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(
        value) and value > 0


def _sha256_text(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def median_lower_order_statistic_rank(
    sample_count: int = BLOCKS,
    confidence_level: float = CONFIDENCE_LEVEL,
) -> tuple[int, float]:
    """Return an exact distribution-free one-sided lower bound for a median.

    Rank ``k`` is the largest lower order statistic whose under-coverage
    probability ``P(Binomial(n, 0.5) <= k - 1)`` does not exceed ``1-confidence``.
    The returned coverage is therefore at least the requested confidence level.
    """
    if (
        type(sample_count) is not int
        or sample_count < 1
        or type(confidence_level) not in (int, float)
        or not math.isfinite(confidence_level)
        or not 0.5 < confidence_level < 1.0
    ):
        raise ValueError("invalid median lower-bound contract")
    alpha = 1.0 - float(confidence_level)
    denominator = 2**sample_count
    rank = 0
    undercoverage = 0.0
    for candidate in range(1, sample_count + 1):
        candidate_undercoverage = sum(
            math.comb(sample_count, count) for count in range(candidate)
        ) / denominator
        if candidate_undercoverage <= alpha:
            rank = candidate
            undercoverage = candidate_undercoverage
        else:
            break
    if rank < 1:
        raise ValueError("sample count cannot provide the requested median lower bound")
    return rank, 1.0 - undercoverage


def median_lower_bound(values: Sequence[float]) -> float:
    if len(values) != BLOCKS or any(not _positive_finite(value) for value in values):
        raise ValueError(f"C31 requires exactly {BLOCKS} positive paired-block values")
    rank, _ = median_lower_order_statistic_rank()
    return sorted(float(value) for value in values)[rank - 1]


def _execution_index(
    rows: Sequence[dict[str, Any]],
) -> dict[tuple[int, int, int], dict[str, Any]]:
    schedule = build_schedule(C30Config("c31-adjudication", blocks=BLOCKS))
    expected = {
        (cell["block"], cell["n_vars"], cell["arm_position"]): cell
        for cell in schedule
    }
    if len(rows) != len(schedule):
        raise ValueError("C31 measurement cardinality mismatch")
    index: dict[tuple[int, int, int], dict[str, Any]] = {}
    for row in rows:
        identity = (row.get("block"), row.get("n_vars"), row.get("arm_position"))
        if identity in index or identity not in expected:
            raise ValueError("C31 duplicate or unknown schedule identity")
        cell = expected[identity]
        for field in (
            "block", "pair_id", "n_vars", "width_position", "arm_position", "method"
        ):
            if row.get(field) != cell[field]:
                raise ValueError(f"C31 frozen schedule mismatch: {field}")
        index[identity] = row
    if set(index) != set(expected):
        raise ValueError("C31 incomplete frozen schedule")
    return index


def adjudicate_execution(
    rows: Sequence[dict[str, Any]],
    *,
    lifecycle_preparation_ns: int,
) -> dict[str, Any]:
    """Adjudicate one unchanged C30 execution using its 16 paired blocks."""
    index = _execution_index(rows)
    summary = summarize(list(rows), lifecycle_preparation_ns=lifecycle_preparation_ns)
    width_ratios: dict[str, list[float]] = {str(n_vars): [] for n_vars in N_VARS}
    aggregate_ratios = []
    for block in range(BLOCKS):
        block_rows = [row for (row_block, _, _), row in index.items() if row_block == block]
        if len(block_rows) != len(N_VARS) * len(METHODS):
            raise ValueError("C31 block cardinality mismatch")
        baseline_total = sum(
            row["timings_ns"]["batch_total_ns"]
            for row in block_rows if row["method"] == BASELINE
        )
        candidate_total = sum(
            row["timings_ns"]["batch_total_ns"]
            + row["lifecycle_preparation_charge_ns"]
            for row in block_rows if row["method"] == CANDIDATE
        )
        for n_vars in N_VARS:
            selected = [
                row for (row_block, row_n_vars, _), row in index.items()
                if row_block == block and row_n_vars == n_vars
            ]
            if len(selected) != 2 or {row["method"] for row in selected} != set(METHODS):
                raise ValueError("C31 paired width cell mismatch")
            by_method = {row["method"]: row for row in selected}
            baseline = by_method[BASELINE]["timings_ns"]["batch_total_ns"]
            candidate_row = by_method[CANDIDATE]
            candidate = (
                candidate_row["timings_ns"]["batch_total_ns"]
                + candidate_row["lifecycle_preparation_charge_ns"]
            )
            if not _positive_finite(baseline) or not _positive_finite(candidate):
                raise ValueError("C31 invalid paired timing")
            width_ratios[str(n_vars)].append(baseline / candidate)
        if not baseline_total or not candidate_total:
            raise ValueError("C31 block coverage mismatch")
        aggregate_ratios.append(baseline_total / candidate_total)

    rank, achieved_confidence = median_lower_order_statistic_rank()
    aggregate_lower = median_lower_bound(aggregate_ratios)
    width_lower = {
        width: median_lower_bound(values) for width, values in width_ratios.items()
    }
    paired_lower_minimum = min(width_lower.values())
    point_gate = (
        summary["aggregate_ratio_of_median_charged_total_speedup"]
        >= AGGREGATE_POINT_FLOOR
        and summary["minimum_width_ratio_of_median_charged_total_speedup"]
        >= MINIMUM_WIDTH_POINT_FLOOR
    )
    paired_lower_gate = (
        aggregate_lower >= AGGREGATE_PAIRED_LOWER_FLOOR
        and paired_lower_minimum >= MINIMUM_WIDTH_PAIRED_LOWER_FLOOR
    )
    return {
        "schema": "crse-c31-prepared-policy-execution-adjudication/v1",
        "point_estimates": {
            "aggregate_ratio_of_median_charged_total_speedup": summary[
                "aggregate_ratio_of_median_charged_total_speedup"
            ],
            "minimum_width_ratio_of_median_charged_total_speedup": summary[
                "minimum_width_ratio_of_median_charged_total_speedup"
            ],
            "by_width": {
                width: row["ratio_of_median_charged_total_speedup"]
                for width, row in summary["by_width"].items()
            },
        },
        "paired_block_median_lower_bounds": {
            "method": "exact_distribution_free_one_sided_binomial_order_statistic",
            "requested_confidence_level": CONFIDENCE_LEVEL,
            "achieved_confidence_level": achieved_confidence,
            "sample_count": BLOCKS,
            "order_statistic_rank_one_based": rank,
            "aggregate_speedup": aggregate_lower,
            "minimum_width_speedup": paired_lower_minimum,
            "by_width_speedup": width_lower,
        },
        "point_gate": point_gate,
        "paired_lower_gate": paired_lower_gate,
        "admissible": point_gate and paired_lower_gate,
        "measurement_batches": summary["measurement_batches"],
        "paired_batches": summary["paired_batches"],
        "timed_queries": summary["timed_queries"],
        "lifecycle_preparation_ns": lifecycle_preparation_ns,
        "preparation_charge_conserved": summary[
            "lifecycle_preparation_charge_conserved"
        ],
    }


def adjudicate_cross_machine(executions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Apply the frozen C31 gates across at least two physical machines."""
    if len(executions) < 2:
        raise ValueError("C31 requires at least two executions")
    execution_ids = [execution.get("execution_id") for execution in executions]
    machine_ids = [execution.get("physical_machine_id") for execution in executions]
    if (
        any(not isinstance(value, str) or not value for value in execution_ids + machine_ids)
        or len(set(execution_ids)) != len(execution_ids)
        or len(set(machine_ids)) < 2
    ):
        raise ValueError("C31 requires unique executions on two physical machines")

    results = []
    for execution in executions:
        if (
            not _sha256_text(execution.get("measurements_sha256"))
            or not _sha256_text(execution.get("independent_verification_sha256"))
            or not isinstance(execution.get("environment"), Mapping)
        ):
            raise ValueError("C31 execution evidence identity is incomplete")
        result = adjudicate_execution(
            execution["rows"],
            lifecycle_preparation_ns=execution["lifecycle_preparation_ns"],
        )
        results.append({
            "execution_id": execution["execution_id"],
            "physical_machine_id": execution["physical_machine_id"],
            "environment": dict(execution["environment"]),
            "measurements_sha256": execution["measurements_sha256"],
            "independent_verification_sha256": execution[
                "independent_verification_sha256"
            ],
            **result,
        })

    point_aggregate_floor = min(
        row["point_estimates"]["aggregate_ratio_of_median_charged_total_speedup"]
        for row in results
    )
    point_width_floor = min(
        row["point_estimates"]["minimum_width_ratio_of_median_charged_total_speedup"]
        for row in results
    )
    paired_aggregate_floor = min(
        row["paired_block_median_lower_bounds"]["aggregate_speedup"]
        for row in results
    )
    paired_width_floor = min(
        row["paired_block_median_lower_bounds"]["minimum_width_speedup"]
        for row in results
    )
    all_exact = all(
        row["measurement_batches"] == 128
        and row["paired_batches"] == 64
        and row["timed_queries"] == 1024
        and row["preparation_charge_conserved"] is True
        for row in results
    )
    point_gate = all(row["point_gate"] for row in results)
    paired_lower_gate = all(row["paired_lower_gate"] for row in results)
    admissible = all_exact and point_gate and paired_lower_gate
    return {
        "schema": "crse-c31-prepared-policy-cross-machine-adjudication/v1",
        "policy_refit": False,
        "training": False,
        "timings_rerun_by_adjudicator": False,
        "thresholds": {
            "aggregate_point_minimum": AGGREGATE_POINT_FLOOR,
            "minimum_width_point_minimum": MINIMUM_WIDTH_POINT_FLOOR,
            "aggregate_paired_median_lower_minimum": AGGREGATE_PAIRED_LOWER_FLOOR,
            "minimum_width_paired_median_lower_minimum": MINIMUM_WIDTH_PAIRED_LOWER_FLOOR,
            "paired_median_lower_confidence_level": CONFIDENCE_LEVEL,
        },
        "execution_count": len(results),
        "physical_machine_count": len(set(machine_ids)),
        "physical_machine_ids": sorted(set(machine_ids)),
        "execution_results": results,
        "cross_machine_floors": {
            "aggregate_point": point_aggregate_floor,
            "minimum_width_point": point_width_floor,
            "aggregate_paired_median_lower": paired_aggregate_floor,
            "minimum_width_paired_median_lower": paired_width_floor,
        },
        "exactness_and_charge_gate": all_exact,
        "point_gate_all_executions": point_gate,
        "paired_lower_gate_all_executions": paired_lower_gate,
        "replication_admissible": admissible,
        "eligible_for_separate_shadow_review": admissible,
        "shadow_promotion": False,
        "production_promotion": False,
        "decision": (
            "replicated_candidate_eligible_for_separate_shadow_review"
            if admissible
            else "refuse_replication_admission"
        ),
        "limitations": [
            "The paired-block lower bound treats the 16 prespecified blocks as the sampling unit.",
            "The exact order-statistic interval is distribution-free but does not model machine populations.",
            "Two physical machines are a minimum replication surface, not broad hardware coverage.",
            "Passing C31 does not itself authorize shadow or production promotion.",
        ],
    }
