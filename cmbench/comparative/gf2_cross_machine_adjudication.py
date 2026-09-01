"""No-refit cross-machine profitability adjudication for frozen C27 timings."""
from __future__ import annotations

from functools import lru_cache
import itertools
import math
import statistics
from typing import Any, Iterable, Sequence

from cmbench.comparative.gf2_resident_session_experiment import N_VARS, QUERY_COUNTS


BASELINE = "resident_direct_screened"
CANDIDATE = "support_aware_c27_advice_on"
ROUNDS = (0, 1, 2, 3, 4)
AGGREGATE_FLOOR = 1.0
MINIMUM_WIDTH_FLOOR = 0.90
CONFIDENCE_LEVEL = 0.95


def percentile_nearest_rank(values: Sequence[float], probability: float) -> float:
    """Return the deterministic nearest-rank empirical percentile."""
    if not values or not 0.0 < probability <= 1.0:
        raise ValueError("percentile requires values and probability in (0, 1]")
    ordered = sorted(float(value) for value in values)
    if any(not math.isfinite(value) or value <= 0.0 for value in ordered):
        raise ValueError("profitability samples must be positive and finite")
    rank = max(1, math.ceil(probability * len(ordered)))
    return ordered[rank - 1]


@lru_cache(maxsize=1)
def paired_round_resamples() -> tuple[tuple[int, ...], ...]:
    """Enumerate the complete five-of-five paired round bootstrap distribution."""
    return tuple(itertools.product(ROUNDS, repeat=len(ROUNDS)))


def _timing_index(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int, int, int], int]:
    index: dict[tuple[str, int, int, int], int] = {}
    for row in rows:
        key = (row.get("method"), row.get("n_vars"), row.get("query_count"),
               row.get("round"))
        if key in index:
            raise ValueError(f"duplicate C27 timing identity: {key}")
        timings = row.get("timings_ns")
        total = timings.get("batch_total_ns") if isinstance(timings, dict) else None
        if (
            row.get("exact_check_passed") is not True
            or type(total) is not int
            or total <= 0
        ):
            raise ValueError(f"invalid or inexact C27 timing row: {key}")
        index[key] = total
    return index


def _profitability_for_round_sample(
    index: dict[tuple[str, int, int, int], int],
    query_count: int,
    rounds: Sequence[int],
) -> tuple[float, float, dict[str, float]]:
    baseline_by_width = {}
    candidate_by_width = {}
    for n_vars in N_VARS:
        baseline_by_width[n_vars] = statistics.median(
            index[(BASELINE, n_vars, query_count, round_index)] for round_index in rounds)
        candidate_by_width[n_vars] = statistics.median(
            index[(CANDIDATE, n_vars, query_count, round_index)] for round_index in rounds)
    by_width = {
        str(n_vars): baseline_by_width[n_vars] / candidate_by_width[n_vars]
        for n_vars in N_VARS
    }
    aggregate = sum(baseline_by_width.values()) / sum(candidate_by_width.values())
    return aggregate, min(by_width.values()), by_width


def adjudicate_execution(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Compute point and exhaustive paired-bootstrap gates for one execution."""
    expected = {
        (method, n_vars, query_count, round_index)
        for method in (BASELINE, CANDIDATE)
        for n_vars in N_VARS
        for query_count in QUERY_COUNTS
        for round_index in ROUNDS
    }
    index = _timing_index(row for row in rows if row.get("method") in (BASELINE, CANDIDATE))
    if set(index) != expected:
        missing = len(expected - set(index))
        extra = len(set(index) - expected)
        raise ValueError(f"C27 paired timing surface mismatch: missing={missing}, extra={extra}")
    samples = paired_round_resamples()
    by_query_count = {}
    for query_count in QUERY_COUNTS:
        point_aggregate, point_minimum, by_width = _profitability_for_round_sample(
            index, query_count, ROUNDS)
        aggregate_samples = []
        minimum_samples = []
        for sample in samples:
            aggregate, minimum, _ = _profitability_for_round_sample(
                index, query_count, sample)
            aggregate_samples.append(aggregate)
            minimum_samples.append(minimum)
        aggregate_lower = percentile_nearest_rank(
            aggregate_samples, 1.0 - CONFIDENCE_LEVEL)
        minimum_lower = percentile_nearest_rank(
            minimum_samples, 1.0 - CONFIDENCE_LEVEL)
        point_gate = (
            point_aggregate >= AGGREGATE_FLOOR
            and point_minimum >= MINIMUM_WIDTH_FLOOR
        )
        uncertainty_gate = (
            aggregate_lower >= AGGREGATE_FLOOR
            and minimum_lower >= MINIMUM_WIDTH_FLOOR
        )
        by_query_count[str(query_count)] = {
            "aggregate_speedup_over_direct_screened": point_aggregate,
            "minimum_width_speedup_over_direct_screened": point_minimum,
            "by_width_speedup_over_direct_screened": by_width,
            "paired_round_bootstrap_95_lower": {
                "aggregate_speedup_over_direct_screened": aggregate_lower,
                "minimum_width_speedup_over_direct_screened": minimum_lower,
            },
            "point_gate": point_gate,
            "uncertainty_gate": uncertainty_gate,
            "admissible": point_gate and uncertainty_gate,
        }
    return {
        "schema": "crse-c28-execution-profitability-adjudication/v1",
        "baseline": BASELINE,
        "candidate": CANDIDATE,
        "rounds": list(ROUNDS),
        "paired_round_resamples": len(samples),
        "confidence_level": CONFIDENCE_LEVEL,
        "bootstrap_scope": (
            "complete paired round resampling within one execution; conditional on the "
            "five recorded rounds and not an independent hardware confidence interval"
        ),
        "by_query_count": by_query_count,
    }


def monotonic_suffix_start(admissible_query_counts: Sequence[int]) -> int | None:
    """Return the first query count whose complete measured suffix is admissible."""
    admissible = set(admissible_query_counts)
    return next((query_count for query_count in QUERY_COUNTS
                 if all(later in admissible for later in QUERY_COUNTS
                        if later >= query_count)), None)


def adjudicate_cross_machine(executions: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Take the fail-closed envelope across frozen execution and machine identities."""
    execution_ids = [row.get("execution_id") for row in executions]
    if len(executions) < 2 or any(type(value) is not str or not value for value in execution_ids):
        raise ValueError("cross-machine adjudication requires named executions")
    if len(set(execution_ids)) != len(execution_ids):
        raise ValueError("execution identities must be unique")
    physical_ids = [row.get("physical_machine_id") for row in executions]
    if any(type(value) is not str or not value for value in physical_ids):
        raise ValueError("every execution requires a physical-machine identity")
    if len(set(physical_ids)) < 2:
        raise ValueError("cross-machine adjudication requires at least two physical machines")

    execution_results = []
    for execution in executions:
        result = adjudicate_execution(execution["rows"])
        execution_results.append({
            "execution_id": execution["execution_id"],
            "physical_machine_id": execution["physical_machine_id"],
            "environment": execution["environment"],
            "independent_verification_sha256": execution[
                "independent_verification_sha256"],
            "measurements_sha256": execution["measurements_sha256"],
            **result,
        })

    by_query_count = {}
    admissible_counts = []
    point_only_counts = []
    for query_count in QUERY_COUNTS:
        key = str(query_count)
        records = [row["by_query_count"][key] for row in execution_results]
        point_aggregate_floor = min(
            row["aggregate_speedup_over_direct_screened"] for row in records)
        point_minimum_floor = min(
            row["minimum_width_speedup_over_direct_screened"] for row in records)
        bootstrap_aggregate_floor = min(
            row["paired_round_bootstrap_95_lower"][
                "aggregate_speedup_over_direct_screened"] for row in records)
        bootstrap_minimum_floor = min(
            row["paired_round_bootstrap_95_lower"][
                "minimum_width_speedup_over_direct_screened"] for row in records)
        point_gate = all(row["point_gate"] for row in records)
        uncertainty_gate = all(row["uncertainty_gate"] for row in records)
        admissible = point_gate and uncertainty_gate
        if point_gate:
            point_only_counts.append(query_count)
        if admissible:
            admissible_counts.append(query_count)
        failures = [
            {"execution_id": execution["execution_id"],
             "point_gate": record["point_gate"],
             "uncertainty_gate": record["uncertainty_gate"]}
            for execution, record in zip(execution_results, records)
            if not record["admissible"]
        ]
        by_query_count[key] = {
            "cross_execution_point_floor": {
                "aggregate_speedup_over_direct_screened": point_aggregate_floor,
                "minimum_width_speedup_over_direct_screened": point_minimum_floor,
            },
            "cross_execution_paired_bootstrap_95_lower_floor": {
                "aggregate_speedup_over_direct_screened": bootstrap_aggregate_floor,
                "minimum_width_speedup_over_direct_screened": bootstrap_minimum_floor,
            },
            "point_gate_all_executions": point_gate,
            "uncertainty_gate_all_executions": uncertainty_gate,
            "admissible": admissible,
            "failed_executions": failures,
        }

    suffix_start = monotonic_suffix_start(admissible_counts)
    point_suffix_start = monotonic_suffix_start(point_only_counts)
    return {
        "schema": "crse-c28-cross-machine-profitability-adjudication/v1",
        "policy_refit": False,
        "training": False,
        "timings_rerun": False,
        "baseline": BASELINE,
        "candidate": CANDIDATE,
        "thresholds": {
            "aggregate_speedup_over_direct_screened_minimum": AGGREGATE_FLOOR,
            "minimum_width_speedup_over_direct_screened_minimum": MINIMUM_WIDTH_FLOOR,
            "paired_round_bootstrap_confidence_level": CONFIDENCE_LEVEL,
        },
        "execution_count": len(executions),
        "physical_machine_count": len(set(physical_ids)),
        "physical_machine_ids": sorted(set(physical_ids)),
        "execution_results": execution_results,
        "by_query_count": by_query_count,
        "point_admissible_query_counts": point_only_counts,
        "uncertainty_admissible_query_counts": admissible_counts,
        "point_monotonic_suffix_start": point_suffix_start,
        "uncertainty_monotonic_suffix_start": suffix_start,
        "exact_length_research_candidates": admissible_counts,
        "shadow_promotion": suffix_start is not None,
        "production_promotion": False,
        "decision": (
            "admit_monotonic_shadow_suffix" if suffix_start is not None
            else "refuse_shadow_promotion_no_uncertainty_safe_monotonic_suffix"
        ),
        "limitations": [
            "Only two physical machines are represented.",
            "Three Docker repetitions share the Windows machine and are not independent machines.",
            "Five rounds per execution support only a conditional resampling diagnostic.",
            "The adjudicator evaluates the frozen C27 corpus and policy; it does not refit either.",
        ],
    }
