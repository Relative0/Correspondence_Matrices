"""C30 prepared-policy lifecycle experiment on the frozen C29 q8 schedule."""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
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

from cmbench.recognition.gf2_prepared_support_context import (
    PreparedSupportPolicyContext,
    prepare_support_policy_context,
    verify_prepared_policy_sources,
)
from cmbench.recognition.gf2_source_portfolio import (
    SOURCE_PACKED_SCREENED,
    load_source_portfolio_policy,
)
from cmbench.recognition.gf2_support_aware_policy import (
    TRUTH_SCREENED,
    load_support_aware_policy,
)
from cmbench.recognition.gf2_support_aware_session import SupportAwareGF2Session
from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE
from cmbench.recognition.gf2_work_policy import load_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy
from cmbench.recognition.yosys_c27_gf2_data import validate_dataset

from .gf2_decomposition import decomposition_contract
from .gf2_resident_session_experiment import (
    BATCH_TIMING_FIELDS,
    N_VARS,
    case_sequence,
    execute_batch as execute_c25_direct_batch,
)
from .gf2_support_aware_experiment import _support_aware_query
from .gf2_table_experiment import C21Config, build_oracles
from .schedule import balanced_orders


SCHEMA = "crse-c30-prepared-support-policy-experiment/v1"
BASELINE = "resident_direct_screened"
CANDIDATE = "support_aware_c30_prepared"
METHODS = (BASELINE, CANDIDATE)
QUERY_COUNT = 8
TIMING_FIELDS = (*BATCH_TIMING_FIELDS, "batch_total_ns")


@dataclass(frozen=True)
class C30Config:
    run_id: str
    seed: int = 20260901
    blocks: int = 16
    query_count: int = QUERY_COUNT
    max_partitions: int = 64
    materialize_budget: int = 4
    max_seconds: float = 600.0

    def validate(self) -> None:
        if (
            not self.run_id
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
            raise ValueError("invalid C30 experiment bounds")

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
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _median(values: Iterable[int | float]) -> float:
    materialized = list(values)
    if not materialized:
        raise ValueError("empty C30 median")
    return float(statistics.median(materialized))


def build_schedule(config: C30Config) -> tuple[dict[str, Any], ...]:
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


def execute_prepared_batch(
    *,
    session_id: str,
    cases: list[dict[str, Any]],
    oracles: dict[str, Any],
    prepared_context: PreparedSupportPolicyContext,
) -> dict[str, Any]:
    if not cases:
        raise ValueError("empty C30 prepared batch")
    total_started = time.perf_counter_ns()
    started = time.perf_counter_ns()
    session = SupportAwareGF2Session.from_prepared_context(
        session_id, prepared_context, max_queries=len(cases))
    setup_ns = max(1, time.perf_counter_ns() - started)
    setup_detail = session.snapshot()["setup_timings_ns"]
    queries_ns = 0
    query_records = []
    for case in cases:
        query = _support_aware_query(
            session, case, oracles[case["case_id"]]["best_artifact"])
        queries_ns += query["elapsed_ns"]
        query_records.append(query)
    started = time.perf_counter_ns()
    before_close = session.snapshot()
    closed = session.close()
    if not closed["closed"] or closed["successful_queries"] != len(cases):
        raise RuntimeError("C30 prepared session close invariant failed")
    close_ns = max(1, time.perf_counter_ns() - started)
    elapsed = max(1, time.perf_counter_ns() - total_started)
    wrapper_ns = max(0, elapsed - setup_ns - queries_ns - close_ns)
    timings = {
        "setup_ns": setup_ns,
        "queries_ns": queries_ns,
        "close_ns": close_ns,
        "wrapper_ns": wrapper_ns,
    }
    timings["batch_total_ns"] = sum(timings.values())
    return {
        "status": "ok",
        "method": CANDIDATE,
        "query_count": len(cases),
        "timings_ns": timings,
        "amortized_query_ns": timings["batch_total_ns"] / len(cases),
        "query_records": query_records,
        "setup_detail": setup_detail,
        "session_snapshot": before_close,
        "prepared_context_sha256": prepared_context.context_sha256,
        "exact_check_passed": all(row["exact_check_passed"] for row in query_records),
    }


def _validate_row(row: dict[str, Any]) -> None:
    timings = row.get("timings_ns")
    charge = row.get("lifecycle_preparation_charge_ns")
    if (
        row.get("method") not in METHODS
        or row.get("n_vars") not in N_VARS
        or row.get("query_count") != QUERY_COUNT
        or row.get("exact_check_passed") is not True
        or type(charge) is not int or charge < 0
        or not isinstance(timings, dict)
        or set(timings) != set(TIMING_FIELDS)
        or any(type(timings[field]) is not int or timings[field] < 0 for field in TIMING_FIELDS)
        or timings["batch_total_ns"] != sum(timings[field] for field in BATCH_TIMING_FIELDS)
    ):
        raise ValueError("invalid or inexact C30 timing row")
    if row["method"] == BASELINE and charge != 0:
        raise ValueError("C30 baseline received preparation charge")
    if row["method"] == CANDIDATE:
        detail = row.get("setup_detail")
        if (
            not isinstance(detail, dict)
            or set(detail) != {
                "prepared_context_bind_ns", "session_initialize_ns", "setup_total_ns"}
            or detail["setup_total_ns"] != (
                detail["prepared_context_bind_ns"] + detail["session_initialize_ns"])
        ):
            raise ValueError("invalid C30 prepared setup decomposition")


def summarize(rows: list[dict[str, Any]], *, lifecycle_preparation_ns: int) -> dict[str, Any]:
    if type(lifecycle_preparation_ns) is not int or lifecycle_preparation_ns < 1:
        raise ValueError("invalid C30 lifecycle preparation charge")
    grouped: dict[tuple[int, str, int, int], dict[str, dict[str, Any]]] = {}
    for row in rows:
        _validate_row(row)
        identity = (row["block"], row["pair_id"], row["n_vars"], row["width_position"])
        methods = grouped.setdefault(identity, {})
        if row["method"] in methods:
            raise ValueError("duplicate C30 timing arm")
        methods[row["method"]] = row
    if any(set(methods) != set(METHODS) for methods in grouped.values()):
        raise ValueError("unpaired C30 timing cell")
    pairs = [
        {"block": identity[0], "pair_id": identity[1], "n_vars": identity[2],
         "width_position": identity[3], "baseline": methods[BASELINE],
         "candidate": methods[CANDIDATE]}
        for identity, methods in grouped.items()
    ]
    if sum(row["lifecycle_preparation_charge_ns"] for row in rows) != lifecycle_preparation_ns:
        raise ValueError("C30 preparation charge is not conserved")
    by_width = {}
    for n_vars in N_VARS:
        selected = [pair for pair in pairs if pair["n_vars"] == n_vars]
        if not selected:
            raise ValueError("missing C30 width")
        baseline_medians = {
            field: _median(pair["baseline"]["timings_ns"][field] for pair in selected)
            for field in TIMING_FIELDS
        }
        candidate_medians = {
            field: _median(pair["candidate"]["timings_ns"][field] for pair in selected)
            for field in TIMING_FIELDS
        }
        candidate_charged = [
            pair["candidate"]["timings_ns"]["batch_total_ns"]
            + pair["candidate"]["lifecycle_preparation_charge_ns"]
            for pair in selected
        ]
        total_speedups = [
            pair["baseline"]["timings_ns"]["batch_total_ns"] / charged
            for pair, charged in zip(selected, candidate_charged)
        ]
        raw_speedups = [
            pair["baseline"]["timings_ns"]["batch_total_ns"]
            / pair["candidate"]["timings_ns"]["batch_total_ns"]
            for pair in selected
        ]
        query_speedups = [
            pair["baseline"]["timings_ns"]["queries_ns"]
            / pair["candidate"]["timings_ns"]["queries_ns"]
            for pair in selected
        ]
        candidate_first = [index for index, pair in enumerate(selected)
                           if pair["candidate"]["arm_position"] == 0]
        candidate_second = [index for index, pair in enumerate(selected)
                            if pair["candidate"]["arm_position"] == 1]
        if len(candidate_first) != len(candidate_second):
            raise ValueError("C30 method order is not balanced")
        charged_median = _median(candidate_charged)
        by_width[str(n_vars)] = {
            "paired_blocks": len(selected),
            "baseline_median_ns": baseline_medians,
            "candidate_raw_median_ns": candidate_medians,
            "candidate_charged_median_batch_total_ns": charged_median,
            "ratio_of_median_charged_total_speedup": (
                baseline_medians["batch_total_ns"] / charged_median),
            "ratio_of_median_raw_total_speedup": (
                baseline_medians["batch_total_ns"] / candidate_medians["batch_total_ns"]),
            "ratio_of_median_query_speedup": (
                baseline_medians["queries_ns"] / candidate_medians["queries_ns"]),
            "median_paired_charged_total_speedup": _median(total_speedups),
            "minimum_paired_charged_total_speedup": min(total_speedups),
            "maximum_paired_charged_total_speedup": max(total_speedups),
            "median_paired_raw_total_speedup": _median(raw_speedups),
            "median_paired_query_speedup": _median(query_speedups),
            "candidate_charged_nonquery_share": (
                charged_median - candidate_medians["queries_ns"]) / charged_median,
            "candidate_first_median_charged_total_speedup": _median(
                total_speedups[index] for index in candidate_first),
            "candidate_second_median_charged_total_speedup": _median(
                total_speedups[index] for index in candidate_second),
            "charged_total_regression_blocks": sum(value < 1.0 for value in total_speedups),
            "query_regression_blocks": sum(value < 1.0 for value in query_speedups),
        }
    baseline_total = sum(row["baseline_median_ns"]["batch_total_ns"]
                         for row in by_width.values())
    candidate_total = sum(row["candidate_charged_median_batch_total_ns"]
                          for row in by_width.values())
    baseline_queries = sum(row["baseline_median_ns"]["queries_ns"]
                           for row in by_width.values())
    candidate_queries = sum(row["candidate_raw_median_ns"]["queries_ns"]
                            for row in by_width.values())
    aggregate = baseline_total / candidate_total
    minimum_width = min(row["ratio_of_median_charged_total_speedup"]
                        for row in by_width.values())
    candidate_rows = [row for row in rows if row["method"] == CANDIDATE]
    setup_detail = {
        field: _median(row["setup_detail"][field] for row in candidate_rows)
        for field in ("prepared_context_bind_ns", "session_initialize_ns", "setup_total_ns")
    }
    return {
        "exactness_gate": all(row["exact_check_passed"] for row in rows),
        "measurement_batches": len(rows),
        "paired_batches": len(pairs),
        "timed_queries": sum(row["query_count"] for row in rows),
        "lifecycle_preparation_ns": lifecycle_preparation_ns,
        "lifecycle_preparation_charge_conserved": True,
        "aggregate_ratio_of_median_charged_total_speedup": aggregate,
        "aggregate_ratio_of_median_query_speedup": baseline_queries / candidate_queries,
        "minimum_width_ratio_of_median_charged_total_speedup": minimum_width,
        "prepared_no_regret_gate": aggregate >= 1.0 and minimum_width >= 0.90,
        "candidate_setup_detail_median_ns": setup_detail,
        "by_width": by_width,
        "arm_order_balanced": all(
            sum(row["method"] == method and row["arm_position"] == position for row in rows)
            == len(rows) // 4
            for method in METHODS for position in range(2)),
        "width_position_balanced": all(
            sum(row["n_vars"] == n_vars and row["width_position"] == position for row in rows)
            == len(rows) // 16
            for n_vars in N_VARS for position in range(4)),
    }


def _controls(
    *,
    output: Path,
    cases: list[dict[str, Any]],
    oracles: dict[str, Any],
    c27_policy_path: Path,
    c22_policy_path: Path,
) -> dict[str, Any]:
    prepared = prepare_support_policy_context(c27_policy_path, c22_policy_path)
    verify_prepared_policy_sources(prepared)
    seed = cases[0]
    oracle = oracles[seed["case_id"]]["best_artifact"]
    off = SupportAwareGF2Session.from_prepared_context(
        "c30-control-off", prepared, advice_enabled=False, max_queries=1)
    off_result = off.execute(seed).to_dict()
    off.close()
    fallback = SupportAwareGF2Session.from_prepared_context(
        "c30-control-fallback", prepared, max_queries=1)
    fallback_result = fallback.execute(seed, force_selected_refusal=True).to_dict()
    fallback.close()

    c27_copy = output / "control_changed_source_c27.json"
    c22_copy = output / "control_changed_source_c22.json"
    c27_copy.write_bytes(c27_policy_path.read_bytes())
    c22_copy.write_bytes(c22_policy_path.read_bytes())
    changed = prepare_support_policy_context(c27_copy, c22_copy)
    with c27_copy.open("ab") as handle:
        handle.write(b" ")
    try:
        verify_prepared_policy_sources(changed)
    except ValueError:
        source_change_status = "refused"
    else:
        source_change_status = "accepted"

    try:
        SupportAwareGF2Session(
            "c30-control-wrong-bind", None, None,
            prepared_context=prepared,
            required_prepared_context_sha256="0" * 64,
        )
    except ValueError:
        wrong_bind_status = "refused"
    else:
        wrong_bind_status = "accepted"

    c27_tampered = copy.deepcopy(load_support_aware_policy(c27_policy_path))
    c27_tampered["tiny_support_max_n_vars"] = 3
    c27_tampered_path = output / "control_tampered_c27.json"
    _write(c27_tampered_path, c27_tampered)
    try:
        prepare_support_policy_context(c27_tampered_path, c22_policy_path)
    except ValueError:
        c27_tamper_status = "refused"
    else:
        c27_tamper_status = "accepted"

    c22_tampered = copy.deepcopy(load_source_portfolio_policy(c22_policy_path))
    c22_tampered["selected_arm"] = EXHAUSTIVE
    c22_tampered_path = output / "control_tampered_c22.json"
    _write(c22_tampered_path, c22_tampered)
    try:
        prepare_support_policy_context(c27_policy_path, c22_tampered_path)
    except ValueError:
        c22_tamper_status = "refused"
    else:
        c22_tamper_status = "accepted"

    exact_controls = (
        off_result["status"] == "ok"
        and off_result["selected_arm"] == EXHAUSTIVE
        and off_result["best_artifact"] == oracle
        and off_result["exact_check_passed"] is True
        and fallback_result["status"] == "ok"
        and fallback_result["selected_arm"] == EXHAUSTIVE
        and fallback_result["fallback_used"] is True
        and fallback_result["best_artifact"] == oracle
        and fallback_result["exact_check_passed"] is True
    )
    refusal_controls = all(status == "refused" for status in (
        source_change_status, wrong_bind_status, c27_tamper_status, c22_tamper_status))
    return {
        "schema": "crse-c30-prepared-context-controls/v1",
        "advice_off": {
            "status": off_result["status"], "selected_arm": off_result["selected_arm"],
            "artifact_sha256": off_result["artifact_sha256"],
            "exact_check_passed": off_result["exact_check_passed"],
        },
        "forced_fallback": {
            "status": fallback_result["status"],
            "selected_arm": fallback_result["selected_arm"],
            "fallback_used": fallback_result["fallback_used"],
            "artifact_sha256": fallback_result["artifact_sha256"],
            "exact_check_passed": fallback_result["exact_check_passed"],
        },
        "refusals": {
            "changed_source_after_preparation": source_change_status,
            "wrong_context_digest_binding": wrong_bind_status,
            "tampered_c27_at_preparation": c27_tamper_status,
            "tampered_c22_at_preparation": c22_tamper_status,
        },
        "exact_controls_passed": exact_controls,
        "refusal_controls_passed": refusal_controls,
        "all_passed": exact_controls and refusal_controls,
    }


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    comparison = result["c29_comparison"]
    lines = [
        "# C30 immutable prepared-policy context", "",
        f"Status: **{result['status']}**  ",
        f"Prepared no-regret diagnostic gate: **{'pass' if summary['prepared_no_regret_gate'] else 'fail'}**  ",
        "Role: local development evidence; shadow and production promotion remain false", "",
        "C30 validates and hash-binds the frozen C27/C22 policies once, then creates each",
        "eight-query session from the immutable prepared snapshot. The one-time preparation",
        "cost is conserved and allocated across all candidate batches.", "",
        "| Width | C29 total | C30 charged total | C30 query-only | C30 paired range | prepared non-query share |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for n_vars in N_VARS:
        row = summary["by_width"][str(n_vars)]
        old = comparison["by_width"][str(n_vars)]
        lines.append(
            f"| {n_vars} | {old['c29_total_speedup']:.4f}x | "
            f"{row['ratio_of_median_charged_total_speedup']:.4f}x | "
            f"{row['ratio_of_median_query_speedup']:.4f}x | "
            f"{row['minimum_paired_charged_total_speedup']:.4f}-"
            f"{row['maximum_paired_charged_total_speedup']:.4f}x | "
            f"{100 * row['candidate_charged_nonquery_share']:.2f}% |")
    lines += [
        "",
        f"Lifecycle preparation: **{summary['lifecycle_preparation_ns'] / 1e6:.4f} ms**.  ",
        f"Median per-session prepared setup: **{summary['candidate_setup_detail_median_ns']['setup_total_ns'] / 1e6:.4f} ms**.  ",
        f"Aggregate charged total speedup: **{summary['aggregate_ratio_of_median_charged_total_speedup']:.4f}x**.  ",
        f"Minimum-width charged total speedup: **{summary['minimum_width_ratio_of_median_charged_total_speedup']:.4f}x**.",
        "",
        "All timed queries remain exact and the fail-closed controls pass. This local run",
        "tests the concrete C29 overhead diagnosis; its paired dispersion is not a new",
        "cross-machine uncertainty adjudication. Exact fallback remains mandatory.", "",
    ]
    return "\n".join(lines)


def run(
    config: C30Config,
    output: Path,
    dataset_path: Path,
    dataset_verification_path: Path,
    c27_policy_path: Path,
    c22_policy_path: Path,
    c19_policy_path: Path,
    c29_run_path: Path,
    root: Path,
) -> dict[str, Any]:
    config.validate()
    wall_started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    verification = json.loads(dataset_verification_path.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    c27_policy = load_support_aware_policy(c27_policy_path)
    c22_policy = load_source_portfolio_policy(c22_policy_path)
    compiled = compile_work_policy(load_policy(c19_policy_path))
    c29_result = json.loads((c29_run_path / "results.json").read_text(encoding="utf-8"))
    c29_verification = json.loads(
        (c29_run_path / "independent_verification.json").read_text(encoding="utf-8"))
    if (
        len(dataset.get("cases", [])) != 48
        or verification.get("status") != "verified"
        or verification.get("cases_replayed") != 48
        or verification.get("expression_truth_mismatches") != 0
        or verification.get("scalar_oracle_mismatches") != 0
        or verification.get("prior_truth_overlaps") != 0
        or dataset.get("provenance", {}).get("policy_frozen_before_dataset") is not True
        or c27_policy["tiny_support_max_n_vars"] != 4
        or c27_policy["tiny_support_arm"] != TRUTH_SCREENED
        or c27_policy["large_support_arm"] != SOURCE_PACKED_SCREENED
        or c27_policy["training_use"] is not False
        or c22_policy["selected_arm"] != SOURCE_PACKED_SCREENED
        or c22_policy["training_use"] is not False
        or compiled.mode != "constant_leaf"
        or compiled.constant_arm != "explicit_cm_screened"
        or c29_result.get("status") != "complete"
        or c29_result.get("diagnostic_only") is not True
        or c29_result.get("semantic_or_artifact_mismatches") != 0
        or c29_verification.get("status") != "verified"
        or c29_verification.get("summary_recomputed") is not True
        or c29_verification.get("results_sha256") != _sha256(c29_run_path / "results.json")
    ):
        raise ValueError("C30 frozen C27/C29 input contract changed")

    cases = dataset["cases"]
    functional, oracles = build_oracles(cases, config.oracle_config())
    if not functional["all_exact"]:
        raise RuntimeError("C30 exhaustive oracle replay failed")
    contracts = {
        case["case_id"]: decomposition_contract(
            contract_id=f"c30-{case['case_id']}", n_vars=case["n_vars"],
            required_output_sha256=oracles[case["case_id"]]["delivered_sha256"])
        for case in cases
    }
    cases_by_width = {
        n_vars: sorted(
            (case for case in cases if case["n_vars"] == n_vars),
            key=lambda case: (case["truth_sha256"], case["case_id"]),
        )
        for n_vars in N_VARS
    }
    controls = _controls(
        output=output, cases=cases, oracles=oracles,
        c27_policy_path=c27_policy_path, c22_policy_path=c22_policy_path)
    if not controls["all_passed"]:
        raise RuntimeError("C30 prepared policy controls failed")
    _write(output / "functional_controls.json", controls)

    prepared = prepare_support_policy_context(c27_policy_path, c22_policy_path)
    verify_prepared_policy_sources(prepared)
    _write(output / "prepared_context.json", prepared.identity())
    schedule = build_schedule(config)
    candidate_batches = sum(cell["method"] == CANDIDATE for cell in schedule)
    base_charge, extra = divmod(prepared.preparation_ns, candidate_batches)
    candidate_index = 0
    rows = []
    for cell in schedule:
        if time.perf_counter() - wall_started > config.max_seconds:
            raise TimeoutError("C30 experiment exceeded wall bound")
        sequence = case_sequence(
            cases_by_width, cell["n_vars"], config.query_count, cell["block"])
        if cell["method"] == BASELINE:
            execution = execute_c25_direct_batch(
                session_id=f"c30-{cell['pair_id']}-p{cell['arm_position']}-{BASELINE}",
                method=BASELINE, cases=sequence, contracts=contracts, oracles=oracles,
                c22_policy_path=c22_policy_path, c19_policy_path=c19_policy_path,
                max_partitions=config.max_partitions,
                materialize_budget=config.materialize_budget,
            )
            charge = 0
        else:
            execution = execute_prepared_batch(
                session_id=f"c30-{cell['pair_id']}-p{cell['arm_position']}-{CANDIDATE}",
                cases=sequence, oracles=oracles, prepared_context=prepared)
            charge = base_charge + (1 if candidate_index < extra else 0)
            candidate_index += 1
        rows.append({**cell, **execution, "lifecycle_preparation_charge_ns": charge})
    verify_prepared_policy_sources(prepared)
    _write_jsonl(output / "measurements.jsonl", rows)
    summary = summarize(rows, lifecycle_preparation_ns=prepared.preparation_ns)
    c29_by_width = c29_result["summary"]["by_width"]
    c29_comparison = {
        "source_run": _rel(c29_run_path, root),
        "source_results_sha256": _sha256(c29_run_path / "results.json"),
        "by_width": {
            str(n_vars): {
                "c29_total_speedup": c29_by_width[str(n_vars)][
                    "ratio_of_median_total_speedup"],
                "c30_charged_total_speedup": summary["by_width"][str(n_vars)][
                    "ratio_of_median_charged_total_speedup"],
                "relative_speedup_improvement": (
                    summary["by_width"][str(n_vars)][
                        "ratio_of_median_charged_total_speedup"]
                    / c29_by_width[str(n_vars)]["ratio_of_median_total_speedup"]),
            }
            for n_vars in N_VARS
        },
    }
    spec = {
        "schema": SCHEMA,
        "config": asdict(config),
        "dataset_path": _rel(dataset_path, root),
        "dataset_sha256": _sha256(dataset_path),
        "dataset_verification_path": _rel(dataset_verification_path, root),
        "dataset_verification_sha256": _sha256(dataset_verification_path),
        "c27_policy_path": _rel(c27_policy_path, root),
        "c27_policy_file_sha256": _sha256(c27_policy_path),
        "c27_policy_sha256": c27_policy["policy_sha256"],
        "c22_policy_path": _rel(c22_policy_path, root),
        "c22_policy_file_sha256": _sha256(c22_policy_path),
        "c22_policy_sha256": c22_policy["policy_sha256"],
        "c19_policy_path": _rel(c19_policy_path, root),
        "c19_policy_file_sha256": _sha256(c19_policy_path),
        "c29_run_path": _rel(c29_run_path, root),
        "c29_results_sha256": _sha256(c29_run_path / "results.json"),
        "c29_independent_verification_sha256": _sha256(
            c29_run_path / "independent_verification.json"),
        "methods": list(METHODS),
        "query_count": QUERY_COUNT,
        "prepared_context_sha256": prepared.context_sha256,
        "lifecycle_preparation_ns": prepared.preparation_ns,
        "lifecycle_preparation_fully_charged": True,
        "unchanged_c29_schedule": True,
        "unchanged_exact_query_path": True,
        "policy_refit": False,
        "training": False,
        "shadow_promotion": False,
        "production_promotion": False,
    }
    _write(output / "run_spec.json", spec)
    result = {
        "schema": SCHEMA,
        "status": "complete" if summary["exactness_gate"] and controls["all_passed"] else "failed",
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
        "c29_comparison": c29_comparison,
        "functional_controls_passed": controls["all_passed"],
        "semantic_or_artifact_mismatches": sum(
            row["exact_check_passed"] is not True for row in rows),
        "policy_refit": False,
        "training": False,
        "development_evidence": True,
        "shadow_promotion": False,
        "production_promotion": False,
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    sources = (
        "cmbench/comparative/gf2_prepared_policy_experiment.py",
        "cmbench/comparative/gf2_resident_session_experiment.py",
        "cmbench/comparative/gf2_support_aware_experiment.py",
        "cmbench/recognition/gf2_prepared_support_context.py",
        "cmbench/recognition/gf2_support_aware_session.py",
        "scripts/cm_comparative_c30_prepared_policy.py",
    )
    artifacts = (
        "control_changed_source_c27.json", "control_changed_source_c22.json",
        "control_tampered_c27.json", "control_tampered_c22.json",
        "functional_controls.json", "prepared_context.json", "measurements.jsonl",
        "run_spec.json", "results.json", "report.md",
    )
    _write(output / "manifest.json", {
        "schema": "crse-c30-run-manifest/v1",
        "inputs": {
            "dataset_sha256": _sha256(dataset_path),
            "dataset_verification_sha256": _sha256(dataset_verification_path),
            "c27_policy_file_sha256": _sha256(c27_policy_path),
            "c22_policy_file_sha256": _sha256(c22_policy_path),
            "c19_policy_file_sha256": _sha256(c19_policy_path),
            "c29_results_sha256": _sha256(c29_run_path / "results.json"),
            "c29_independent_verification_sha256": _sha256(
                c29_run_path / "independent_verification.json"),
        },
        "sources": {name: _sha256(root / name) for name in sources},
        "artifacts": {name: _sha256(output / name) for name in artifacts},
    })
    return result
