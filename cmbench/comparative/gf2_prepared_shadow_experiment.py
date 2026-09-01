"""C32 production-shaped, baseline-serving shadow-boundary experiment."""
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


SCHEMA = "crse-c32-prepared-policy-shadow-experiment/v1"
DISABLED = "baseline_serving_shadow_disabled"
ENABLED = "baseline_serving_shadow_enabled"
METHODS = (DISABLED, ENABLED)
QUERY_COUNT = 8
BATCH_TIMING_FIELDS = (
    "boundary_initialize_ns",
    "served_baseline_ns",
    "shadow_candidate_ns",
    "comparison_ns",
    "query_wrapper_ns",
    "close_ns",
    "batch_wrapper_ns",
)


@dataclass(frozen=True)
class C32Config:
    run_id: str
    seed: int = 20260901
    blocks: int = 16
    query_count: int = QUERY_COUNT
    max_partitions: int = 64
    materialize_budget: int = 4
    max_seconds: float = 600.0

    def validate(self) -> None:
        if (
            type(self.run_id) is not str
            or not self.run_id
            or type(self.seed) is not int
            or type(self.blocks) is not int
            or not 8 <= self.blocks <= 32
            or self.blocks % len(balanced_orders(N_VARS))
            or self.query_count != QUERY_COUNT
            or self.max_partitions != 64
            or self.materialize_budget != 4
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 180 <= self.max_seconds <= 1200
        ):
            raise ValueError("invalid C32 experiment bounds")

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
        raise ValueError("empty C32 median")
    return float(statistics.median(materialized))


def build_schedule(config: C32Config) -> tuple[dict[str, Any], ...]:
    config.validate()
    width_orders = balanced_orders(N_VARS)
    method_orders = balanced_orders(METHODS)
    schedule = []
    for block in range(config.blocks):
        width_order = width_orders[(block + config.seed) % len(width_orders)]
        method_order = method_orders[(block + config.seed) % len(method_orders)]
        for width_position, n_vars in enumerate(width_order):
            pair_id = f"b{block:02d}-n{n_vars}"
            for arm_position, method in enumerate(method_order):
                schedule.append({
                    "block": block,
                    "pair_id": pair_id,
                    "n_vars": n_vars,
                    "width_position": width_position,
                    "arm_position": arm_position,
                    "method": method,
                })
    return tuple(schedule)


def _compact(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_index": document["request_index"],
        "case_id": document["case_id"],
        "n_vars": document["n_vars"],
        "status": document["status"],
        "shadow_enabled": document["shadow_enabled"],
        "served_output_source": document["served_output_source"],
        "served_selected_arm": document["served_selected_arm"],
        "served_artifact_sha256": document["served_artifact_sha256"],
        "baseline_context_sha256": document["baseline_context_sha256"],
        "baseline_exact_check_passed": document["baseline_exact_check_passed"],
        "candidate_status": document["candidate_status"],
        "candidate_selected_arm": document["candidate_selected_arm"],
        "candidate_artifact_sha256": document["candidate_artifact_sha256"],
        "candidate_context_sha256": document["candidate_context_sha256"],
        "candidate_best_identity_match": document["candidate_best_identity_match"],
        "candidate_error_type": document["candidate_error_type"],
        "candidate_refusal_reason": document["candidate_refusal_reason"],
        "shadow_divergence_detected": document["shadow_divergence_detected"],
        "shadow_failure_contained": document["shadow_failure_contained"],
        "candidate_observed_only": document["candidate_observed_only"],
        "production_write": document["production_write"],
        "shadow_promotion": document["shadow_promotion"],
        "production_promotion": document["production_promotion"],
        "timings_ns": document["timings_ns"],
    }


def execute_shadow_batch(
    *,
    boundary_id: str,
    method: str,
    cases: list[dict[str, Any]],
    oracles: dict[str, Any],
    prepared_context,
    max_partitions: int = 64,
    materialize_budget: int = 4,
) -> dict[str, Any]:
    if method not in METHODS or not cases:
        raise ValueError("invalid C32 shadow batch")
    total_started = time.perf_counter_ns()
    started = time.perf_counter_ns()
    boundary = PreparedPolicyShadowBoundary(
        boundary_id,
        prepared_context,
        required_prepared_context_sha256=prepared_context.context_sha256,
        shadow_enabled=method == ENABLED,
        max_queries=len(cases),
        max_partitions=max_partitions,
        materialize_budget=materialize_budget,
    )
    initialize_ns = max(1, time.perf_counter_ns() - started)
    records = []
    phase_totals = {
        "served_baseline_ns": 0,
        "shadow_candidate_ns": 0,
        "comparison_ns": 0,
        "query_wrapper_ns": 0,
    }
    for case in cases:
        required = oracles[case["case_id"]]["best_artifact"]
        document = boundary.execute(case).to_dict()
        verify_prepared_policy_shadow_result(document, case, required_best=required)
        records.append(_compact(document))
        phase_totals["served_baseline_ns"] += document["timings_ns"]["baseline_ns"]
        phase_totals["shadow_candidate_ns"] += document["timings_ns"][
            "shadow_candidate_ns"]
        phase_totals["comparison_ns"] += document["timings_ns"]["comparison_ns"]
        phase_totals["query_wrapper_ns"] += document["timings_ns"]["wrapper_ns"]
    before_close = boundary.snapshot()
    started = time.perf_counter_ns()
    closed = boundary.close()
    close_ns = max(1, time.perf_counter_ns() - started)
    if (
        closed.get("closed") is not True
        or closed.get("requests") != len(cases)
        or closed.get("served_candidate_results") != 0
        or closed.get("production_writes") != 0
        or closed.get("shadow_promotions") != 0
        or closed.get("production_promotions") != 0
    ):
        raise RuntimeError("C32 boundary close invariant failed")
    elapsed = max(1, time.perf_counter_ns() - total_started)
    timings = {
        "boundary_initialize_ns": initialize_ns,
        **phase_totals,
        "close_ns": close_ns,
        "batch_wrapper_ns": 0,
    }
    charged = sum(timings.values())
    timings["batch_wrapper_ns"] = max(0, elapsed - charged)
    timings["batch_total_ns"] = sum(timings.values())
    return {
        "status": "ok",
        "method": method,
        "query_count": len(cases),
        "timings_ns": timings,
        "amortized_synchronous_request_ns": timings["batch_total_ns"] / len(cases),
        "amortized_served_baseline_ns": timings["served_baseline_ns"] / len(cases),
        "query_records": records,
        "boundary_snapshot": before_close,
        "closed_snapshot": closed,
        "served_baseline_exact": all(row["baseline_exact_check_passed"] for row in records),
        "candidate_observations": sum(row["candidate_status"] == "observed" for row in records),
        "candidate_divergences": sum(row["shadow_divergence_detected"] for row in records),
        "candidate_failures_contained": sum(row["shadow_failure_contained"] for row in records),
        "production_writes": 0,
        "shadow_promotions": 0,
        "production_promotions": 0,
    }


def summarize(rows: list[dict[str, Any]], controls: dict[str, Any]) -> dict[str, Any]:
    expected_timing = {*BATCH_TIMING_FIELDS, "batch_total_ns"}
    for row in rows:
        timings = row.get("timings_ns")
        if (
            row.get("method") not in METHODS
            or row.get("query_count") != QUERY_COUNT
            or row.get("served_baseline_exact") is not True
            or row.get("candidate_divergences") != 0
            or row.get("candidate_failures_contained") != 0
            or row.get("production_writes") != 0
            or row.get("shadow_promotions") != 0
            or row.get("production_promotions") != 0
            or type(timings) is not dict
            or set(timings) != expected_timing
            or any(type(value) is not int or value < 0 for value in timings.values())
            or timings["batch_total_ns"] != sum(
                timings[field] for field in BATCH_TIMING_FIELDS)
            or len(row.get("query_records", [])) != QUERY_COUNT
        ):
            raise ValueError("invalid C32 measurement row")
        expected_observations = QUERY_COUNT if row["method"] == ENABLED else 0
        if row.get("candidate_observations") != expected_observations:
            raise ValueError("invalid C32 shadow observation count")

    by_width = {}
    for n_vars in N_VARS:
        selected = [row for row in rows if row["n_vars"] == n_vars]
        by_method = {
            method: [row for row in selected if row["method"] == method]
            for method in METHODS
        }
        if any(len(values) != len(rows) // (len(N_VARS) * len(METHODS))
               for values in by_method.values()):
            raise ValueError("C32 width/method balance mismatch")
        medians = {
            method: {
                field: _median(row["timings_ns"][field] for row in values)
                for field in (*BATCH_TIMING_FIELDS, "batch_total_ns")
            }
            for method, values in by_method.items()
        }
        by_width[str(n_vars)] = {
            "paired_blocks": len(by_method[DISABLED]),
            "methods": medians,
            "shadow_enabled_synchronous_overhead_ratio": (
                medians[ENABLED]["batch_total_ns"] / medians[DISABLED]["batch_total_ns"]),
            "served_baseline_latency_ratio_enabled_over_disabled": (
                medians[ENABLED]["served_baseline_ns"]
                / medians[DISABLED]["served_baseline_ns"]),
            "shadow_incremental_median_ns": (
                medians[ENABLED]["shadow_candidate_ns"]
                + medians[ENABLED]["comparison_ns"]),
        }
    disabled_total = sum(row["methods"][DISABLED]["batch_total_ns"] for row in by_width.values())
    enabled_total = sum(row["methods"][ENABLED]["batch_total_ns"] for row in by_width.values())
    disabled_baseline = sum(
        row["methods"][DISABLED]["served_baseline_ns"] for row in by_width.values())
    enabled_baseline = sum(
        row["methods"][ENABLED]["served_baseline_ns"] for row in by_width.values())
    shadow_observations = sum(row["candidate_observations"] for row in rows)
    shadow_gate = (
        controls.get("all_passed") is True
        and all(row["served_baseline_exact"] for row in rows)
        and sum(row["candidate_divergences"] for row in rows) == 0
        and sum(row["production_writes"] for row in rows) == 0
        and shadow_observations == len(rows) // 2 * QUERY_COUNT
    )
    return {
        "measurement_batches": len(rows),
        "paired_batches": len(rows) // 2,
        "served_exact_queries": sum(row["query_count"] for row in rows),
        "shadow_candidate_observations": shadow_observations,
        "semantic_or_artifact_mismatches": sum(
            row["candidate_divergences"] for row in rows),
        "contained_measurement_failures": sum(
            row["candidate_failures_contained"] for row in rows),
        "functional_controls_passed": controls.get("all_passed") is True,
        "served_baseline_exactness_gate": all(row["served_baseline_exact"] for row in rows),
        "zero_divergence_gate": all(row["candidate_divergences"] == 0 for row in rows),
        "zero_production_write_gate": all(row["production_writes"] == 0 for row in rows),
        "shadow_review_gate": shadow_gate,
        "aggregate_shadow_enabled_synchronous_overhead_ratio": enabled_total / disabled_total,
        "aggregate_served_baseline_latency_ratio_enabled_over_disabled": (
            enabled_baseline / disabled_baseline),
        "by_width": by_width,
        "arm_order_balanced": all(
            sum(row["method"] == method and row["arm_position"] == position for row in rows)
            == len(rows) // 4
            for method in METHODS for position in range(2)),
        "width_position_balanced": all(
            sum(row["n_vars"] == n_vars and row["width_position"] == position for row in rows)
            == len(rows) // 16
            for n_vars in N_VARS for position in range(4)),
        "timing_is_observational_not_a_promotion_gate": True,
    }


def _control_record(document: dict[str, Any]) -> dict[str, Any]:
    return {
        key: document[key] for key in (
            "status", "shadow_enabled", "served_output_source",
            "served_artifact_sha256", "baseline_exact_check_passed",
            "candidate_status", "candidate_best_identity_match",
            "candidate_error_type", "candidate_refusal_reason",
            "shadow_divergence_detected", "shadow_failure_contained",
            "candidate_observed_only", "production_write",
            "shadow_promotion", "production_promotion",
        )
    }


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
    divergent_case = next(
        case for case in cases if case["case_id"].endswith("03b09ef790ba581d"))

    disabled = PreparedPolicyShadowBoundary(
        "c32-control-disabled", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=False, max_queries=1)
    disabled_result = disabled.execute(tiny).to_dict()
    verify_prepared_policy_shadow_result(
        disabled_result, tiny, required_best=oracles[tiny["case_id"]]["best_artifact"])
    disabled_snapshot = disabled.close()

    def fail(_session, _case):
        raise RuntimeError("simulated shadow failure")

    exception = PreparedPolicyShadowBoundary(
        "c32-control-exception", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=True, max_queries=1, candidate_executor=fail)
    exception_result = exception.execute(tiny).to_dict()
    verify_prepared_policy_shadow_result(
        exception_result, tiny, required_best=oracles[tiny["case_id"]]["best_artifact"])
    exception_snapshot = exception.close()

    def refuse(session, case):
        session.close()
        return session.execute(case)

    refusal = PreparedPolicyShadowBoundary(
        "c32-control-refusal", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=True, max_queries=1, candidate_executor=refuse)
    refusal_result = refusal.execute(tiny).to_dict()
    verify_prepared_policy_shadow_result(
        refusal_result, tiny, required_best=oracles[tiny["case_id"]]["best_artifact"])
    refusal_snapshot = refusal.close()

    truth = int(divergent_case["truth_bits_hex"], 16)
    exhaustive = analyze_exact_gf2(truth, divergent_case["n_vars"], max_partitions=64)
    required = oracles[divergent_case["case_id"]]["best_artifact"]
    alternate = next(
        artifact.to_dict() for artifact in exhaustive.candidates
        if artifact.to_dict() != required)

    def diverge(session, case):
        result = session.execute(case)
        return replace(
            result, best_artifact=alternate,
            artifact_sha256=canonical_sha256(alternate))

    divergence = PreparedPolicyShadowBoundary(
        "c32-control-divergence", prepared,
        required_prepared_context_sha256=prepared.context_sha256,
        shadow_enabled=True, max_queries=1, candidate_executor=diverge)
    divergence_result = divergence.execute(divergent_case).to_dict()
    verify_prepared_policy_shadow_result(
        divergence_result, divergent_case, required_best=required)
    divergence_snapshot = divergence.close()

    try:
        PreparedPolicyShadowBoundary(
            "c32-control-wrong-bind", prepared,
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
    changed_boundary = PreparedPolicyShadowBoundary(
        "c32-control-source-change", changed,
        required_prepared_context_sha256=changed.context_sha256)
    with c27_copy.open("ab") as handle:
        handle.write(b" ")
    try:
        changed_boundary.audit_sources()
    except ValueError:
        changed_source = "refused"
    else:
        changed_source = "accepted"

    snapshots = (
        disabled_snapshot, exception_snapshot, refusal_snapshot, divergence_snapshot)
    controls = {
        "schema": "crse-c32-shadow-boundary-controls/v1",
        "disabled": _control_record(disabled_result),
        "candidate_exception": _control_record(exception_result),
        "candidate_refusal": _control_record(refusal_result),
        "candidate_divergence": _control_record(divergence_result),
        "wrong_context_binding": wrong_bind,
        "changed_policy_source": changed_source,
        "served_candidate_results": sum(row["served_candidate_results"] for row in snapshots),
        "production_writes": sum(row["production_writes"] for row in snapshots),
        "shadow_promotions": sum(row["shadow_promotions"] for row in snapshots),
        "production_promotions": sum(row["production_promotions"] for row in snapshots),
    }
    controls["all_passed"] = (
        disabled_result["candidate_status"] == "disabled"
        and exception_result["candidate_status"] == "error"
        and exception_result["shadow_failure_contained"] is True
        and refusal_result["candidate_status"] == "refused"
        and refusal_result["shadow_failure_contained"] is True
        and divergence_result["candidate_status"] == "observed"
        and divergence_result["candidate_best_identity_match"] is False
        and divergence_result["shadow_divergence_detected"] is True
        and divergence_result["shadow_failure_contained"] is True
        and divergence_result["served_artifact_sha256"]
        == oracles[divergent_case["case_id"]]["delivered_sha256"]
        and wrong_bind == "refused"
        and changed_source == "refused"
        and controls["served_candidate_results"] == 0
        and controls["production_writes"] == 0
        and controls["shadow_promotions"] == 0
        and controls["production_promotions"] == 0
    )
    return controls


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    return f"""# C32 prepared-policy shadow boundary

Status: **{result['status']}**
Shadow review gate: **{'pass' if summary['shadow_review_gate'] else 'fail'}**

The boundary served the exact screened baseline for all
{summary['served_exact_queries']:,} requests. The frozen C30 candidate was observed
{summary['shadow_candidate_observations']:,} times with
{summary['semantic_or_artifact_mismatches']} divergences. Candidate exceptions,
refusals, and exact-but-nonbest divergence controls were contained without serving a
candidate result.

Synchronous shadow total-time ratio: **{summary['aggregate_shadow_enabled_synchronous_overhead_ratio']:.3f}x**.
Enabled/disabled served-baseline latency ratio: **{summary['aggregate_served_baseline_latency_ratio_enabled_over_disabled']:.3f}x**.

Timing is observational. No production write, shadow promotion, or production promotion
was authorized or performed.
"""


def run_experiment(
    config: C32Config,
    *,
    output: Path,
    dataset_path: Path,
    dataset_verification_path: Path,
    c27_policy_path: Path,
    c22_policy_path: Path,
    c31_final_path: Path,
    c31_adjudication_path: Path,
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
        or c31_adjudication.get("eligible_for_separate_shadow_review") is not True
        or c31_adjudication.get("shadow_promotion") is not False
        or c31_adjudication.get("production_promotion") is not False
    ):
        raise ValueError("C32 frozen input contract changed")

    cases = dataset["cases"]
    functional, oracles = build_oracles(cases, config.oracle_config())
    if not functional["all_exact"]:
        raise RuntimeError("C32 exhaustive oracle replay failed")
    controls = run_controls(
        output=output,
        cases=cases,
        oracles=oracles,
        c27_policy_path=c27_policy_path,
        c22_policy_path=c22_policy_path,
    )
    if not controls["all_passed"]:
        raise RuntimeError("C32 shadow controls failed")
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
            raise TimeoutError("C32 experiment exceeded wall bound")
        sequence = case_sequence(
            cases_by_width, cell["n_vars"], config.query_count, cell["block"])
        execution = execute_shadow_batch(
            boundary_id=f"c32-{cell['pair_id']}-p{cell['arm_position']}",
            method=cell["method"],
            cases=sequence,
            oracles=oracles,
            prepared_context=prepared,
            max_partitions=config.max_partitions,
            materialize_budget=config.materialize_budget,
        )
        rows.append({**cell, **execution})
    verify_prepared_policy_sources(prepared)
    _write_jsonl(output / "measurements.jsonl", rows)
    summary = summarize(rows, controls)
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
        "methods": list(METHODS),
        "served_method": "exact_screened_baseline",
        "candidate_method": "support_aware_c30_prepared",
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
        "status": "complete" if summary["shadow_review_gate"] else "failed",
        "run_name": output.name,
        "wall_seconds": time.perf_counter() - wall_started,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "dd_version": importlib.metadata.version("dd"),
            "thread_environment": {name: os.environ.get(name) for name in
                                   ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        },
        "dataset_cases": len(cases),
        "summary": summary,
        "functional_controls_passed": controls["all_passed"],
        "semantic_or_artifact_mismatches": summary["semantic_or_artifact_mismatches"],
        "policy_refit": False,
        "training": False,
        "development_shadow_evidence": True,
        "production_write": False,
        "shadow_promotion": False,
        "production_promotion": False,
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")

    sources = (
        "cmbench/comparative/gf2_prepared_shadow_experiment.py",
        "cmbench/recognition/gf2_prepared_shadow_boundary.py",
        "cmbench/recognition/gf2_prepared_support_context.py",
        "cmbench/recognition/gf2_support_aware_session.py",
        "scripts/cm_comparative_c32_prepared_shadow.py",
        "scripts/crse_gf2_prepared_shadow_verify.py",
    )
    artifacts = (
        "control_changed_source_c22.json", "control_changed_source_c27.json",
        "functional_controls.json", "measurements.jsonl", "prepared_context.json",
        "report.md", "results.json", "run_spec.json",
    )
    manifest = {
        "schema": "crse-c32-shadow-run-manifest/v1",
        "sources": {name: _sha256(root / name) for name in sources},
        "inputs": {
            "dataset_sha256": _sha256(dataset_path),
            "dataset_verification_sha256": _sha256(dataset_verification_path),
            "c27_policy_file_sha256": _sha256(c27_policy_path),
            "c22_policy_file_sha256": _sha256(c22_policy_path),
            "c31_final_sha256": _sha256(c31_final_path),
            "c31_adjudication_sha256": _sha256(c31_adjudication_path),
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
