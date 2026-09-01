"""C27 fresh confirmation of the frozen support-aware exact GF(2) session."""
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
import random
import statistics
import sys
import time
import tracemalloc
from typing import Any

from cmbench.recognition.gf2_support_aware_session import (
    SupportAwareGF2Session,
)
from cmbench.recognition.gf2_source_portfolio import load_source_portfolio_policy
from cmbench.recognition.gf2_support_aware_policy import (
    TRUTH_SCREENED, load_support_aware_policy, select_support_arm,
)
from cmbench.recognition.gf2_task_dispatcher import EXHAUSTIVE
from cmbench.recognition.gf2_verified_context import (
    build_verified_gf2_context,
    verify_verified_gf2_context,
)
from cmbench.recognition.gf2_work_policy import load_policy
from cmbench.recognition.gf2_work_policy_compiler import compile_work_policy
from cmbench.recognition.yosys_c27_gf2_data import validate_dataset

from .contracts import canonical_bytes
from .gf2_decomposition import decomposition_contract, delivered_document, delivered_sha256
from .gf2_resident_session_experiment import (
    BATCH_TIMING_FIELDS,
    N_VARS,
    QUERY_COUNTS,
    case_sequence,
    execute_batch as execute_c25_direct_batch,
)
from .gf2_table_experiment import C21Config, build_oracles

SCHEMA = "crse-c27-support-aware-fresh-confirmation-experiment/v1"
METHODS = (
    "resident_direct_exhaustive",
    "resident_direct_screened",
    "resident_direct_compiled_screened",
    "resident_direct_source_packed",
    "support_aware_c27_advice_on",
    "support_aware_c27_advice_off",
)
DIRECT_METHODS = frozenset(METHODS[:4])


@dataclass(frozen=True)
class C27Config:
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
            raise ValueError("invalid C27 experiment bounds")

    def oracle_config(self) -> C21Config:
        return C21Config(
            run_id=self.run_id, rounds=max(3, self.rounds),
            max_partitions=self.max_partitions,
            materialize_budget=self.materialize_budget,
            memory_cases_per_width=1, max_seconds=self.max_seconds)


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


def _support_aware_query(session: SupportAwareGF2Session,
                         case: dict[str, Any],
                         required_best: dict[str, Any] | None) -> dict[str, Any]:
    started = time.perf_counter_ns()
    result = session.execute(case).to_dict()
    delivered = canonical_bytes(delivered_document(result["best_artifact"]))
    delivered_digest = hashlib.sha256(delivered).hexdigest()
    if (
        result["status"] != "ok"
        or result["exact_check_passed"] is not True
        or result["best_artifact"] != required_best
        or delivered_digest != delivered_sha256(required_best)
    ):
        raise RuntimeError("C27 support-aware query failed exact delivery")
    return {
        "elapsed_ns": max(1, time.perf_counter_ns() - started),
        "case_id": case["case_id"],
        "context_sha256": result["context_sha256"],
        "expression_sha256": result["expression_sha256"],
        "truth_sha256": result["truth_sha256"],
        "artifact_sha256": delivered_digest,
        "best_artifact_sha256": required_best["payload_sha256"] if required_best else None,
        "selected_arm": result["selected_arm"],
        "compile_cache_hit": result["plan_cache_hit"],
        "partitions_tested": result["partitions_tested"],
        "descriptors_screened": result["descriptors_screened"],
        "artifacts_materialized": result["artifacts_materialized"],
        "exact_check_passed": True,
    }


def execute_support_aware_batch(
    *, session_id: str, method: str, cases: list[dict[str, Any]],
    oracles: dict[str, Any], c27_policy_path: Path, c22_policy_path: Path,
) -> dict[str, Any]:
    if method not in {"support_aware_c27_advice_on", "support_aware_c27_advice_off"} or not cases:
        raise ValueError("invalid C27 support-aware batch")
    total_started = time.perf_counter_ns()
    started = time.perf_counter_ns()
    session = SupportAwareGF2Session(
        session_id,
        c27_policy_path,
        c22_policy_path,
        advice_enabled=method == "support_aware_c27_advice_on",
        max_queries=len(cases),
    )
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
        raise RuntimeError("C27 support-aware session close invariant failed")
    close_ns = max(1, time.perf_counter_ns() - started)
    elapsed = max(1, time.perf_counter_ns() - total_started)
    wrapper_ns = max(0, elapsed - setup_ns - queries_ns - close_ns)
    timings = {"setup_ns": setup_ns, "queries_ns": queries_ns,
               "close_ns": close_ns, "wrapper_ns": wrapper_ns}
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
        key: {field: int(statistics.median(row["timings_ns"][field] for row in values))
              for field in (*BATCH_TIMING_FIELDS, "batch_total_ns")}
        for key, values in grouped.items()
    }


def summarize(rows: list[dict[str, Any]], memory_rows: list[dict[str, Any]],
              controls: dict[str, Any]) -> dict[str, Any]:
    medians = _median_batches(rows)
    by_query_count = {}
    for query_count in QUERY_COUNTS:
        method_rows = {}
        baseline_names = (
            "resident_direct_exhaustive", "resident_direct_screened",
            "resident_direct_source_packed",
        )
        baselines = {
            name: {n: medians[(n, query_count, name)]["batch_total_ns"] for n in N_VARS}
            for name in baseline_names
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
                "by_width_speedup_over_direct_screened": {
                    str(n): baselines["resident_direct_screened"][n] / selected[n]
                    for n in N_VARS
                },
                "aggregate_amortized_query_ns": sum(selected.values()) / (len(N_VARS) * query_count),
                "median_width_setup_ns": int(statistics.median(
                    medians[(n, query_count, method)]["setup_ns"] for n in N_VARS)),
            }
        best = min(METHODS, key=lambda method: (
            sum(medians[(n, query_count, method)]["batch_total_ns"] for n in N_VARS), method))
        by_query_count[str(query_count)] = {"methods": method_rows, "best_fixed_method": best}
    break_even = next((
        count for count in QUERY_COUNTS
        if by_query_count[str(count)]["methods"]["support_aware_c27_advice_on"]
        ["aggregate_speedup_over_direct_screened"] >= 1.0
        and by_query_count[str(count)]["methods"]["support_aware_c27_advice_on"]
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
        "support_aware_break_even_query_count": break_even,
        "support_aware_confirmation_gate": (
            controls.get("all_passed") is True and break_even is not None),
        "support_aware_confirmation_gate_contract": {
            "all_controls_pass": True,
            "aggregate_vs_direct_screened_minimum": 1.0,
            "minimum_width_vs_direct_screened_minimum": 0.90,
            "maximum_query_count": max(QUERY_COUNTS),
        },
        "memory": memory,
        "timing_is_retrospective_and_machine_specific": True,
    }


def _run_controls(cases: list[dict[str, Any]], oracles: dict[str, Any],
                  c27_policy_path: Path, c22_policy_path: Path,
                  output: Path) -> dict[str, Any]:
    c27_policy = load_support_aware_policy(c27_policy_path)
    c22_policy = load_source_portfolio_policy(c22_policy_path)
    fallback_session = SupportAwareGF2Session(
        "c27-fallback", c27_policy_path, c22_policy_path, max_queries=len(cases))
    fallback = []
    for case in cases:
        result = fallback_session.execute(case, force_selected_refusal=True).to_dict()
        if result["best_artifact"] != oracles[case["case_id"]]["best_artifact"]:
            raise RuntimeError("C27 forced fallback changed exhaustive best")
        fallback.append({
            "case_id": case["case_id"], "status": result["status"],
            "selected_arm": result["selected_arm"], "fallback_used": result["fallback_used"],
            "exact_check_passed": result["exact_check_passed"],
            "artifact_sha256": result["artifact_sha256"],
            "context_sha256": result["context_sha256"],
        })
    fallback_session.close()

    path_session = SupportAwareGF2Session(
        "c27-selected-paths", c27_policy_path, c22_policy_path,
        max_queries=len(cases))
    selected_paths = []
    for case in cases:
        result = path_session.execute(case).to_dict()
        expected = select_support_arm(c27_policy, case["n_vars"], advice_enabled=True)
        selected_paths.append({
            "case_id": case["case_id"], "n_vars": case["n_vars"],
            "expected_arm": expected, "selected_arm": result["selected_arm"],
            "status": result["status"], "exact_check_passed": result["exact_check_passed"],
        })
    path_session.close()

    seed = copy.deepcopy(cases[0])
    session = SupportAwareGF2Session(
        "c27-refusal", c27_policy_path, c22_policy_path, max_queries=1)
    mismatch = copy.deepcopy(seed)
    mismatch["truth_bits_hex"] = hex(int(mismatch["truth_bits_hex"], 16) ^ 1)
    ood = copy.deepcopy(seed)
    ood["n_vars"] = 7
    raw_refusals = [
        {"control_id": "truth_mismatch", "status": session.execute(mismatch).status},
        {"control_id": "unsupported_n7", "status": session.execute(ood).status},
    ]
    session.close()
    raw_refusals.append({"control_id": "closed_session", "status": session.execute(seed).status})
    limit = SupportAwareGF2Session(
        "c27-limit", c27_policy_path, c22_policy_path, max_queries=1)
    if limit.execute(seed).status != "ok":
        raise RuntimeError("C27 query-limit setup failed")
    raw_refusals.append({"control_id": "query_limit", "status": limit.execute(seed).status})

    tampered_c22 = dict(c22_policy)
    tampered_c22["selected_arm"] = EXHAUSTIVE
    tampered_c22_path = output / "control_c22_policy_tampered.json"
    _write(tampered_c22_path, tampered_c22)
    try:
        SupportAwareGF2Session(
            "c27-bad-c22", c27_policy_path, tampered_c22_path)
    except ValueError:
        status = "refused"
    else:
        status = "accepted"
    raw_refusals.append({"control_id": "tampered_c22_policy_at_setup", "status": status})

    tampered_c27 = dict(c27_policy)
    tampered_c27["tiny_support_max_n_vars"] = 3
    tampered_c27_path = output / "control_c27_policy_tampered.json"
    _write(tampered_c27_path, tampered_c27)
    try:
        SupportAwareGF2Session(
            "c27-bad-c27", tampered_c27_path, c22_policy_path)
    except ValueError:
        status = "refused"
    else:
        status = "accepted"
    raw_refusals.append({"control_id": "tampered_c27_policy_at_setup", "status": status})

    valid_context = build_verified_gf2_context(
        seed,
        require_source_packed=(seed["n_vars"] > c27_policy["tiny_support_max_n_vars"]),
    ).to_dict()
    context_controls = []
    for control_id, field, value in (
        ("tampered_context_expression", "expression_sha256", "0" * 64),
        ("tampered_context_truth", "truth_bits_hex", hex(int(valid_context["truth_bits_hex"], 16) ^ 1)),
        ("tampered_context_width", "n_vars", 6 if seed["n_vars"] != 6 else 5),
        ("tampered_context_digest", "context_sha256", "f" * 64),
    ):
        changed = copy.deepcopy(valid_context)
        changed[field] = value
        try:
            verify_verified_gf2_context(changed, seed)
        except ValueError:
            status = "refused"
        else:
            status = "accepted"
        context_controls.append({"control_id": control_id, "status": status})
    refusals = raw_refusals + context_controls
    fallback_pass = all(
        row["status"] == "ok" and row["selected_arm"] == EXHAUSTIVE
        and row["fallback_used"] is True and row["exact_check_passed"] is True
        for row in fallback)
    refusal_pass = all(row["status"] == "refused" for row in refusals)
    path_pass = all(
        row["status"] == "ok" and row["exact_check_passed"] is True
        and row["selected_arm"] == row["expected_arm"] for row in selected_paths)
    return {
        "schema": "crse-c27-support-aware-session-controls/v1",
        "fallback_cases": fallback,
        "selected_path_cases": selected_paths,
        "refusal_cases": refusals,
        "fallback_cases_checked": len(fallback),
        "selected_path_cases_checked": len(selected_paths),
        "tiny_truth_path_cases_checked": sum(
            row["selected_arm"] == TRUTH_SCREENED for row in selected_paths),
        "large_packed_path_cases_checked": sum(
            row["selected_arm"] == "source_packed_anf_screened" for row in selected_paths),
        "refusal_cases_checked": len(refusals),
        "context_tamper_controls_checked": len(context_controls),
        "fallback_gate": fallback_pass,
        "support_rule_gate": path_pass,
        "refusal_gate": refusal_pass,
        "all_passed": fallback_pass and path_pass and refusal_pass,
    }


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# C27 support-aware fresh confirmation", "",
        f"Status: **{result['status']}**  ",
        f"Confirmation gate: **{'pass' if summary['support_aware_confirmation_gate'] else 'fail'}**  ",
        f"Break-even query count: **{summary['support_aware_break_even_query_count']}**", "",
        "The policy was frozen before this corpus: n<=4 uses verified truth screening and n>=5",
        "uses the packed fused path. Every arm retains exact CM completion and final artifact",
        "reconstruction.", "",
        "| Queries | Support-aware vs screened | Minimum width vs screened | Best fixed method |",
        "|---:|---:|---:|---|",
    ]
    for count in QUERY_COUNTS:
        row = summary["by_query_count"][str(count)]
        advice = row["methods"]["support_aware_c27_advice_on"]
        lines.append(
            f"| {count} | {advice['aggregate_speedup_over_direct_screened']:.4f}x | "
            f"{advice['minimum_width_speedup_over_direct_screened']:.4f}x | "
            f"{row['best_fixed_method']} |")
    lines += ["", "Production promotion remains false."]
    return "\n".join(lines) + "\n"


def run(config: C27Config, output: Path, dataset_path: Path,
        dataset_verification_path: Path, c27_policy_path: Path,
        c22_policy_path: Path, c19_policy_path: Path, root: Path) -> dict[str, Any]:
    config.validate()
    wall_started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset_verification = json.loads(dataset_verification_path.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    if (
        len(dataset.get("cases", [])) != 48
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("cases_replayed") != 48
        or dataset_verification.get("expression_truth_mismatches") != 0
        or dataset_verification.get("scalar_oracle_mismatches") != 0
        or dataset_verification.get("prior_truth_overlaps") != 0
        or dataset.get("provenance", {}).get("policy_frozen_before_dataset") is not True
    ):
        raise ValueError("C27 requires the sealed fresh C27 corpus")
    c27_policy = load_support_aware_policy(c27_policy_path)
    c22_policy = load_source_portfolio_policy(c22_policy_path)
    c19_policy = load_policy(c19_policy_path)
    compiled = compile_work_policy(c19_policy)
    if (
        c27_policy["tiny_support_max_n_vars"] != 4
        or c27_policy["tiny_support_arm"] != TRUTH_SCREENED
        or c27_policy["large_support_arm"] != "source_packed_anf_screened"
        or c27_policy["fresh_confirmation_complete"] is not False
        or c27_policy["training_use"] is not False
        or c22_policy["selected_arm"] != "source_packed_anf_screened"
        or c22_policy["training_use"] is not False
        or compiled.mode != "constant_leaf"
        or compiled.constant_arm != "explicit_cm_screened"
    ):
        raise ValueError("C27 frozen policy contract changed")
    _write(output / "run_spec.json", {
        "schema": SCHEMA,
        "config": {**asdict(config), "query_counts": list(config.query_counts)},
        "dataset_path": _rel(dataset_path, root), "dataset_sha256": _sha256(dataset_path),
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
        "c19_policy_sha256": c19_policy["policy_sha256"],
        "methods": list(METHODS), "lifecycle": "support_aware_verified_context_resident",
        "support_rule": {"n_vars_lte_4": TRUTH_SCREENED,
                         "n_vars_gte_5": "source_packed_anf_screened"},
        "unchanged_c25_direct_controls": True,
        "single_expression_evaluation_per_fused_query": True,
        "context_digest_binds_expression_width_truth_and_source": True,
        "final_artifact_reconstruction_charged": True,
        "policy_frozen_before_fresh_corpus": True,
        "fresh_confirmation": True,
        "policy_refit": False, "production_promotion": False,
    })
    cases = dataset["cases"]
    functional, oracles = build_oracles(cases, config.oracle_config())
    if not functional["all_exact"]:
        raise RuntimeError("C27 exhaustive oracle replay failed")
    _write(output / "functional.json", functional)
    _write(output / "oracles.json", oracles)
    contracts = {
        case["case_id"]: decomposition_contract(
            contract_id=f"c27-{case['case_id']}", n_vars=case["n_vars"],
            required_output_sha256=oracles[case["case_id"]]["delivered_sha256"])
        for case in cases
    }
    _write(output / "contracts.json", contracts)
    controls = _run_controls(
        cases, oracles, c27_policy_path, c22_policy_path, output)
    if not controls["all_passed"]:
        raise RuntimeError("C27 functional controls failed")
    _write(output / "functional_controls.json", controls)
    cases_by_width = {
        n: sorted((case for case in cases if case["n_vars"] == n),
                  key=lambda case: (case["truth_sha256"], case["case_id"]))
        for n in N_VARS
    }
    if any(not group for group in cases_by_width.values()):
        raise ValueError("C27 support-width coverage mismatch")
    rng = random.Random(f"{config.seed}:c27-balanced/v1")
    rows = []
    for round_index in range(config.rounds):
        order = [(n, count, method) for n in N_VARS for count in QUERY_COUNTS for method in METHODS]
        rng.shuffle(order)
        for n_vars, query_count, method in order:
            if time.perf_counter() - wall_started > config.max_seconds:
                raise TimeoutError("C27 experiment exceeded wall bound")
            sequence = case_sequence(cases_by_width, n_vars, query_count, round_index)
            if method in DIRECT_METHODS:
                execution = execute_c25_direct_batch(
                    session_id=f"c27-r{round_index}-n{n_vars}-q{query_count}-{method}",
                    method=method, cases=sequence, contracts=contracts, oracles=oracles,
                    c22_policy_path=c22_policy_path, c19_policy_path=c19_policy_path,
                    max_partitions=config.max_partitions,
                    materialize_budget=config.materialize_budget)
            else:
                execution = execute_support_aware_batch(
                    session_id=f"c27-r{round_index}-n{n_vars}-q{query_count}-{method}",
                    method=method, cases=sequence, oracles=oracles,
                    c27_policy_path=c27_policy_path,
                    c22_policy_path=c22_policy_path)
            rows.append({"round": round_index, "n_vars": n_vars,
                         "query_count": query_count, **execution})
    _write_jsonl(output / "measurements.jsonl", rows)
    memory_rows = []
    for n_vars in N_VARS:
        sequence = case_sequence(cases_by_width, n_vars, config.memory_query_count, 0)
        for method in METHODS:
            tracemalloc.start()
            try:
                if method in DIRECT_METHODS:
                    execution = execute_c25_direct_batch(
                        session_id=f"c27-memory-n{n_vars}-{method}", method=method,
                        cases=sequence, contracts=contracts, oracles=oracles,
                        c22_policy_path=c22_policy_path, c19_policy_path=c19_policy_path,
                        max_partitions=config.max_partitions,
                        materialize_budget=config.materialize_budget)
                else:
                    execution = execute_support_aware_batch(
                        session_id=f"c27-memory-n{n_vars}-{method}", method=method,
                        cases=sequence, oracles=oracles,
                        c27_policy_path=c27_policy_path,
                        c22_policy_path=c22_policy_path)
                current, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            memory_rows.append({"n_vars": n_vars, "query_count": config.memory_query_count,
                                "method": method, "current_bytes": current,
                                "peak_bytes": peak,
                                "exact_check_passed": execution["exact_check_passed"]})
    _write_jsonl(output / "memory_measurements.jsonl", memory_rows)
    summary = summarize(rows, memory_rows, controls)
    mismatches = sum(not row["exact_check_passed"] for row in rows)
    result = {
        "schema": SCHEMA,
        "status": "complete" if mismatches == 0 and controls["all_passed"] else "failed",
        "config": {**asdict(config), "query_counts": list(config.query_counts)},
        "wall_seconds": time.perf_counter() - wall_started,
        "environment": {
            "python": sys.version, "platform": platform.platform(),
            "dd_version": importlib.metadata.version("dd"),
            "thread_environment": {name: os.environ.get(name) for name in
                                   ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        },
        "dataset": {"cases": len(cases), "families": dataset["counts"]["families"],
                    "n_vars": list(N_VARS), "fresh_confirmation": True,
                    "policy_refit": False},
        "measurement_batches": len(rows),
        "timed_queries": sum(row["query_count"] for row in rows),
        "memory_measurement_batches": len(memory_rows),
        "fallback_controls": controls["fallback_cases_checked"],
        "selected_path_controls": controls["selected_path_cases_checked"],
        "tiny_truth_path_controls": controls["tiny_truth_path_cases_checked"],
        "large_packed_path_controls": controls["large_packed_path_cases_checked"],
        "refusal_controls": controls["refusal_cases_checked"],
        "context_tamper_controls": controls["context_tamper_controls_checked"],
        "semantic_or_artifact_mismatches": mismatches,
        "summary": summary,
        "claims": {
            "unchanged_c22_policy": True, "unchanged_c25_direct_controls": True,
            "support_policy_frozen_before_corpus": True,
            "transparent_support_rule": True,
            "single_expression_evaluation_per_support_aware_query": True,
            "hash_bound_verified_context": True, "every_query_exactly_verified": True,
            "fallback_and_refusal_controls_passed": controls["all_passed"],
            "fresh_confirmation": True, "policy_refit": False,
            "production_promotion": False,
        },
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    sources = (
        "cmbench/comparative/gf2_support_aware_experiment.py",
        "cmbench/comparative/gf2_resident_session_experiment.py",
        "cmbench/recognition/gf2_support_aware_session.py",
        "cmbench/recognition/gf2_support_aware_policy.py",
        "cmbench/recognition/gf2_verified_context.py",
        "cmbench/recognition/yosys_c27_gf2_data.py",
        "scripts/cm_comparative_c27_support_aware.py",
    )
    artifacts = (
        "run_spec.json", "functional.json", "oracles.json", "contracts.json",
        "control_c22_policy_tampered.json", "control_c27_policy_tampered.json",
        "functional_controls.json", "measurements.jsonl", "memory_measurements.jsonl",
        "results.json", "report.md",
    )
    _write(output / "manifest.json", {
        "schema": "crse-c27-run-manifest/v1",
        "dataset_sha256": _sha256(dataset_path),
        "dataset_verification_sha256": _sha256(dataset_verification_path),
        "c27_policy_file_sha256": _sha256(c27_policy_path),
        "c22_policy_file_sha256": _sha256(c22_policy_path),
        "c19_policy_file_sha256": _sha256(c19_policy_path),
        "sources": {name: _sha256(root / name) for name in sources},
        "artifacts": {name: _sha256(output / name) for name in artifacts},
    })
    return result

