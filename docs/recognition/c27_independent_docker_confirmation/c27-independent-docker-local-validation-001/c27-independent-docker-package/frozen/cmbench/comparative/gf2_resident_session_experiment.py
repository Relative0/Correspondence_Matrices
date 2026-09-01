"""C25 repeated-query evaluation of resident frozen C22 portfolio sessions."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time
import tracemalloc
from typing import Any

from cmbench.recognition.gf2_decomposition import ExactGF2Artifact
from cmbench.recognition.gf2_source_portfolio import load_source_portfolio_policy
from cmbench.recognition.gf2_source_portfolio_session import (
    ResidentSourcePortfolioSession,
    verify_resident_query_result,
)
from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE
from cmbench.recognition.gf2_work_policy import load_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy
from cmbench.recognition.yosys_unused_gf2_data import validate_dataset

from .contracts import canonical_bytes
from .gf2_decomposition import decomposition_contract, delivered_document, delivered_sha256
from .gf2_source_portfolio_experiment import execute_benchmark_method
from .gf2_table_experiment import C21Config, build_oracles

SCHEMA = "crse-c25-resident-c22-session-experiment/v1"
METHODS = (
    "resident_direct_exhaustive",
    "resident_direct_screened",
    "resident_direct_compiled_screened",
    "resident_direct_source_packed",
    "resident_c22_advice_on",
    "resident_c22_advice_off",
)
DIRECT_METHODS = {
    "resident_direct_exhaustive": "direct_exhaustive",
    "resident_direct_screened": "direct_screened",
    "resident_direct_compiled_screened": "direct_compiled_screened",
    "resident_direct_source_packed": "direct_source_packed",
}
QUERY_COUNTS = (1, 2, 4, 8, 16, 32)
N_VARS = (3, 4, 5, 6)
BATCH_TIMING_FIELDS = ("setup_ns", "queries_ns", "close_ns", "wrapper_ns")


@dataclass(frozen=True)
class C25Config:
    run_id: str
    seed: int = 20260831
    rounds: int = 5
    query_counts: tuple[int, ...] = QUERY_COUNTS
    max_partitions: int = 64
    materialize_budget: int = 4
    memory_query_count: int = 8
    max_seconds: float = 1200.0

    def validate(self) -> None:
        if (
            not self.run_id
            or type(self.rounds) is not int
            or not 3 <= self.rounds <= 7
            or tuple(self.query_counts) != QUERY_COUNTS
            or self.max_partitions != 64
            or self.materialize_budget != 4
            or self.memory_query_count != 8
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 180 <= self.max_seconds <= 1800
        ):
            raise ValueError("invalid C25 experiment bounds")

    def oracle_config(self) -> C21Config:
        return C21Config(
            run_id=self.run_id,
            rounds=max(3, self.rounds),
            max_partitions=self.max_partitions,
            materialize_budget=self.materialize_budget,
            memory_cases_per_width=1,
            max_seconds=self.max_seconds,
        )


def _write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def case_sequence(cases_by_width: dict[int, list[dict[str, Any]]], n_vars: int,
                  query_count: int, round_index: int) -> list[dict[str, Any]]:
    group = cases_by_width[n_vars]
    start = (round_index * 5 + query_count) % len(group)
    return [group[(start + index) % len(group)] for index in range(query_count)]


def _resident_query(session: ResidentSourcePortfolioSession, case: dict[str, Any],
                    required_best: dict[str, Any] | None) -> dict[str, Any]:
    started = time.perf_counter_ns()
    result = session.execute(case).to_dict()
    verify_resident_query_result(
        result, case, policy_sha256=session.policy["policy_sha256"], required_best=required_best)
    delivered = canonical_bytes(delivered_document(result["best_artifact"]))
    artifact_sha256 = hashlib.sha256(delivered).hexdigest()
    exact = (
        result["status"] == "ok"
        and result["exact_check_passed"] is True
        and result["best_artifact"] == required_best
        and artifact_sha256 == delivered_sha256(required_best)
        and (required_best is None or ExactGF2Artifact.from_dict(required_best).reconstruct()
             == int(case["truth_bits_hex"], 16))
    )
    if not exact:
        raise RuntimeError("C25 resident query failed exact delivery")
    return {
        "elapsed_ns": max(1, time.perf_counter_ns() - started),
        "case_id": case["case_id"],
        "artifact_sha256": artifact_sha256,
        "best_artifact_sha256": required_best["payload_sha256"] if required_best else None,
        "selected_arm": result["selected_arm"],
        "compile_cache_hit": result["compile_cache_hit"],
        "exact_check_passed": True,
    }


def execute_batch(*, session_id: str, method: str, cases: list[dict[str, Any]],
                  contracts: dict[str, Any], oracles: dict[str, Any],
                  c22_policy_path: Path, c19_policy_path: Path,
                  max_partitions: int, materialize_budget: int) -> dict[str, Any]:
    if method not in METHODS or not cases:
        raise ValueError("invalid C25 batch")
    total_started = time.perf_counter_ns()
    started = time.perf_counter_ns()
    session = None
    compiled = None
    if method == "resident_c22_advice_on":
        session = ResidentSourcePortfolioSession(
            session_id, c22_policy_path, advice_enabled=True, max_queries=len(cases))
        setup_detail = session.snapshot()["setup_timings_ns"]
    elif method == "resident_c22_advice_off":
        session = ResidentSourcePortfolioSession(
            session_id, c22_policy_path, advice_enabled=False, max_queries=len(cases))
        setup_detail = session.snapshot()["setup_timings_ns"]
    elif method == "resident_direct_compiled_screened":
        compiled = compile_work_policy(load_policy(c19_policy_path))
        setup_detail = {"frozen_c19_policy_load_and_compile": True}
    else:
        setup_detail = {"stateless_direct_session": True}
    setup_ns = max(1, time.perf_counter_ns() - started)

    query_records = []
    queries_ns = 0
    for case in cases:
        required_best = oracles[case["case_id"]]["best_artifact"]
        if session is not None:
            query = _resident_query(session, case, required_best)
        else:
            execution = execute_benchmark_method(
                case=case,
                contract=contracts[case["case_id"]],
                method=DIRECT_METHODS[method],
                required_best=required_best,
                policy_path=c22_policy_path,
                compiled_policy=compiled,
                max_partitions=max_partitions,
                materialize_budget=materialize_budget,
            )
            query = {
                "elapsed_ns": execution["timings_ns"]["task_total_ns"],
                "case_id": case["case_id"],
                "artifact_sha256": execution["artifact_sha256"],
                "best_artifact_sha256": execution["best_artifact_sha256"],
                "selected_arm": execution["selected_arm"],
                "compile_cache_hit": None,
                "exact_check_passed": execution["exact_check_passed"],
            }
        queries_ns += query["elapsed_ns"]
        query_records.append(query)

    started = time.perf_counter_ns()
    if session is not None:
        before_close = session.snapshot()
        closed = session.close()
        if not closed["closed"] or closed["successful_queries"] != len(cases):
            raise RuntimeError("C25 session close invariant failed")
    else:
        before_close = None
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
        "method": method,
        "query_count": len(cases),
        "timings_ns": timings,
        "amortized_query_ns": timings["batch_total_ns"] / len(cases),
        "query_records": query_records,
        "setup_detail": setup_detail,
        "session_snapshot": before_close,
        "exact_check_passed": all(row["exact_check_passed"] for row in query_records),
    }


def _median_batches(rows: list[dict[str, Any]]):
    grouped = {}
    for row in rows:
        grouped.setdefault((row["n_vars"], row["query_count"], row["method"]), []).append(row)
    return {
        key: {
            field: int(statistics.median(row["timings_ns"][field] for row in values))
            for field in (*BATCH_TIMING_FIELDS, "batch_total_ns")
        }
        for key, values in grouped.items()
    }


def summarize(rows: list[dict[str, Any]], memory_rows: list[dict[str, Any]],
              controls: dict[str, Any]) -> dict[str, Any]:
    medians = _median_batches(rows)
    by_query_count = {}
    for query_count in QUERY_COUNTS:
        method_rows = {}
        baselines = {
            name: {n: medians[(n, query_count, name)]["batch_total_ns"] for n in N_VARS}
            for name in (
                "resident_direct_exhaustive",
                "resident_direct_screened",
                "resident_direct_source_packed",
            )
        }
        for method in METHODS:
            selected = {n: medians[(n, query_count, method)]["batch_total_ns"] for n in N_VARS}
            method_rows[method] = {
                "aggregate_speedup_over_direct_exhaustive": (
                    sum(baselines["resident_direct_exhaustive"].values()) / sum(selected.values())),
                "aggregate_speedup_over_direct_screened": (
                    sum(baselines["resident_direct_screened"].values()) / sum(selected.values())),
                "aggregate_speedup_over_direct_source_packed": (
                    sum(baselines["resident_direct_source_packed"].values()) / sum(selected.values())),
                "minimum_width_speedup_over_direct_screened": min(
                    baselines["resident_direct_screened"][n] / selected[n] for n in N_VARS),
                "aggregate_amortized_query_ns": sum(selected.values()) / (len(N_VARS) * query_count),
                "median_width_setup_ns": int(statistics.median(
                    medians[(n, query_count, method)]["setup_ns"] for n in N_VARS)),
            }
        best = min(METHODS, key=lambda method: (
            sum(medians[(n, query_count, method)]["batch_total_ns"] for n in N_VARS), method))
        by_query_count[str(query_count)] = {
            "methods": method_rows,
            "best_fixed_method": best,
        }
    advice_break_even = next((
        query_count for query_count in QUERY_COUNTS
        if by_query_count[str(query_count)]["methods"]["resident_c22_advice_on"]
        ["aggregate_speedup_over_direct_screened"] >= 1.0
        and by_query_count[str(query_count)]["methods"]["resident_c22_advice_on"]
        ["minimum_width_speedup_over_direct_screened"] >= 0.90
    ), None)
    memory = {}
    for method in METHODS:
        peaks = [row["peak_bytes"] for row in memory_rows if row["method"] == method]
        memory[method] = {
            "peak_bytes_median": int(statistics.median(peaks)) if peaks else None,
            "peak_bytes_maximum": max(peaks) if peaks else None,
        }
    return {
        "exactness_gate": all(row["exact_check_passed"] for row in rows),
        "functional_control_gate": controls.get("all_passed") is True,
        "query_counts": list(QUERY_COUNTS),
        "by_query_count": by_query_count,
        "advice_on_break_even_query_count": advice_break_even,
        "resident_promotion_gate": controls.get("all_passed") is True and advice_break_even is not None,
        "resident_promotion_gate_contract": {
            "all_controls_pass": True,
            "aggregate_vs_direct_screened_minimum": 1.0,
            "minimum_width_vs_direct_screened_minimum": 0.90,
            "maximum_query_count": max(QUERY_COUNTS),
        },
        "memory": memory,
        "timing_is_retrospective_and_machine_specific": True,
    }


def _run_controls(cases: list[dict[str, Any]], oracles: dict[str, Any],
                  c22_policy_path: Path, output: Path) -> dict[str, Any]:
    fallback_session = ResidentSourcePortfolioSession(
        "c25-fallback-control", c22_policy_path, max_queries=len(cases))
    fallback = []
    for case in cases:
        result = fallback_session.execute(case, force_source_refusal=True).to_dict()
        verify_resident_query_result(
            result, case, policy_sha256=fallback_session.policy["policy_sha256"],
            required_best=oracles[case["case_id"]]["best_artifact"])
        fallback.append({
            "case_id": case["case_id"],
            "status": result["status"],
            "selected_arm": result["selected_arm"],
            "fallback_used": result["fallback_used"],
            "exact_check_passed": result["exact_check_passed"],
            "artifact_sha256": result["artifact_sha256"],
        })
    fallback_session.close()

    seed_case = json.loads(json.dumps(cases[0]))
    session = ResidentSourcePortfolioSession("c25-refusal-control", c22_policy_path, max_queries=1)
    mismatch = json.loads(json.dumps(seed_case))
    mismatch["truth_bits_hex"] = hex(int(mismatch["truth_bits_hex"], 16) ^ 1)
    ood = json.loads(json.dumps(seed_case))
    ood["n_vars"] = 7
    mismatch_result = session.execute(mismatch).to_dict()
    ood_result = session.execute(ood).to_dict()
    session.close()
    closed_result = session.execute(seed_case).to_dict()
    for document, case in ((mismatch_result, mismatch), (ood_result, ood), (closed_result, seed_case)):
        verify_resident_query_result(
            document, case, policy_sha256=session.policy["policy_sha256"])

    limit = ResidentSourcePortfolioSession("c25-limit-control", c22_policy_path, max_queries=1)
    accepted = limit.execute(seed_case).to_dict()
    verify_resident_query_result(
        accepted, seed_case, policy_sha256=limit.policy["policy_sha256"],
        required_best=oracles[seed_case["case_id"]]["best_artifact"])
    limit_result = limit.execute(seed_case).to_dict()
    verify_resident_query_result(
        limit_result, seed_case, policy_sha256=limit.policy["policy_sha256"])

    policy = load_source_portfolio_policy(c22_policy_path)
    tampered = dict(policy)
    tampered["selected_arm"] = EXHAUSTIVE
    tampered_path = output / "control_policy_tampered.json"
    _write(tampered_path, tampered)
    try:
        ResidentSourcePortfolioSession("c25-tampered", tampered_path)
    except ValueError:
        tampered_refused = True
    else:
        tampered_refused = False
    refusal_rows = [
        {"control_id": "truth_mismatch", "status": mismatch_result["status"]},
        {"control_id": "unsupported_n7", "status": ood_result["status"]},
        {"control_id": "closed_session", "status": closed_result["status"]},
        {"control_id": "query_limit", "status": limit_result["status"]},
        {"control_id": "tampered_policy_at_setup", "status": "refused" if tampered_refused else "accepted"},
    ]
    fallback_pass = all(
        row["status"] == "ok"
        and row["selected_arm"] == EXHAUSTIVE
        and row["fallback_used"] is True
        and row["exact_check_passed"] is True
        for row in fallback
    )
    refusal_pass = all(row["status"] == "refused" for row in refusal_rows)
    return {
        "schema": "crse-c25-resident-session-controls/v1",
        "fallback_cases": fallback,
        "refusal_cases": refusal_rows,
        "fallback_cases_checked": len(fallback),
        "refusal_cases_checked": len(refusal_rows),
        "fallback_gate": fallback_pass,
        "refusal_gate": refusal_pass,
        "all_passed": fallback_pass and refusal_pass,
    }


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# C25 resident C22 repeated-query evaluation",
        "",
        f"Status: **{result['status']}**  ",
        f"Resident promotion gate: **{'pass' if summary['resident_promotion_gate'] else 'fail'}**  ",
        f"Advice-on break-even query count: **{summary['advice_on_break_even_query_count']}**",
        "",
        "Each batch charged session setup, every exact query and delivered response, session close,",
        "and wrapper work. C22 reused one validated immutable policy and one compiled portfolio per",
        "support width. Direct controls used the same query sequence and exact artifacts.",
        "",
        "| Queries | C22 advice on vs screened | Minimum width vs screened | Best fixed method |",
        "|---:|---:|---:|---|",
    ]
    for query_count in QUERY_COUNTS:
        row = summary["by_query_count"][str(query_count)]
        advice = row["methods"]["resident_c22_advice_on"]
        lines.append(
            f"| {query_count} | {advice['aggregate_speedup_over_direct_screened']:.4f}x | "
            f"{advice['minimum_width_speedup_over_direct_screened']:.4f}x | "
            f"{row['best_fixed_method']} |"
        )
    lines += [
        "",
        "The functional gate contains exact forced fallback on all 48 cases and refusal controls",
        "for truth mismatch, unsupported width, closed session, query limit, and tampered policy.",
        "Production promotion remains false.",
    ]
    return "\n".join(lines) + "\n"


def run(config: C25Config, output: Path, dataset_path: Path,
        dataset_verification_path: Path, c22_policy_path: Path,
        c19_policy_path: Path, root: Path) -> dict[str, Any]:
    config.validate()
    wall_started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset_verification = json.loads(dataset_verification_path.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    if (
        len(dataset.get("cases", [])) != 48
        or dataset.get("revision", {}).get("id") != "task-complete-v2"
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 48
        or dataset_verification.get("expression_truth_mismatches") != 0
    ):
        raise ValueError("C25 requires the sealed verified C23 corpus")
    c22_policy = load_source_portfolio_policy(c22_policy_path)
    c19_policy = load_policy(c19_policy_path)
    compiled = compile_work_policy(c19_policy)
    if (
        c22_policy["selected_arm"] != "source_packed_anf_screened"
        or c22_policy["training_use"] is not False
        or compiled.mode != "constant_leaf"
        or compiled.constant_arm != "explicit_cm_screened"
    ):
        raise ValueError("C25 frozen policy contract changed")
    _write(output / "run_spec.json", {
        "schema": SCHEMA,
        "config": {**asdict(config), "query_counts": list(config.query_counts)},
        "dataset_path": _rel(dataset_path, root),
        "dataset_sha256": _sha256(dataset_path),
        "dataset_verification_path": _rel(dataset_verification_path, root),
        "dataset_verification_sha256": _sha256(dataset_verification_path),
        "c22_policy_path": _rel(c22_policy_path, root),
        "c22_policy_file_sha256": _sha256(c22_policy_path),
        "c22_policy_sha256": c22_policy["policy_sha256"],
        "c19_policy_path": _rel(c19_policy_path, root),
        "c19_policy_file_sha256": _sha256(c19_policy_path),
        "c19_policy_sha256": c19_policy["policy_sha256"],
        "methods": list(METHODS),
        "lifecycle": "resident_bounded_repeated_query",
        "per_query_input_validation": True,
        "per_query_exact_delivery_verification": True,
        "immutable_policy_reuse": True,
        "compiled_state_reuse_by_support_width": True,
        "policy_refit": False,
        "production_promotion": False,
    })
    cases = dataset["cases"]
    functional, oracles = build_oracles(cases, config.oracle_config())
    if not functional["all_exact"]:
        raise RuntimeError("C25 exhaustive oracle replay failed")
    _write(output / "functional.json", functional)
    _write(output / "oracles.json", oracles)
    contracts = {
        case["case_id"]: decomposition_contract(
            contract_id=f"c25-{case['case_id']}", n_vars=case["n_vars"],
            required_output_sha256=oracles[case["case_id"]]["delivered_sha256"])
        for case in cases
    }
    _write(output / "contracts.json", contracts)
    controls = _run_controls(cases, oracles, c22_policy_path, output)
    if not controls["all_passed"]:
        raise RuntimeError("C25 functional controls failed")
    _write(output / "functional_controls.json", controls)

    cases_by_width = {
        n_vars: sorted(
            (case for case in cases if case["n_vars"] == n_vars),
            key=lambda case: (case["truth_sha256"], case["case_id"]),
        )
        for n_vars in N_VARS
    }
    if any(not group for group in cases_by_width.values()):
        raise ValueError("C25 requires at least one sealed case per support width")
    rng = random.Random(f"{config.seed}:c25-balanced/v1")
    rows = []
    for round_index in range(config.rounds):
        order = [(n_vars, count, method) for n_vars in N_VARS
                 for count in QUERY_COUNTS for method in METHODS]
        rng.shuffle(order)
        for n_vars, query_count, method in order:
            if time.perf_counter() - wall_started > config.max_seconds:
                raise TimeoutError("C25 experiment exceeded wall bound")
            sequence = case_sequence(cases_by_width, n_vars, query_count, round_index)
            execution = execute_batch(
                session_id=f"c25-r{round_index}-n{n_vars}-q{query_count}-{method}",
                method=method,
                cases=sequence,
                contracts=contracts,
                oracles=oracles,
                c22_policy_path=c22_policy_path,
                c19_policy_path=c19_policy_path,
                max_partitions=config.max_partitions,
                materialize_budget=config.materialize_budget,
            )
            rows.append({
                "round": round_index,
                "n_vars": n_vars,
                "query_count": query_count,
                **execution,
            })
    _write_jsonl(output / "measurements.jsonl", rows)

    memory_rows = []
    for n_vars in N_VARS:
        sequence = case_sequence(cases_by_width, n_vars, config.memory_query_count, 0)
        for method in METHODS:
            tracemalloc.start()
            try:
                execution = execute_batch(
                    session_id=f"c25-memory-n{n_vars}-{method}",
                    method=method,
                    cases=sequence,
                    contracts=contracts,
                    oracles=oracles,
                    c22_policy_path=c22_policy_path,
                    c19_policy_path=c19_policy_path,
                    max_partitions=config.max_partitions,
                    materialize_budget=config.materialize_budget,
                )
                current, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            memory_rows.append({
                "n_vars": n_vars,
                "query_count": config.memory_query_count,
                "method": method,
                "current_bytes": current,
                "peak_bytes": peak,
                "exact_check_passed": execution["exact_check_passed"],
            })
    _write_jsonl(output / "memory_measurements.jsonl", memory_rows)
    summary = summarize(rows, memory_rows, controls)
    mismatches = sum(not row["exact_check_passed"] for row in rows)
    result = {
        "schema": SCHEMA,
        "status": "complete" if mismatches == 0 and controls["all_passed"] else "failed",
        "config": {**asdict(config), "query_counts": list(config.query_counts)},
        "wall_seconds": time.perf_counter() - wall_started,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "dd_version": importlib.metadata.version("dd"),
            "thread_environment": {
                name: os.environ.get(name)
                for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
            },
        },
        "dataset": {
            "cases": len(cases),
            "families": dataset["counts"]["families"],
            "n_vars": list(N_VARS),
            "retrospective_resident_evaluation": True,
            "policy_refit": False,
        },
        "measurement_batches": len(rows),
        "timed_queries": sum(row["query_count"] for row in rows),
        "memory_measurement_batches": len(memory_rows),
        "fallback_controls": controls["fallback_cases_checked"],
        "refusal_controls": controls["refusal_cases_checked"],
        "semantic_or_artifact_mismatches": mismatches,
        "summary": summary,
        "claims": {
            "unchanged_c22_policy": True,
            "resident_policy_and_compiled_state_reused": True,
            "every_query_exactly_verified": True,
            "fallback_and_refusal_controls_passed": controls["all_passed"],
            "fresh_confirmation": False,
            "production_promotion": False,
        },
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    sources = (
        "cmbench/comparative/gf2_resident_session_experiment.py",
        "cmbench/comparative/gf2_source_portfolio_experiment.py",
        "cmbench/recognition/gf2_source_portfolio.py",
        "cmbench/recognition/gf2_source_portfolio_session.py",
        "scripts/cm_comparative_c25_resident_session.py",
    )
    artifacts = (
        "run_spec.json", "functional.json", "oracles.json", "contracts.json",
        "control_policy_tampered.json", "functional_controls.json", "measurements.jsonl",
        "memory_measurements.jsonl", "results.json", "report.md",
    )
    _write(output / "manifest.json", {
        "schema": "crse-c25-run-manifest/v1",
        "dataset_sha256": _sha256(dataset_path),
        "dataset_verification_sha256": _sha256(dataset_verification_path),
        "c22_policy_file_sha256": _sha256(c22_policy_path),
        "c19_policy_file_sha256": _sha256(c19_policy_path),
        "sources": {name: _sha256(root / name) for name in sources},
        "artifacts": {name: _sha256(output / name) for name in artifacts},
    })
    return result
