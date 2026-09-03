"""C33 bounded asynchronous and sampled prepared-policy shadow experiment."""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, replace
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Any, Iterable

from cmbench.recognition.gf2_async_shadow_boundary import (
    PreparedPolicyAsyncShadowBoundary,
    verify_async_shadow_observation,
    verify_async_shadow_serve_result,
)
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
from cmbench.recognition.gf2_prepared_shadow_boundary import (
    PreparedPolicyShadowBoundary,
    verify_prepared_policy_shadow_result,
)
from cmbench.recognition.gf2_prepared_support_context import (
    prepare_support_policy_context,
    verify_prepared_policy_sources,
)
from cmbench.recognition.gf2_source_portfolio import load_source_portfolio_policy
from cmbench.recognition.gf2_support_aware_policy import load_support_aware_policy
from cmbench.recognition.gf2_task_dispatcher import canonical_sha256
from cmbench.recognition.yosys_c27_gf2_data import validate_dataset

from .gf2_resident_session_experiment import N_VARS, case_sequence
from .gf2_table_experiment import C21Config, build_oracles
from .schedule import balanced_orders


SCHEMA = "crse-c33-prepared-policy-async-shadow-experiment/v1"
DISABLED = "baseline_serving_shadow_disabled"
SYNCHRONOUS = "c32_synchronous_shadow"
ASYNC_FULL = "c33_async_full_deferred_ack"
ASYNC_QUARTER = "c33_async_quarter_deferred_ack"
METHODS = (DISABLED, SYNCHRONOUS, ASYNC_FULL, ASYNC_QUARTER)
QUERY_COUNT = 8
METHOD_SAMPLE_EVERY = {
    DISABLED: None,
    SYNCHRONOUS: 1,
    ASYNC_FULL: 1,
    ASYNC_QUARTER: 4,
}
BATCH_TIMING_FIELDS = (
    "boundary_initialize_ns",
    "served_baseline_ns",
    "envelope_copy_ns",
    "stage_ns",
    "query_wrapper_ns",
    "synchronous_candidate_ns",
    "synchronous_comparison_ns",
    "serving_wrapper_ns",
    "serving_total_ns",
    "post_response_ack_ns",
    "observation_drain_ns",
    "close_ns",
    "lifecycle_wrapper_ns",
    "lifecycle_total_ns",
)


@dataclass(frozen=True)
class C33Config:
    run_id: str
    seed: int = 20260901
    blocks: int = 16
    query_count: int = QUERY_COUNT
    queue_capacity: int = QUERY_COUNT
    max_partitions: int = 64
    materialize_budget: int = 4
    max_seconds: float = 600.0
    max_aggregate_async_full_serving_ratio: float = 1.10
    max_width_async_full_serving_ratio: float = 1.20
    max_async_full_enqueue_p95_ns: int = 500_000

    def validate(self) -> None:
        width_orders = balanced_orders(N_VARS)
        method_orders = balanced_orders(METHODS)
        if (
            type(self.run_id) is not str
            or not self.run_id
            or type(self.seed) is not int
            or type(self.blocks) is not int
            or not 8 <= self.blocks <= 32
            or self.blocks % len(width_orders)
            or self.blocks % len(method_orders)
            or self.query_count != QUERY_COUNT
            or self.queue_capacity != QUERY_COUNT
            or self.max_partitions != 64
            or self.materialize_budget != 4
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 180 <= self.max_seconds <= 1200
            or type(self.max_aggregate_async_full_serving_ratio) is not float
            or not 1.0 <= self.max_aggregate_async_full_serving_ratio <= 2.0
            or type(self.max_width_async_full_serving_ratio) is not float
            or not 1.0 <= self.max_width_async_full_serving_ratio <= 2.0
            or type(self.max_async_full_enqueue_p95_ns) is not int
            or not 10_000 <= self.max_async_full_enqueue_p95_ns <= 5_000_000
        ):
            raise ValueError("invalid C33 experiment bounds")

    def oracle_config(self) -> C21Config:
        return C21Config(
            run_id=self.run_id,
            rounds=3,
            max_partitions=self.max_partitions,
            materialize_budget=self.materialize_budget,
            memory_cases_per_width=1,
            max_seconds=self.max_seconds,
        )


def _write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(
                row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _median(values: Iterable[int | float]) -> float:
    materialized = list(values)
    if not materialized:
        raise ValueError("empty C33 median")
    return float(statistics.median(materialized))


def _percentile(values: Iterable[int | float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered or not 0.0 < fraction <= 1.0:
        raise ValueError("invalid C33 percentile")
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return float(ordered[index])


def build_schedule(config: C33Config) -> tuple[dict[str, Any], ...]:
    config.validate()
    width_orders = balanced_orders(N_VARS)
    method_orders = balanced_orders(METHODS)
    schedule = []
    for block in range(config.blocks):
        width_order = width_orders[(block + config.seed) % len(width_orders)]
        method_order = method_orders[(block + config.seed) % len(method_orders)]
        for width_position, n_vars in enumerate(width_order):
            group_id = f"b{block:02d}-n{n_vars}"
            for arm_position, method in enumerate(method_order):
                schedule.append({
                    "block": block,
                    "group_id": group_id,
                    "n_vars": n_vars,
                    "width_position": width_position,
                    "arm_position": arm_position,
                    "method": method,
                })
    return tuple(schedule)


def _zero_batch_timings() -> dict[str, int]:
    return {field: 0 for field in BATCH_TIMING_FIELDS}


def execute_shadow_batch(
    *,
    boundary_id: str,
    method: str,
    cases: list[dict[str, Any]],
    oracles: dict[str, Any],
    prepared_context,
    queue_capacity: int = QUERY_COUNT,
    max_partitions: int = 64,
    materialize_budget: int = 4,
) -> dict[str, Any]:
    if method not in METHODS or len(cases) != QUERY_COUNT:
        raise ValueError("invalid C33 shadow batch")
    total_started = time.perf_counter_ns()
    timings = _zero_batch_timings()
    started = time.perf_counter_ns()
    if method == SYNCHRONOUS:
        boundary = PreparedPolicyShadowBoundary(
            boundary_id,
            prepared_context,
            required_prepared_context_sha256=prepared_context.context_sha256,
            shadow_enabled=True,
            max_queries=len(cases),
            max_partitions=max_partitions,
            materialize_budget=materialize_budget,
        )
    else:
        boundary = PreparedPolicyAsyncShadowBoundary(
            boundary_id,
            prepared_context,
            required_prepared_context_sha256=prepared_context.context_sha256,
            shadow_enabled=method in {ASYNC_FULL, ASYNC_QUARTER},
            sample_every=METHOD_SAMPLE_EVERY[method] or 1,
            queue_capacity=queue_capacity,
            max_queries=len(cases),
            max_partitions=max_partitions,
            materialize_budget=materialize_budget,
        )
    timings["boundary_initialize_ns"] = max(1, time.perf_counter_ns() - started)

    query_records = []
    serving_started = total_started
    for case in cases:
        required = oracles[case["case_id"]]["best_artifact"]
        document = boundary.execute(case).to_dict()
        if method == SYNCHRONOUS:
            verify_prepared_policy_shadow_result(document, case, required_best=required)
            timings["served_baseline_ns"] += document["timings_ns"]["baseline_ns"]
            timings["synchronous_candidate_ns"] += document["timings_ns"][
                "shadow_candidate_ns"]
            timings["synchronous_comparison_ns"] += document["timings_ns"][
                "comparison_ns"]
            timings["query_wrapper_ns"] += document["timings_ns"]["wrapper_ns"]
        else:
            verify_async_shadow_serve_result(document, case, required_best=required)
            timings["served_baseline_ns"] += document["timings_ns"]["baseline_ns"]
            timings["envelope_copy_ns"] += document["timings_ns"]["envelope_copy_ns"]
            timings["stage_ns"] += document["timings_ns"]["stage_ns"]
            timings["query_wrapper_ns"] += document["timings_ns"]["wrapper_ns"]
        query_records.append(document)
    serving_elapsed = max(1, time.perf_counter_ns() - serving_started)
    serving_charged = sum(timings[field] for field in (
        "boundary_initialize_ns", "served_baseline_ns", "envelope_copy_ns",
        "stage_ns", "query_wrapper_ns", "synchronous_candidate_ns",
        "synchronous_comparison_ns",
    ))
    timings["serving_wrapper_ns"] = max(0, serving_elapsed - serving_charged)
    timings["serving_total_ns"] = serving_charged + timings["serving_wrapper_ns"]

    if method == SYNCHRONOUS:
        pre_ack_observations = len(cases)
        observations = []
    else:
        pre_ack_observations = len(boundary.observations())
        started = time.perf_counter_ns()
        boundary.acknowledge_all_delivered()
        timings["post_response_ack_ns"] = max(1, time.perf_counter_ns() - started)
        started = time.perf_counter_ns()
        if not boundary.drain(timeout_seconds=30.0):
            raise TimeoutError("C33 measurement observation drain timed out")
        timings["observation_drain_ns"] = max(1, time.perf_counter_ns() - started)
        observations = list(boundary.observations())

    before_close = boundary.snapshot()
    started = time.perf_counter_ns()
    closed = boundary.close(timeout_seconds=30.0) if method != SYNCHRONOUS else boundary.close()
    timings["close_ns"] = max(1, time.perf_counter_ns() - started)
    lifecycle_elapsed = max(1, time.perf_counter_ns() - total_started)
    lifecycle_charged = (
        timings["serving_total_ns"]
        + timings["post_response_ack_ns"]
        + timings["observation_drain_ns"]
        + timings["close_ns"]
    )
    timings["lifecycle_wrapper_ns"] = max(0, lifecycle_elapsed - lifecycle_charged)
    timings["lifecycle_total_ns"] = lifecycle_charged + timings["lifecycle_wrapper_ns"]

    expected_observations = {
        DISABLED: 0,
        SYNCHRONOUS: QUERY_COUNT,
        ASYNC_FULL: QUERY_COUNT,
        ASYNC_QUARTER: QUERY_COUNT // 4,
    }[method]
    if method == SYNCHRONOUS:
        candidate_observations = sum(
            row["candidate_status"] == "observed" for row in query_records)
        divergences = sum(row["shadow_divergence_detected"] for row in query_records)
        failures = sum(row["shadow_failure_contained"] for row in query_records)
        queue_drops = 0
        served_candidate_results = closed["served_candidate_results"]
    else:
        candidate_observations = sum(
            row["candidate_status"] == "observed" for row in observations)
        divergences = sum(row["shadow_divergence_detected"] for row in observations)
        failures = sum(row["shadow_failure_contained"] for row in observations)
        queue_drops = closed["queue_full_drops"]
        served_candidate_results = closed["served_candidate_results"]
    if (
        closed.get("closed") is not True
        or candidate_observations != expected_observations
        or divergences != 0
        or failures != 0
        or queue_drops != 0
        or served_candidate_results != 0
        or closed.get("production_writes") != 0
        or closed.get("shadow_promotions") != 0
        or closed.get("production_promotions") != 0
    ):
        raise RuntimeError("C33 measurement boundary invariant failed")
    return {
        "status": "ok",
        "method": method,
        "query_count": len(cases),
        "timings_ns": timings,
        "query_records": query_records,
        "observations": observations,
        "pre_ack_candidate_observations": pre_ack_observations,
        "candidate_observations": candidate_observations,
        "candidate_divergences": divergences,
        "candidate_failures_contained": failures,
        "queue_full_drops": queue_drops,
        "served_candidate_results": served_candidate_results,
        "boundary_snapshot": before_close,
        "closed_snapshot": closed,
        "served_baseline_exact": all(
            row["baseline_exact_check_passed"] for row in query_records),
        "production_writes": 0,
        "shadow_promotions": 0,
        "production_promotions": 0,
    }


def _enqueue_costs(rows: list[dict[str, Any]], method: str) -> list[int]:
    return [
        record["timings_ns"]["envelope_copy_ns"]
        + record["timings_ns"]["stage_ns"]
        for row in rows if row["method"] == method
        for record in row["query_records"] if record["sample_eligible"]
    ]


def summarize(
    rows: list[dict[str, Any]], controls: dict[str, Any], config: C33Config,
) -> dict[str, Any]:
    expected_timing = set(BATCH_TIMING_FIELDS)
    expected_per_batch = {
        DISABLED: 0,
        SYNCHRONOUS: QUERY_COUNT,
        ASYNC_FULL: QUERY_COUNT,
        ASYNC_QUARTER: QUERY_COUNT // 4,
    }
    for row in rows:
        timings = row.get("timings_ns")
        method = row.get("method")
        if (
            method not in METHODS
            or row.get("query_count") != QUERY_COUNT
            or row.get("served_baseline_exact") is not True
            or row.get("candidate_observations") != expected_per_batch.get(method)
            or row.get("candidate_divergences") != 0
            or row.get("candidate_failures_contained") != 0
            or row.get("queue_full_drops") != 0
            or row.get("served_candidate_results") != 0
            or row.get("production_writes") != 0
            or row.get("shadow_promotions") != 0
            or row.get("production_promotions") != 0
            or type(timings) is not dict
            or set(timings) != expected_timing
            or any(type(value) is not int or value < 0 for value in timings.values())
            or timings["serving_total_ns"] != sum(timings[field] for field in (
                "boundary_initialize_ns", "served_baseline_ns", "envelope_copy_ns",
                "stage_ns", "query_wrapper_ns", "synchronous_candidate_ns",
                "synchronous_comparison_ns", "serving_wrapper_ns"))
            or timings["lifecycle_total_ns"] != sum(timings[field] for field in (
                "serving_total_ns", "post_response_ack_ns", "observation_drain_ns",
                "close_ns", "lifecycle_wrapper_ns"))
            or len(row.get("query_records", [])) != QUERY_COUNT
        ):
            raise ValueError("invalid C33 measurement row")
        if method in {ASYNC_FULL, ASYNC_QUARTER} and (
                row.get("pre_ack_candidate_observations") != 0):
            raise ValueError("C33 candidate started before delivery acknowledgement")

    by_width = {}
    per_cell = len(rows) // (len(N_VARS) * len(METHODS))
    for n_vars in N_VARS:
        selected = [row for row in rows if row["n_vars"] == n_vars]
        by_method = {
            method: [row for row in selected if row["method"] == method]
            for method in METHODS
        }
        if any(len(values) != per_cell for values in by_method.values()):
            raise ValueError("C33 width/method balance mismatch")
        medians = {
            method: {
                field: _median(row["timings_ns"][field] for row in values)
                for field in BATCH_TIMING_FIELDS
            }
            for method, values in by_method.items()
        }
        disabled_total = medians[DISABLED]["serving_total_ns"]
        by_width[str(n_vars)] = {
            "groups": per_cell,
            "methods": medians,
            "synchronous_serving_ratio_over_disabled": (
                medians[SYNCHRONOUS]["serving_total_ns"] / disabled_total),
            "async_full_serving_ratio_over_disabled": (
                medians[ASYNC_FULL]["serving_total_ns"] / disabled_total),
            "async_quarter_serving_ratio_over_disabled": (
                medians[ASYNC_QUARTER]["serving_total_ns"] / disabled_total),
            "async_full_baseline_ratio_over_disabled": (
                medians[ASYNC_FULL]["served_baseline_ns"]
                / medians[DISABLED]["served_baseline_ns"]),
        }

    def aggregate(method: str, field: str) -> float:
        return sum(row["methods"][method][field] for row in by_width.values())

    disabled_serving = aggregate(DISABLED, "serving_total_ns")
    ratios = {
        "synchronous_serving_ratio_over_disabled": (
            aggregate(SYNCHRONOUS, "serving_total_ns") / disabled_serving),
        "async_full_serving_ratio_over_disabled": (
            aggregate(ASYNC_FULL, "serving_total_ns") / disabled_serving),
        "async_quarter_serving_ratio_over_disabled": (
            aggregate(ASYNC_QUARTER, "serving_total_ns") / disabled_serving),
        "async_full_baseline_ratio_over_disabled": (
            aggregate(ASYNC_FULL, "served_baseline_ns")
            / aggregate(DISABLED, "served_baseline_ns")),
    }
    full_costs = _enqueue_costs(rows, ASYNC_FULL)
    quarter_costs = _enqueue_costs(rows, ASYNC_QUARTER)
    timing_gate = (
        ratios["async_full_serving_ratio_over_disabled"]
        <= config.max_aggregate_async_full_serving_ratio
        and max(row["async_full_serving_ratio_over_disabled"] for row in by_width.values())
        <= config.max_width_async_full_serving_ratio
        and _percentile(full_costs, 0.95) <= config.max_async_full_enqueue_p95_ns
        and ratios["async_full_serving_ratio_over_disabled"]
        < ratios["synchronous_serving_ratio_over_disabled"]
    )
    exact_gate = (
        controls.get("all_passed") is True
        and all(row["served_baseline_exact"] for row in rows)
        and sum(row["candidate_divergences"] for row in rows) == 0
        and sum(row["queue_full_drops"] for row in rows) == 0
        and sum(row["served_candidate_results"] for row in rows) == 0
        and sum(row["production_writes"] for row in rows) == 0
        and all(
            row["pre_ack_candidate_observations"] == 0
            for row in rows if row["method"] in {ASYNC_FULL, ASYNC_QUARTER})
    )
    observations_by_method = {
        method: sum(row["candidate_observations"] for row in rows
                    if row["method"] == method)
        for method in METHODS
    }
    requests_by_method = {
        method: sum(row["query_count"] for row in rows if row["method"] == method)
        for method in METHODS
    }
    return {
        "measurement_batches": len(rows),
        "counterbalanced_groups": len(rows) // len(METHODS),
        "served_exact_queries": sum(row["query_count"] for row in rows),
        "candidate_observations": sum(observations_by_method.values()),
        "candidate_observations_by_method": observations_by_method,
        "observation_coverage_by_method": {
            method: observations_by_method[method] / requests_by_method[method]
            for method in METHODS
        },
        "semantic_or_artifact_mismatches": sum(
            row["candidate_divergences"] for row in rows),
        "queue_full_drops_in_measurement": sum(row["queue_full_drops"] for row in rows),
        "candidate_results_served": sum(
            row["served_candidate_results"] for row in rows),
        "pre_ack_candidate_observations": sum(
            row["pre_ack_candidate_observations"] for row in rows
            if row["method"] in {ASYNC_FULL, ASYNC_QUARTER}),
        "functional_controls_passed": controls.get("all_passed") is True,
        "exact_containment_gate": exact_gate,
        "timing_gate": timing_gate,
        "c33_local_gate": exact_gate and timing_gate,
        "timing_thresholds": {
            "max_aggregate_async_full_serving_ratio": (
                config.max_aggregate_async_full_serving_ratio),
            "max_width_async_full_serving_ratio": (
                config.max_width_async_full_serving_ratio),
            "max_async_full_enqueue_p95_ns": config.max_async_full_enqueue_p95_ns,
        },
        "aggregate_ratios": ratios,
        "async_full_enqueue_ns": {
            "count": len(full_costs),
            "median": _median(full_costs),
            "p95": _percentile(full_costs, 0.95),
            "maximum": float(max(full_costs)),
        },
        "async_quarter_enqueue_ns": {
            "count": len(quarter_costs),
            "median": _median(quarter_costs),
            "p95": _percentile(quarter_costs, 0.95),
            "maximum": float(max(quarter_costs)),
        },
        "by_width": by_width,
        "arm_order_balanced": all(
            sum(row["method"] == method and row["arm_position"] == position
                for row in rows) == len(rows) // 16
            for method in METHODS for position in range(4)),
        "width_position_balanced": all(
            sum(row["n_vars"] == n_vars and row["width_position"] == position
                for row in rows) == len(rows) // 16
            for n_vars in N_VARS for position in range(4)),
        "timing_is_observational_not_a_promotion_gate": True,
    }


def _without_timings(value: Any) -> Any:
    if type(value) is dict:
        return {
            key: _without_timings(item)
            for key, item in value.items()
            if key not in {"timings_ns", "queue_wait_ns"}
        }
    if type(value) is list:
        return [_without_timings(item) for item in value]
    return value


def control_signature(controls: dict[str, Any]) -> dict[str, Any]:
    return _without_timings(controls)


def run_controls(
    *,
    output: Path,
    cases: list[dict[str, Any]],
    oracles: dict[str, Any],
    c27_policy_path: Path,
    c22_policy_path: Path,
) -> dict[str, Any]:
    prepared = prepare_support_policy_context(c27_policy_path, c22_policy_path)
    tiny = next(case for case in cases if case["n_vars"] == 3)
    tiny_best = oracles[tiny["case_id"]]["best_artifact"]
    divergent_case = next(
        case for case in cases if case["case_id"].endswith("03b09ef790ba581d"))
    divergent_best = oracles[divergent_case["case_id"]]["best_artifact"]

    delivery = PreparedPolicyAsyncShadowBoundary(
        "c33-control-delivery", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=True, queue_capacity=1, max_queries=1)
    delivery_result = delivery.execute(tiny).to_dict()
    before_ack = delivery.snapshot()
    delivery.acknowledge_all_delivered()
    if not delivery.drain(timeout_seconds=5.0):
        raise TimeoutError("C33 delivery control drain")
    delivery_observation = delivery.observations()[0]
    delivery_closed = delivery.close()

    mutable = copy.deepcopy(tiny)
    mutation = PreparedPolicyAsyncShadowBoundary(
        "c33-control-mutation", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=True, queue_capacity=1, max_queries=1)
    mutation_result = mutation.execute(mutable).to_dict()
    mutable["truth_bits_hex"] = "0x0"
    mutable["expression_v2"]["root"] = 0
    mutation.acknowledge_all_delivered()
    if not mutation.drain(timeout_seconds=5.0):
        raise TimeoutError("C33 mutation control drain")
    mutation_observation = mutation.observations()[0]
    mutation_closed = mutation.close()

    saturation = PreparedPolicyAsyncShadowBoundary(
        "c33-control-saturation", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=True, queue_capacity=1, max_queries=2)
    saturated_first = saturation.execute(tiny).to_dict()
    saturated_second = saturation.execute(cases[1]).to_dict()
    saturation_closed = saturation.close()

    sampling = PreparedPolicyAsyncShadowBoundary(
        "c33-control-sampling", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=True, sample_every=2, queue_capacity=2, max_queries=4)
    sampling_results = [sampling.execute(case).to_dict() for case in cases[:4]]
    sampling_closed = sampling.close()

    def fail(_session, _case):
        raise RuntimeError("simulated asynchronous shadow failure")

    exception = PreparedPolicyAsyncShadowBoundary(
        "c33-control-exception", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=True, queue_capacity=1, max_queries=1,
        candidate_executor=fail)
    exception_result = exception.execute(tiny).to_dict()
    exception_closed = exception.close()
    exception_observation = exception.observations()[0]

    def refuse(session, case):
        session.close()
        return session.execute(case)

    refusal = PreparedPolicyAsyncShadowBoundary(
        "c33-control-refusal", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=True, queue_capacity=1, max_queries=1,
        candidate_executor=refuse)
    refusal_result = refusal.execute(tiny).to_dict()
    refusal_closed = refusal.close()
    refusal_observation = refusal.observations()[0]

    truth = int(divergent_case["truth_bits_hex"], 16)
    exhaustive = analyze_exact_gf2(truth, divergent_case["n_vars"], max_partitions=64)
    alternate = next(
        artifact.to_dict() for artifact in exhaustive.candidates
        if artifact.to_dict() != divergent_best)

    def diverge(session, case):
        result = session.execute(case)
        return replace(
            result, best_artifact=alternate,
            artifact_sha256=canonical_sha256(alternate))

    divergence = PreparedPolicyAsyncShadowBoundary(
        "c33-control-divergence", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=True, queue_capacity=1, max_queries=1,
        candidate_executor=diverge)
    divergence_result = divergence.execute(divergent_case).to_dict()
    divergence_closed = divergence.close()
    divergence_observation = divergence.observations()[0]

    try:
        PreparedPolicyAsyncShadowBoundary(
            "c33-control-wrong-bind", prepared,
            required_prepared_context_sha256="0" * 64)
    except ValueError:
        wrong_bind = "refused"
    else:
        wrong_bind = "accepted"

    c27_copy = output / "control_changed_source_c27.json"
    c22_copy = output / "control_changed_source_c22.json"
    c27_copy.write_bytes(c27_policy_path.read_bytes())
    c22_copy.write_bytes(c22_policy_path.read_bytes())
    changed = prepare_support_policy_context(c27_copy, c22_copy)
    source_change = PreparedPolicyAsyncShadowBoundary(
        "c33-control-source-change", changed,
        required_prepared_context_sha256=changed.context_sha256,
        shadow_enabled=True, queue_capacity=1, max_queries=1)
    source_change_result = source_change.execute(tiny).to_dict()
    with c27_copy.open("ab") as handle:
        handle.write(b" ")
    source_change.acknowledge_all_delivered()
    if not source_change.drain(timeout_seconds=5.0):
        raise TimeoutError("C33 changed-source control drain")
    source_observation = source_change.observations()[0]
    try:
        source_change.close()
    except ValueError:
        changed_close = "refused"
    else:
        changed_close = "accepted"
    source_closed = source_change.snapshot()

    shutdown = PreparedPolicyAsyncShadowBoundary(
        "c33-control-shutdown", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=True, queue_capacity=1, max_queries=1)
    shutdown_result = shutdown.execute(tiny).to_dict()
    shutdown_closed = shutdown.close()
    try:
        shutdown.execute(tiny)
    except ValueError:
        late_request = "refused"
    else:
        late_request = "accepted"

    controls = {
        "schema": "crse-c33-async-shadow-controls/v1",
        "delivery_ack_boundary": {
            "result": delivery_result,
            "observations_before_ack": before_ack["observations_recorded"],
            "observation": delivery_observation,
            "closed": delivery_closed,
        },
        "post_return_mutation": {
            "result": mutation_result,
            "observation": mutation_observation,
            "closed": mutation_closed,
        },
        "queue_saturation": {
            "first": saturated_first,
            "second": saturated_second,
            "closed": saturation_closed,
        },
        "deterministic_sampling": {
            "results": sampling_results,
            "closed": sampling_closed,
        },
        "candidate_exception": {
            "result": exception_result,
            "observation": exception_observation,
            "closed": exception_closed,
        },
        "candidate_refusal": {
            "result": refusal_result,
            "observation": refusal_observation,
            "closed": refusal_closed,
        },
        "candidate_divergence": {
            "result": divergence_result,
            "observation": divergence_observation,
            "closed": divergence_closed,
        },
        "wrong_context_binding": wrong_bind,
        "changed_policy_source": {
            "result": source_change_result,
            "observation": source_observation,
            "close": changed_close,
            "closed": source_closed,
        },
        "bounded_shutdown": {
            "result": shutdown_result,
            "closed": shutdown_closed,
            "late_request": late_request,
        },
    }
    controls["all_passed"] = (
        controls["delivery_ack_boundary"]["observations_before_ack"] == 0
        and delivery_observation["candidate_best_identity_match"] is True
        and mutation_observation["candidate_best_identity_match"] is True
        and saturated_first["shadow_disposition"] == "staged_pending_delivery_ack"
        and saturated_second["shadow_disposition"] == "queue_full"
        and saturation_closed["queue_full_drops"] == 1
        and [row["sample_eligible"] for row in sampling_results]
        == [True, False, True, False]
        and sampling_closed["candidate_observations"] == 2
        and exception_observation["candidate_status"] == "error"
        and exception_observation["shadow_failure_contained"] is True
        and refusal_observation["candidate_status"] == "refused"
        and refusal_observation["shadow_failure_contained"] is True
        and divergence_observation["candidate_best_identity_match"] is False
        and divergence_observation["shadow_divergence_detected"] is True
        and divergence_result["served_best_artifact"] == divergent_best
        and wrong_bind == "refused"
        and source_observation["candidate_status"] == "error"
        and changed_close == "refused"
        and source_closed["closed"] is True
        and shutdown_closed["candidate_observations"] == 1
        and late_request == "refused"
        and all(
            snapshot["served_candidate_results"] == 0
            and snapshot["production_writes"] == 0
            and snapshot["shadow_promotions"] == 0
            and snapshot["production_promotions"] == 0
            for snapshot in (
                delivery_closed, mutation_closed, saturation_closed, sampling_closed,
                exception_closed, refusal_closed, divergence_closed, source_closed,
                shutdown_closed,
            )
        )
    )
    return controls


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    ratios = summary["aggregate_ratios"]
    return f"""# C33 bounded asynchronous prepared-policy shadowing

Status: **{result['status']}**
Local C33 gate: **{'pass' if summary['c33_local_gate'] else 'fail'}**

All {summary['served_exact_queries']:,} requests served the exact screened baseline.
Candidate execution remained impossible until an explicit post-delivery acknowledgement.
The run observed {summary['candidate_observations']:,} candidates with
{summary['semantic_or_artifact_mismatches']} divergences and served zero candidate results.

Synchronous C32 serving ratio: **{ratios['synchronous_serving_ratio_over_disabled']:.3f}x**.
Full asynchronous serving ratio: **{ratios['async_full_serving_ratio_over_disabled']:.3f}x**.
Quarter-sampled asynchronous serving ratio: **{ratios['async_quarter_serving_ratio_over_disabled']:.3f}x**.
Full-shadow enqueue p95: **{summary['async_full_enqueue_ns']['p95'] / 1000:.1f} us**.

The queue-full control dropped observational work without blocking or changing the exact
response. Mutation, exception, refusal, divergence, source-change, binding, sampling, and
shutdown controls all remained fail closed. Timing is local engineering evidence only;
no production write, shadow promotion, or production promotion was authorized.
"""


def run_experiment(
    config: C33Config,
    *,
    output: Path,
    dataset_path: Path,
    dataset_verification_path: Path,
    c27_policy_path: Path,
    c22_policy_path: Path,
    c31_final_path: Path,
    c31_adjudication_path: Path,
    c32_summary_path: Path,
    root: Path,
) -> dict[str, Any]:
    config.validate()
    wall_started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset_verification = json.loads(
        dataset_verification_path.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    c27_policy = load_support_aware_policy(c27_policy_path)
    c22_policy = load_source_portfolio_policy(c22_policy_path)
    c31_final = json.loads(c31_final_path.read_text(encoding="utf-8"))
    c31_adjudication = json.loads(c31_adjudication_path.read_text(encoding="utf-8"))
    c32_summary = json.loads(c32_summary_path.read_text(encoding="utf-8"))
    if (
        len(dataset.get("cases", [])) != 48
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 48
        or dataset_verification.get("expression_truth_mismatches") != 0
        or dataset_verification.get("scalar_oracle_mismatches") != 0
        or dataset_verification.get("prior_truth_overlaps") != 0
        or c27_policy.get("training_use") is not False
        or c22_policy.get("training_use") is not False
        or c31_final.get("status") != "pass"
        or c31_final.get("scientific_replication_complete") is not True
        or c31_adjudication.get("replication_admissible") is not True
        or c32_summary.get("status")
        != "verified_local_shadow_boundary_no_promotion"
        or c32_summary.get("served_exact_queries") != 1024
        or c32_summary.get("candidate_results_served") != 0
        or c32_summary.get("shadow_promotion") is not False
        or c32_summary.get("production_promotion") is not False
    ):
        raise ValueError("C33 frozen input contract changed")

    cases = dataset["cases"]
    functional, oracles = build_oracles(cases, config.oracle_config())
    if not functional["all_exact"]:
        raise RuntimeError("C33 exhaustive oracle replay failed")
    controls = run_controls(
        output=output,
        cases=cases,
        oracles=oracles,
        c27_policy_path=c27_policy_path,
        c22_policy_path=c22_policy_path,
    )
    if not controls["all_passed"]:
        raise RuntimeError("C33 asynchronous controls failed")
    _write(output / "functional_controls.json", controls)

    prepared = prepare_support_policy_context(c27_policy_path, c22_policy_path)
    verify_prepared_policy_sources(prepared)
    _write(output / "prepared_context.json", prepared.identity())
    cases_by_width = {
        n_vars: sorted(
            (case for case in cases if case["n_vars"] == n_vars),
            key=lambda case: (case["truth_sha256"], case["case_id"]),
        )
        for n_vars in N_VARS
    }
    rows = []
    for cell in build_schedule(config):
        if time.perf_counter() - wall_started > config.max_seconds:
            raise TimeoutError("C33 experiment exceeded wall bound")
        sequence = case_sequence(
            cases_by_width, cell["n_vars"], config.query_count, cell["block"])
        execution = execute_shadow_batch(
            boundary_id=f"c33-{cell['group_id']}-p{cell['arm_position']}",
            method=cell["method"],
            cases=sequence,
            oracles=oracles,
            prepared_context=prepared,
            queue_capacity=config.queue_capacity,
            max_partitions=config.max_partitions,
            materialize_budget=config.materialize_budget,
        )
        rows.append({**cell, **execution})
    verify_prepared_policy_sources(prepared)
    _write_jsonl(output / "measurements.jsonl", rows)
    summary = summarize(rows, controls, config)
    spec = {
        "schema": SCHEMA,
        "config": asdict(config),
        "dataset_path": _rel(dataset_path, root),
        "dataset_sha256": _sha256(dataset_path),
        "dataset_verification_path": _rel(dataset_verification_path, root),
        "dataset_verification_sha256": _sha256(dataset_verification_path),
        "c27_policy_path": _rel(c27_policy_path, root),
        "c27_policy_file_sha256": _sha256(c27_policy_path),
        "c22_policy_path": _rel(c22_policy_path, root),
        "c22_policy_file_sha256": _sha256(c22_policy_path),
        "c31_final_path": _rel(c31_final_path, root),
        "c31_final_sha256": _sha256(c31_final_path),
        "c31_adjudication_path": _rel(c31_adjudication_path, root),
        "c31_adjudication_sha256": _sha256(c31_adjudication_path),
        "c32_summary_path": _rel(c32_summary_path, root),
        "c32_summary_sha256": _sha256(c32_summary_path),
        "methods": list(METHODS),
        "method_sample_every": METHOD_SAMPLE_EVERY,
        "served_method": "exact_screened_baseline",
        "candidate_method": "support_aware_c30_prepared",
        "delivery_ack_required_before_candidate": True,
        "candidate_observed_only": True,
        "prepared_context_sha256": prepared.context_sha256,
        "policy_refit": False,
        "training": False,
        "production_write": False,
        "shadow_promotion": False,
        "production_promotion": False,
    }
    _write(output / "run_spec.json", spec)
    result = {
        "schema": SCHEMA,
        "status": "complete" if summary["exact_containment_gate"] else "failed",
        "run_name": output.name,
        "wall_seconds": time.perf_counter() - wall_started,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "dd_version": importlib.metadata.version("dd"),
            "thread_environment": {name: os.environ.get(name) for name in
                                   ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS",
                                    "MKL_NUM_THREADS")},
        },
        "dataset_cases": len(cases),
        "summary": summary,
        "functional_controls_passed": controls["all_passed"],
        "semantic_or_artifact_mismatches": summary[
            "semantic_or_artifact_mismatches"],
        "policy_refit": False,
        "training": False,
        "development_shadow_evidence": True,
        "production_write": False,
        "shadow_promotion": False,
        "production_promotion": False,
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(
        render_report(result), encoding="utf-8", newline="\n")

    sources = (
        "cmbench/comparative/gf2_async_shadow_experiment.py",
        "cmbench/recognition/gf2_async_shadow_boundary.py",
        "cmbench/recognition/gf2_prepared_shadow_boundary.py",
        "cmbench/recognition/gf2_prepared_support_context.py",
        "cmbench/recognition/gf2_support_aware_session.py",
        "scripts/cm_comparative_c33_async_shadow.py",
        "scripts/crse_gf2_async_shadow_verify.py",
    )
    artifacts = (
        "control_changed_source_c22.json", "control_changed_source_c27.json",
        "functional_controls.json", "measurements.jsonl", "prepared_context.json",
        "report.md", "results.json", "run_spec.json",
    )
    manifest = {
        "schema": "crse-c33-async-shadow-run-manifest/v1",
        "sources": {name: _sha256(root / name) for name in sources},
        "inputs": {
            "dataset_sha256": _sha256(dataset_path),
            "dataset_verification_sha256": _sha256(dataset_verification_path),
            "c27_policy_file_sha256": _sha256(c27_policy_path),
            "c22_policy_file_sha256": _sha256(c22_policy_path),
            "c31_final_sha256": _sha256(c31_final_path),
            "c31_adjudication_sha256": _sha256(c31_adjudication_path),
            "c32_summary_sha256": _sha256(c32_summary_path),
        },
        "artifacts": {name: _sha256(output / name) for name in artifacts},
        "policy_refit": False,
        "training": False,
        "production_write": False,
        "shadow_promotion": False,
        "production_promotion": False,
    }
    _write(output / "manifest.json", manifest)
    return result
