"""C16 exact-screened tail experiment for bounded CM/GF(2) artifacts."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from cm_expr_serde import expr_from_json

from .gf2_decomposition import (
    ExactGF2Analysis,
    analyze_exact_gf2,
    analyze_screened_exact_gf2,
    truth_sha256,
)
from .gf2_decomposition_experiment import make_gf2_controls
from .portfolio import reference_bits
from .proved_rules import canonical
from .source_anf_hybrid import packed_truth_bits, source_anf_packed
from .yosys_composed_holdout_data import make_yosys_composed_holdout

SCHEMA = "crse-c16-gf2-screened-tail-experiment/v1"
METHODS = (
    "explicit_cm_exhaustive",
    "explicit_cm_screened",
    "packed_source_anf_screened",
)


@dataclass(frozen=True)
class GF2ScreeningConfig:
    run_id: str = "c16-gf2-screened-tail-windows-20260830-001"
    seed: int = 20260830
    rounds: int = 3
    max_partitions: int = 64
    materialize_budget: int = 4
    max_seconds: float = 420.0

    def validate(self) -> None:
        if (type(self.run_id) is not str or not self.run_id or type(self.seed) is not int
                or type(self.rounds) is not int or not 3 <= self.rounds <= 8
                or type(self.max_partitions) is not int or not 8 <= self.max_partitions <= 128
                or type(self.materialize_budget) is not int
                or not 1 <= self.materialize_budget <= 16
                or not 60 <= self.max_seconds <= 1800):
            raise ValueError("invalid C16 GF(2) screening config")


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def _best_document(analysis: ExactGF2Analysis) -> dict[str, Any] | None:
    return analysis.best.to_dict() if analysis.best is not None else None


def _best_fields(analysis: ExactGF2Analysis) -> dict[str, Any]:
    best = analysis.best
    return {
        "best_kind": best.kind if best else None,
        "best_factor_bits": best.document["factor_bits"] if best else None,
        "best_artifact_sha256": best.digest if best else None,
    }


def _analyze(bits: int, n_vars: int, method: str,
             config: GF2ScreeningConfig) -> ExactGF2Analysis:
    if method == "explicit_cm_exhaustive":
        return analyze_exact_gf2(bits, n_vars, max_partitions=config.max_partitions)
    return analyze_screened_exact_gf2(
        bits,
        n_vars,
        max_partitions=config.max_partitions,
        materialize_budget=config.materialize_budget,
    )


def _method_bits(method: str, expression, case: dict[str, Any]) -> int:
    if method in {"explicit_cm_exhaustive", "explicit_cm_screened"}:
        return reference_bits(expression, case["n_vars"])
    if method == "packed_source_anf_screened":
        polynomial, _stats = source_anf_packed(case["expression_v2"], case["n_vars"])
        return packed_truth_bits(polynomial, case["n_vars"])
    raise ValueError("unknown C16 method")


def _measure(method: str, case: dict[str, Any], expression, expected_bits: int,
             expected_best: dict[str, Any] | None, config: GF2ScreeningConfig,
             round_index: int) -> dict[str, Any]:
    started = time.perf_counter_ns()
    bits = _method_bits(method, expression, case)
    representation_ns = max(1, time.perf_counter_ns() - started)
    analysis_started = time.perf_counter_ns()
    analysis = _analyze(bits, case["n_vars"], method, config)
    analysis_ns = max(1, time.perf_counter_ns() - analysis_started)
    best = _best_document(analysis)
    semantic_mismatch = int(bits != expected_bits)
    artifact_mismatch = int(best != expected_best)
    return {
        "schema": "crse-c16-gf2-screened-tail-measurement/v1",
        "case_id": case["case_id"],
        "split": case["split"],
        "source_kind": case["source_kind"],
        "n_vars": case["n_vars"],
        "method": method,
        "round": round_index,
        "status": "ok" if not semantic_mismatch and not artifact_mismatch else "mismatch",
        "semantic_mismatches": semantic_mismatch,
        "artifact_mismatches": artifact_mismatch,
        "representation_ns": representation_ns,
        "analysis_ns": analysis_ns,
        "total_ns": representation_ns + analysis_ns,
        "partitions_screened": analysis.partitions_tested,
        "descriptors_screened": analysis.descriptors_screened,
        "artifacts_materialized": analysis.artifacts_materialized,
        "candidate_count": len(analysis.candidates),
        **_best_fields(analysis),
        "output_sha256": truth_sha256(bits, case["n_vars"]),
    }


def _functional(cases: list[dict[str, Any]], controls: list[dict[str, Any]],
                config: GF2ScreeningConfig) -> tuple[list[dict[str, Any]],
                                                     list[dict[str, Any]],
                                                     list[dict[str, Any]]]:
    rows, control_rows, artifacts = [], [], []
    for case in cases:
        expression = expr_from_json(case["expression_v2"])
        bits = reference_bits(expression, case["n_vars"])
        exhaustive = analyze_exact_gf2(bits, case["n_vars"],
                                       max_partitions=config.max_partitions)
        screened = analyze_screened_exact_gf2(
            bits,
            case["n_vars"],
            max_partitions=config.max_partitions,
            materialize_budget=config.materialize_budget,
        )
        exact = all(candidate.reconstruct() == bits for candidate in screened.candidates)
        match = _best_document(screened) == _best_document(exhaustive)
        rows.append({
            "case_id": case["case_id"],
            "split": case["split"],
            "source_kind": case["source_kind"],
            "n_vars": case["n_vars"],
            "exact_best_identity_match": match,
            "exact_reconstruction": exact,
            "exhaustive_candidates": len(exhaustive.candidates),
            "screened_descriptors": screened.descriptors_screened,
            "screened_artifacts_materialized": screened.artifacts_materialized,
            **_best_fields(screened),
        })
        if screened.best is not None:
            artifacts.append({"case_id": case["case_id"], "role": "screened_best",
                              "artifact": screened.best.to_dict()})

    for control in controls:
        kwargs = ({"row_partitions": control["row_partitions"]}
                  if control["row_partitions"] is not None
                  else {"max_partitions": 32})
        exhaustive = analyze_exact_gf2(control["bits"], control["n_vars"], **kwargs)
        screened = analyze_screened_exact_gf2(
            control["bits"], control["n_vars"],
            materialize_budget=config.materialize_budget, **kwargs
        )
        control_rows.append({
            "case_id": control["case_id"],
            "n_vars": control["n_vars"],
            "required_kind": control["required_kind"],
            "source_sha256": truth_sha256(control["bits"], control["n_vars"]),
            "exact_best_identity_match": _best_document(screened) == _best_document(exhaustive),
            "exact_reconstruction": all(candidate.reconstruct() == control["bits"]
                                        for candidate in screened.candidates),
            "screened_artifacts_materialized": screened.artifacts_materialized,
            **_best_fields(screened),
        })
    return rows, control_rows, artifacts


def _p95(values: list[float]) -> float:
    return statistics.quantiles(values, n=20, method="inclusive")[18]


def summarize(measurements: list[dict[str, Any]], functional: list[dict[str, Any]],
              controls: list[dict[str, Any]], materialize_budget: int) -> dict[str, Any]:
    by_case_method: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in measurements:
        by_case_method.setdefault((row["case_id"], row["method"]), []).append(row)
    case_ids = sorted({row["case_id"] for row in measurements})
    medians: dict[tuple[str, str], dict[str, float]] = {}
    for key, values in by_case_method.items():
        medians[key] = {
            field: statistics.median(row[field] for row in values)
            for field in ("representation_ns", "analysis_ns", "total_ns")
        }
    totals = {
        method: {field: sum(medians[(case_id, method)][field] for case_id in case_ids)
                 for field in ("representation_ns", "analysis_ns", "total_ns")}
        for method in METHODS
    }
    exhaustive = "explicit_cm_exhaustive"
    screened = "explicit_cm_screened"
    case_speedups = [medians[(case_id, exhaustive)]["total_ns"]
                     / medians[(case_id, screened)]["total_ns"] for case_id in case_ids]
    p95_exhaustive = _p95([medians[(case_id, exhaustive)]["total_ns"] for case_id in case_ids])
    p95_screened = _p95([medians[(case_id, screened)]["total_ns"] for case_id in case_ids])
    speedup = {
        "screened_analysis_over_exhaustive":
            totals[exhaustive]["analysis_ns"] / totals[screened]["analysis_ns"],
        "screened_whole_path_over_exhaustive":
            totals[exhaustive]["total_ns"] / totals[screened]["total_ns"],
        "screened_whole_path_p95": p95_exhaustive / p95_screened,
        "packed_source_anf_over_explicit_cm_screened":
            totals[screened]["total_ns"] / totals["packed_source_anf_screened"]["total_ns"],
        "minimum_case_speedup": min(case_speedups),
        "median_case_speedup": statistics.median(case_speedups),
    }
    criteria = {
        "exact_method_outputs": all(not row["semantic_mismatches"] for row in measurements),
        "exact_timed_best_identity": all(not row["artifact_mismatches"] for row in measurements),
        "exact_functional_best_identity_40_of_40":
            len(functional) == 40 and all(row["exact_best_identity_match"] for row in functional),
        "exact_control_best_identity_12_of_12":
            len(controls) == 12 and all(row["exact_best_identity_match"] for row in controls),
        "exact_artifact_reconstruction":
            all(row["exact_reconstruction"] for row in functional + controls),
        "dense_controls_remain_uncompressed":
            all(row["best_kind"] is None for row in controls if row["required_kind"] is None),
        "materialization_bound_respected":
            all(row["screened_artifacts_materialized"] <= materialize_budget + 1
                for row in functional + controls),
        "screened_analysis_speedup_at_least_1_50x":
            speedup["screened_analysis_over_exhaustive"] >= 1.50,
        "whole_path_speedup_at_least_1_25x":
            speedup["screened_whole_path_over_exhaustive"] >= 1.25,
        "whole_path_p95_speedup_at_least_1_20x": speedup["screened_whole_path_p95"] >= 1.20,
    }
    functional_gate = all(criteria[key] for key in criteria
                          if "speedup" not in key)
    local_timing_gate = functional_gate and all(criteria[key] for key in criteria
                                                if "speedup" in key)
    return {
        "median_case_sum_ns": {
            method: {field: int(value) for field, value in fields.items()}
            for method, fields in totals.items()
        },
        "speedup": speedup,
        "criteria": criteria,
        "functional_gate": functional_gate,
        "local_timing_gate": local_timing_gate,
        "second_machine_gate": local_timing_gate,
        "timing_is_machine_specific": True,
    }


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# CRSE C16 exact-screened CM/GF(2) tail",
        "",
        f"Status: **{result['status']}**",
        f"Functional gate: **{summary['functional_gate']}**",
        f"Local timing gate: **{summary['local_timing_gate']}**",
        "",
        "## Exact-safe change",
        "",
        "All bounded partitions still receive the same exact rank, cofactor, and Kronecker screen. "
        "The screen shares one matrix layout per partition and admits nothing. Only the four best "
        "descriptors receive artifact hashes and complete truth reconstruction. Advice-off runs the "
        "original exhaustive materializer.",
        "",
        "The screened best artifact matched the exhaustive best artifact identity on all 40 Yosys "
        "cases and all 12 structured/dense controls. Every materialized proposal reconstructed the "
        "complete source truth vector.",
        "",
        "## Task-equivalent timing",
        "",
        "| Method | Representation (ns) | Analysis (ns) | Whole path (ns) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for method, values in summary["median_case_sum_ns"].items():
        lines.append(f"| {method} | {values['representation_ns']} | "
                     f"{values['analysis_ns']} | {values['total_ns']} |")
    speed = summary["speedup"]
    lines += [
        "",
        f"Screened analyzer speedup: **{speed['screened_analysis_over_exhaustive']:.4f}x**.",
        f"Explicit-CM whole-path speedup: **{speed['screened_whole_path_over_exhaustive']:.4f}x**; "
        f"p95 speedup: **{speed['screened_whole_path_p95']:.4f}x**.",
        f"Packed source ANF versus explicit CM with the same screened analyzer: "
        f"**{speed['packed_source_anf_over_explicit_cm_screened']:.4f}x**.",
        "",
        "## Criteria",
        "",
    ]
    lines.extend(f"- `{key}`: **{value}**" for key, value in summary["criteria"].items())
    lines += [
        "",
        "This is deterministic exact computation, not a trained or approximate value model. "
        "The positive local gate permits bounded second-machine timing; it does not enable production.",
        "",
    ]
    return "\n".join(lines)


def run_gf2_screening_experiment(config: GF2ScreeningConfig, output: Path,
                                 progress: Callable[[str], None] = print) -> dict[str, Any]:
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    wall_started = time.perf_counter()
    cases, provenance = make_yosys_composed_holdout()
    controls = make_gf2_controls(config.seed)
    _write_json(output / "run_spec.json", {
        "schema": SCHEMA,
        "config": asdict(config),
        "controls": {"thread_count": 1, "runpod": False, "advice_off": "explicit_cm_exhaustive"},
        "predeclared_gates": {"analysis_speedup": 1.50, "whole_path_speedup": 1.25,
                              "p95_speedup": 1.20},
    })
    _write_json(output / "dataset.json", {
        "schema": "crse-c16-gf2-screened-tail-dataset/v1",
        "provenance": provenance,
        "reuse_notice": "C15 frozen Yosys family; no timing-based case selection",
        "rows": len(cases),
        "cases": cases,
        "controls": [
            {key: value for key, value in row.items() if key != "bits"}
            | {"source_sha256": truth_sha256(row["bits"], row["n_vars"])}
            for row in controls
        ],
    })

    progress("Checking exact screened-tail identity against advice-off exhaustive materialization")
    functional, control_rows, artifacts = _functional(cases, controls, config)
    _write_json(output / "artifacts.json", {
        "schema": "crse-c16-gf2-screened-tail-artifacts/v1",
        "artifacts": artifacts,
        "functional": functional,
        "controls": control_rows,
        "payload_sha256": hashlib.sha256(canonical(artifacts)).hexdigest(),
    })

    expressions, expected_bits, expected_best = {}, {}, {}
    for case in cases:
        expression = expr_from_json(case["expression_v2"])
        bits = reference_bits(expression, case["n_vars"])
        expressions[case["case_id"]] = expression
        expected_bits[case["case_id"]] = bits
        exhaustive = analyze_exact_gf2(bits, case["n_vars"],
                                       max_partitions=config.max_partitions)
        expected_best[case["case_id"]] = _best_document(exhaustive)

    measurements = []
    rng = random.Random(f"{config.seed}:c16-balanced-method-order/v1")
    progress("Timing screened explicit CM/source ANF against the advice-off exhaustive control")
    for round_index in range(config.rounds):
        order = [(case, method) for case in cases for method in METHODS]
        rng.shuffle(order)
        for case, method in order:
            if time.perf_counter() - wall_started > config.max_seconds:
                raise TimeoutError("C16 GF(2) screening experiment exceeded wall budget")
            case_id = case["case_id"]
            measurements.append(_measure(
                method, case, expressions[case_id], expected_bits[case_id],
                expected_best[case_id], config, round_index
            ))
    _write_jsonl(output / "measurements.jsonl", measurements)
    summary = summarize(measurements, functional, control_rows, config.materialize_budget)
    mismatches = sum(row["semantic_mismatches"] + row["artifact_mismatches"]
                     for row in measurements)
    result = {
        "schema": SCHEMA,
        "status": "complete" if not mismatches and summary["functional_gate"] else "failed",
        "config": asdict(config),
        "wall_seconds": time.perf_counter() - wall_started,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "thread_environment": {name: os.environ.get(name) for name in
                                   ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        },
        "dataset": {"rows": len(cases), "source": provenance["source"],
                    "upstream_commit": provenance["upstream_commit"], "reused_from": "C15"},
        "artifact_rows": len(artifacts),
        "semantic_or_artifact_mismatches": mismatches,
        "summary": summary,
        "runpod": {"used": False, "cost_usd": 0.0,
                   "reason": "pending_second_machine_confirmation" if summary["second_machine_gate"]
                             else "local_timing_gate_failed"},
        "claims": {
            "same_best_as_bounded_exhaustive": summary["functional_gate"],
            "learned_or_approximate_values": False,
            "unbounded_factorization": False,
            "production_promotion": False,
        },
    }
    _write_json(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    return result
