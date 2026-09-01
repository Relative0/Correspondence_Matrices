"""C29 q8 variance localization for the exact support-aware GF(2) path.

C29 is diagnostic evidence.  It retains the frozen C27 policy/corpus, pairs the
candidate immediately with its direct-screened control, and records component
timings so fixed lifecycle overhead can be separated from query-path variance.
"""
from __future__ import annotations

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

from cmbench.recognition.gf2_source_portfolio import (
    SOURCE_PACKED_SCREENED,
    load_source_portfolio_policy,
)
from cmbench.recognition.gf2_support_aware_policy import (
    TRUTH_SCREENED,
    load_support_aware_policy,
)
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
from .gf2_support_aware_experiment import execute_support_aware_batch
from .gf2_table_experiment import C21Config, build_oracles
from .schedule import balanced_orders


SCHEMA = "crse-c29-gf2-variance-localization/v1"
LOCALIZATION_SCHEMA = "crse-c29-frozen-q8-localization/v1"
BASELINE = "resident_direct_screened"
CANDIDATE = "support_aware_c27_advice_on"
METHODS = (BASELINE, CANDIDATE)
QUERY_COUNT = 8
TIMING_FIELDS = (*BATCH_TIMING_FIELDS, "batch_total_ns")
CANDIDATE_SETUP_FIELDS = (
    "c27_policy_load_validate_ns",
    "c22_policy_load_validate_ns",
    "session_initialize_ns",
    "setup_total_ns",
)


@dataclass(frozen=True)
class C29Config:
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
            raise ValueError("invalid C29 experiment bounds")

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


def build_schedule(config: C29Config) -> tuple[dict[str, Any], ...]:
    """Build adjacent method pairs with balanced method and width positions."""
    config.validate()
    width_orders = balanced_orders(N_VARS)
    method_orders = balanced_orders(METHODS)
    schedule: list[dict[str, Any]] = []
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
    expected = config.blocks * len(N_VARS) * len(METHODS)
    if len(schedule) != expected:
        raise AssertionError("C29 schedule cardinality mismatch")
    return tuple(schedule)


def _validate_timing_row(row: dict[str, Any]) -> None:
    timings = row.get("timings_ns")
    if (
        row.get("method") not in METHODS
        or row.get("n_vars") not in N_VARS
        or row.get("query_count") != QUERY_COUNT
        or row.get("exact_check_passed") is not True
        or not isinstance(timings, dict)
        or set(timings) != set(TIMING_FIELDS)
        or any(type(timings[field]) is not int or timings[field] < 0 for field in TIMING_FIELDS)
        or timings["batch_total_ns"] != sum(timings[field] for field in BATCH_TIMING_FIELDS)
    ):
        raise ValueError("invalid or inexact C29/C27 timing row")
    if row["method"] == CANDIDATE:
        setup_detail = row.get("setup_detail")
        if (
            not isinstance(setup_detail, dict)
            or set(setup_detail) != set(CANDIDATE_SETUP_FIELDS)
            or any(type(setup_detail[field]) is not int or setup_detail[field] < 1
                   for field in CANDIDATE_SETUP_FIELDS)
            or setup_detail["setup_total_ns"] != sum(
                setup_detail[field] for field in CANDIDATE_SETUP_FIELDS[:-1])
        ):
            raise ValueError("invalid C29 candidate setup decomposition")


def _median(values: Iterable[int | float]) -> float:
    materialized = list(values)
    if not materialized:
        raise ValueError("empty median")
    return float(statistics.median(materialized))


def _pair_rows(rows: Iterable[dict[str, Any]], identity_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for row in rows:
        _validate_timing_row(row)
        identity = tuple(row[field] for field in identity_fields)
        methods = grouped.setdefault(identity, {})
        if row["method"] in methods:
            raise ValueError("duplicate timing arm")
        methods[row["method"]] = row
    pairs = []
    for identity, methods in grouped.items():
        if set(methods) != set(METHODS):
            raise ValueError("unpaired timing cell")
        pairs.append({
            **dict(zip(identity_fields, identity)),
            "baseline": methods[BASELINE],
            "candidate": methods[CANDIDATE],
        })
    return pairs


def localize_frozen_executions(executions: list[dict[str, Any]]) -> dict[str, Any]:
    """Decompose the five frozen C27 q8 executions by width, round, and component."""
    if not executions:
        raise ValueError("C29 requires frozen C27 executions")
    details = []
    all_cells = []
    for execution in executions:
        rows = [row for row in execution.get("rows", [])
                if row.get("query_count") == QUERY_COUNT and row.get("method") in METHODS]
        pairs = _pair_rows(rows, ("n_vars", "round"))
        if len(pairs) != len(N_VARS) * 5:
            raise ValueError("C29 requires a complete five-round frozen q8 surface")
        by_width = {}
        cells = []
        for pair in sorted(pairs, key=lambda row: (row["n_vars"], row["round"])):
            baseline = pair["baseline"]["timings_ns"]
            candidate = pair["candidate"]["timings_ns"]
            cell = {
                "execution_id": execution["execution_id"],
                "physical_machine_id": execution["physical_machine_id"],
                "n_vars": pair["n_vars"],
                "round": pair["round"],
                "total_speedup": baseline["batch_total_ns"] / candidate["batch_total_ns"],
                "query_speedup": baseline["queries_ns"] / candidate["queries_ns"],
                "candidate_nonquery_share": (
                    candidate["batch_total_ns"] - candidate["queries_ns"]
                ) / candidate["batch_total_ns"],
                "candidate_component_ns": {field: candidate[field] for field in TIMING_FIELDS},
                "baseline_component_ns": {field: baseline[field] for field in TIMING_FIELDS},
            }
            cells.append(cell)
            all_cells.append(cell)
        for n_vars in N_VARS:
            selected = [row for row in cells if row["n_vars"] == n_vars]
            totals = [row["total_speedup"] for row in selected]
            queries = [row["query_speedup"] for row in selected]
            by_width[str(n_vars)] = {
                "rounds": len(selected),
                "median_total_speedup": _median(totals),
                "minimum_total_speedup": min(totals),
                "maximum_total_speedup": max(totals),
                "total_speedup_range": max(totals) - min(totals),
                "median_query_speedup": _median(queries),
                "median_candidate_nonquery_share": _median(
                    row["candidate_nonquery_share"] for row in selected),
                "total_regression_rounds": sum(value < 1.0 for value in totals),
                "query_regression_rounds": sum(value < 1.0 for value in queries),
                "overhead_only_regression_rounds": sum(
                    row["total_speedup"] < 1.0 <= row["query_speedup"] for row in selected),
            }
        details.append({
            "execution_id": execution["execution_id"],
            "physical_machine_id": execution["physical_machine_id"],
            "environment": execution.get("environment"),
            "by_width": by_width,
            "cells": cells,
        })
    by_width = {}
    for n_vars in N_VARS:
        selected = [row for row in all_cells if row["n_vars"] == n_vars]
        by_width[str(n_vars)] = {
            "cells": len(selected),
            "total_regression_cells": sum(row["total_speedup"] < 1.0 for row in selected),
            "query_regression_cells": sum(row["query_speedup"] < 1.0 for row in selected),
            "overhead_only_regression_cells": sum(
                row["total_speedup"] < 1.0 <= row["query_speedup"] for row in selected),
            "median_total_speedup": _median(row["total_speedup"] for row in selected),
            "minimum_total_speedup": min(row["total_speedup"] for row in selected),
            "median_query_speedup": _median(row["query_speedup"] for row in selected),
            "median_candidate_nonquery_share": _median(
                row["candidate_nonquery_share"] for row in selected),
        }
    worst = sorted(all_cells, key=lambda row: row["total_speedup"])[:12]
    return {
        "schema": LOCALIZATION_SCHEMA,
        "query_count": QUERY_COUNT,
        "execution_count": len(executions),
        "physical_machine_count": len({row["physical_machine_id"] for row in executions}),
        "paired_cells": len(all_cells),
        "by_width": by_width,
        "executions": details,
        "worst_total_speedup_cells": worst,
        "policy_refit": False,
        "training": False,
        "timings_rerun": False,
    }


def summarize_interleaved(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = _pair_rows(rows, ("block", "pair_id", "n_vars", "width_position"))
    by_width = {}
    for n_vars in N_VARS:
        selected = [pair for pair in pairs if pair["n_vars"] == n_vars]
        if len(selected) == 0:
            raise ValueError("missing C29 width")
        baseline_medians = {
            field: _median(pair["baseline"]["timings_ns"][field] for pair in selected)
            for field in TIMING_FIELDS
        }
        candidate_medians = {
            field: _median(pair["candidate"]["timings_ns"][field] for pair in selected)
            for field in TIMING_FIELDS
        }
        total_speedups = [
            pair["baseline"]["timings_ns"]["batch_total_ns"]
            / pair["candidate"]["timings_ns"]["batch_total_ns"]
            for pair in selected
        ]
        query_speedups = [
            pair["baseline"]["timings_ns"]["queries_ns"]
            / pair["candidate"]["timings_ns"]["queries_ns"]
            for pair in selected
        ]
        candidate_first = [pair for pair in selected
                           if pair["candidate"]["arm_position"] == 0]
        candidate_second = [pair for pair in selected
                            if pair["candidate"]["arm_position"] == 1]
        if len(candidate_first) != len(candidate_second):
            raise ValueError("C29 method order is not balanced")
        by_width[str(n_vars)] = {
            "paired_blocks": len(selected),
            "baseline_median_ns": baseline_medians,
            "candidate_median_ns": candidate_medians,
            "median_paired_total_speedup": _median(total_speedups),
            "minimum_paired_total_speedup": min(total_speedups),
            "maximum_paired_total_speedup": max(total_speedups),
            "median_paired_query_speedup": _median(query_speedups),
            "minimum_paired_query_speedup": min(query_speedups),
            "maximum_paired_query_speedup": max(query_speedups),
            "ratio_of_median_total_speedup": (
                baseline_medians["batch_total_ns"] / candidate_medians["batch_total_ns"]),
            "ratio_of_median_query_speedup": (
                baseline_medians["queries_ns"] / candidate_medians["queries_ns"]),
            "candidate_median_nonquery_ns": (
                candidate_medians["batch_total_ns"] - candidate_medians["queries_ns"]),
            "candidate_median_nonquery_share": (
                candidate_medians["batch_total_ns"] - candidate_medians["queries_ns"]
            ) / candidate_medians["batch_total_ns"],
            "candidate_first_median_total_speedup": _median(
                pair["baseline"]["timings_ns"]["batch_total_ns"]
                / pair["candidate"]["timings_ns"]["batch_total_ns"]
                for pair in candidate_first),
            "candidate_second_median_total_speedup": _median(
                pair["baseline"]["timings_ns"]["batch_total_ns"]
                / pair["candidate"]["timings_ns"]["batch_total_ns"]
                for pair in candidate_second),
            "total_regression_blocks": sum(value < 1.0 for value in total_speedups),
            "query_regression_blocks": sum(value < 1.0 for value in query_speedups),
            "overhead_only_regression_blocks": sum(
                total < 1.0 <= query for total, query in zip(total_speedups, query_speedups)),
        }
    baseline_total = sum(row["baseline_median_ns"]["batch_total_ns"]
                         for row in by_width.values())
    candidate_total = sum(row["candidate_median_ns"]["batch_total_ns"]
                          for row in by_width.values())
    baseline_queries = sum(row["baseline_median_ns"]["queries_ns"]
                           for row in by_width.values())
    candidate_queries = sum(row["candidate_median_ns"]["queries_ns"]
                            for row in by_width.values())
    candidate_rows = [row for row in rows if row["method"] == CANDIDATE]
    candidate_setup_detail = {
        field: _median(row["setup_detail"][field] for row in candidate_rows)
        for field in CANDIDATE_SETUP_FIELDS
    }
    return {
        "exactness_gate": all(row.get("exact_check_passed") is True for row in rows),
        "measurement_batches": len(rows),
        "paired_batches": len(pairs),
        "timed_queries": sum(row["query_count"] for row in rows),
        "aggregate_ratio_of_median_total_speedup": baseline_total / candidate_total,
        "aggregate_ratio_of_median_query_speedup": baseline_queries / candidate_queries,
        "candidate_setup_detail_median_ns": candidate_setup_detail,
        "candidate_policy_load_median_share_of_setup": (
            candidate_setup_detail["c27_policy_load_validate_ns"]
            + candidate_setup_detail["c22_policy_load_validate_ns"]
        ) / candidate_setup_detail["setup_total_ns"],
        "by_width": by_width,
        "arm_order_balanced": all(
            sum(row["method"] == method and row["arm_position"] == position for row in rows)
            == len(rows) // (len(METHODS) * len(METHODS))
            for method in METHODS for position in range(len(METHODS))),
        "width_position_balanced": all(
            sum(row["n_vars"] == n_vars and row["width_position"] == position for row in rows)
            == len(rows) // (len(N_VARS) * len(N_VARS))
            for n_vars in N_VARS for position in range(len(N_VARS))),
    }


def render_report(result: dict[str, Any], frozen: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# C29 q8 variance localization", "",
        f"Status: **{result['status']}**  ",
        "Role: diagnostic only; no training, refit, shadow promotion, or production promotion", "",
        "C29 first decomposes the five frozen C27 q8 executions. It then times the unchanged",
        "candidate and resident direct-screened control as adjacent pairs. Both arm order and",
        "width position are counterbalanced, and setup/query/close/wrapper time remains visible.", "",
        "## Frozen C27 localization", "",
        "| Width | regression cells | query regressions | overhead-only regressions | median total | median query | candidate non-query share |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for n_vars in N_VARS:
        row = frozen["by_width"][str(n_vars)]
        lines.append(
            f"| {n_vars} | {row['total_regression_cells']}/{row['cells']} | "
            f"{row['query_regression_cells']}/{row['cells']} | "
            f"{row['overhead_only_regression_cells']}/{row['cells']} | "
            f"{row['median_total_speedup']:.4f}x | {row['median_query_speedup']:.4f}x | "
            f"{100 * row['median_candidate_nonquery_share']:.2f}% |")
    lines += [
        "", "## Counterbalanced local diagnostic", "",
        "| Width | total speedup | query-only speedup | paired total range | candidate non-query share | candidate-first | candidate-second |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for n_vars in N_VARS:
        row = summary["by_width"][str(n_vars)]
        lines.append(
            f"| {n_vars} | {row['ratio_of_median_total_speedup']:.4f}x | "
            f"{row['ratio_of_median_query_speedup']:.4f}x | "
            f"{row['minimum_paired_total_speedup']:.4f}-{row['maximum_paired_total_speedup']:.4f}x | "
            f"{100 * row['candidate_median_nonquery_share']:.2f}% | "
            f"{row['candidate_first_median_total_speedup']:.4f}x | "
            f"{row['candidate_second_median_total_speedup']:.4f}x |")
    lines += [
        "",
        f"Aggregate ratio-of-medians total speedup: **{summary['aggregate_ratio_of_median_total_speedup']:.4f}x**.  ",
        f"Aggregate ratio-of-medians query-only speedup: **{summary['aggregate_ratio_of_median_query_speedup']:.4f}x**.",
        f"Frozen-policy load/validation accounts for **{100 * summary['candidate_policy_load_median_share_of_setup']:.2f}%** of the candidate's median setup time.",
        "",
        "These local timings diagnose where variance enters; they do not replace C28's",
        "cross-machine ruling. Exact fallback remains mandatory and promotion remains false.",
        "",
    ]
    return "\n".join(lines)


def run(config: C29Config, output: Path, dataset_path: Path,
        dataset_verification_path: Path, c27_policy_path: Path,
        c22_policy_path: Path, c19_policy_path: Path,
        c28_input_manifest_path: Path, root: Path) -> dict[str, Any]:
    config.validate()
    wall_started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    verification = json.loads(dataset_verification_path.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    c27_policy = load_support_aware_policy(c27_policy_path)
    c22_policy = load_source_portfolio_policy(c22_policy_path)
    compiled = compile_work_policy(load_policy(c19_policy_path))
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
    ):
        raise ValueError("C29 frozen corpus or policy contract changed")

    c28_manifest = json.loads(c28_input_manifest_path.read_text(encoding="utf-8"))
    executions = []
    if (
        c28_manifest.get("schema") != "crse-c28-cross-machine-input-manifest/v1"
        or c28_manifest.get("source_execution_count") != 5
        or c28_manifest.get("physical_machine_count") != 2
        or c28_manifest.get("policy_refit") is not False
        or c28_manifest.get("training") is not False
        or c28_manifest.get("timings_rerun") is not False
    ):
        raise ValueError("C29 requires the independently adjudicated C28 input manifest")
    for source in c28_manifest["executions"]:
        measurements = root / source["path"] / "measurements.jsonl"
        expected = source["files"]["measurements.jsonl"]
        if _sha256(measurements) != expected["sha256"] or measurements.stat().st_size != expected["bytes"]:
            raise ValueError("C29 frozen C27 measurement fingerprint mismatch")
        rows = [json.loads(line) for line in measurements.read_text(encoding="utf-8").splitlines()]
        executions.append({
            "execution_id": source["execution_id"],
            "physical_machine_id": source["physical_machine_id"],
            "environment": source["environment"],
            "rows": rows,
        })
    frozen = localize_frozen_executions(executions)

    cases = dataset["cases"]
    functional, oracles = build_oracles(cases, config.oracle_config())
    if not functional["all_exact"]:
        raise RuntimeError("C29 exhaustive oracle replay failed")
    contracts = {
        case["case_id"]: decomposition_contract(
            contract_id=f"c29-{case['case_id']}", n_vars=case["n_vars"],
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
    schedule = build_schedule(config)
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
        "c28_input_manifest_path": _rel(c28_input_manifest_path, root),
        "c28_input_manifest_sha256": _sha256(c28_input_manifest_path),
        "methods": list(METHODS),
        "query_count": QUERY_COUNT,
        "adjacent_pairing": True,
        "method_order_counterbalanced": True,
        "width_position_counterbalanced": True,
        "component_timing_retained": True,
        "policy_refit": False,
        "training": False,
        "shadow_promotion": False,
        "production_promotion": False,
    }
    _write(output / "run_spec.json", spec)
    _write(output / "frozen_localization.json", frozen)

    rows = []
    for cell in schedule:
        if time.perf_counter() - wall_started > config.max_seconds:
            raise TimeoutError("C29 experiment exceeded wall bound")
        sequence = case_sequence(
            cases_by_width, cell["n_vars"], config.query_count, cell["block"])
        method = cell["method"]
        if method == BASELINE:
            execution = execute_c25_direct_batch(
                session_id=f"c29-{cell['pair_id']}-p{cell['arm_position']}-{method}",
                method=method, cases=sequence, contracts=contracts, oracles=oracles,
                c22_policy_path=c22_policy_path, c19_policy_path=c19_policy_path,
                max_partitions=config.max_partitions,
                materialize_budget=config.materialize_budget,
            )
        else:
            execution = execute_support_aware_batch(
                session_id=f"c29-{cell['pair_id']}-p{cell['arm_position']}-{method}",
                method=method, cases=sequence, oracles=oracles,
                c27_policy_path=c27_policy_path, c22_policy_path=c22_policy_path,
            )
        rows.append({**cell, **execution})
    _write_jsonl(output / "measurements.jsonl", rows)
    summary = summarize_interleaved(rows)
    result = {
        "schema": SCHEMA,
        "status": "complete" if summary["exactness_gate"] else "failed",
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
        "frozen_executions_localized": frozen["execution_count"],
        "frozen_physical_machines": frozen["physical_machine_count"],
        "frozen_paired_q8_cells": frozen["paired_cells"],
        "summary": summary,
        "semantic_or_artifact_mismatches": sum(
            row["exact_check_passed"] is not True for row in rows),
        "policy_refit": False,
        "training": False,
        "diagnostic_only": True,
        "shadow_promotion": False,
        "production_promotion": False,
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(
        render_report(result, frozen), encoding="utf-8", newline="\n")
    sources = (
        "cmbench/comparative/gf2_variance_localization.py",
        "cmbench/comparative/gf2_support_aware_experiment.py",
        "cmbench/comparative/gf2_resident_session_experiment.py",
        "cmbench/comparative/schedule.py",
        "scripts/cm_comparative_c29_variance_localization.py",
    )
    artifacts = (
        "run_spec.json", "frozen_localization.json", "measurements.jsonl",
        "results.json", "report.md",
    )
    _write(output / "manifest.json", {
        "schema": "crse-c29-run-manifest/v1",
        "inputs": {
            "dataset_sha256": _sha256(dataset_path),
            "dataset_verification_sha256": _sha256(dataset_verification_path),
            "c27_policy_file_sha256": _sha256(c27_policy_path),
            "c22_policy_file_sha256": _sha256(c22_policy_path),
            "c19_policy_file_sha256": _sha256(c19_policy_path),
            "c28_input_manifest_sha256": _sha256(c28_input_manifest_path),
        },
        "sources": {name: _sha256(root / name) for name in sources},
        "artifacts": {name: _sha256(output / name) for name in artifacts},
    })
    return result
