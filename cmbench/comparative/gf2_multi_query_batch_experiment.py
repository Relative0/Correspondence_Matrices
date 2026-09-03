"""Development adjudication for exact multi-query batching and engine choice."""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import time
import tracemalloc
from typing import Any

from bitset_backend import (
    bitset_to_bool_array,
    build_bitset_env,
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_bitset,
    eval_expr_flat_cse,
    eval_expr_words_cse,
    get_expr_cse_program,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json
from cm_ir import compile_expr_to_cm_ir

from .contracts import canonical_bytes
from .gf2_multi_query_batches import (
    batch_plan_metrics,
    build_multi_query_batch_plan,
    gather_multi_query_batch,
    prepare_arbitrary_assignment_lanes,
)
from .gf2_restricted_evaluator_experiment import (
    _environment,
    _rss_snapshot,
    collect_reproducibility_manifest,
)
from .gf2_restricted_evaluators import (
    arena_structural_profile,
    compile_restricted_arena,
    eval_restricted_r2,
    prepare_restriction,
)
from .gf2_wide_repeated_queries import (
    oracle_document,
    project_truth_vector,
    projection_indices,
    semantic_document,
    semantic_row,
    validate_dataset,
    validate_query_trace,
    validate_wide_case,
)
from .schedule import balanced_orders


SCHEMA = "crse-multi-query-batch-development/v1"
RAW_SCHEMA = "crse-multi-query-batch-raw-session/v1"
METHODS = (
    "r2_per_query",
    "cse_bigint",
    "cse_words",
    "cm_ir_bigint",
    "cm_ir_words",
    "concatenated_r2",
    "union_care_r2",
    "full_projection",
)
BATCH_METHODS = ("concatenated_r2", "union_care_r2")
BASELINE_METHODS = tuple(method for method in METHODS if method not in BATCH_METHODS)
QUERY_COUNTS = (1, 4, 16, 64)
EXTRA_MANIFEST_SOURCES = (
    "cmbench/comparative/gf2_multi_query_batches.py",
    "cmbench/comparative/gf2_multi_query_batch_experiment.py",
    "scripts/cm_comparative_multi_query_batch_development.py",
    "scripts/crse_multi_query_batch_development_verify.py",
)


@dataclass(frozen=True)
class MultiQueryBatchConfig:
    run_id: str
    seed: int = 20260902
    blocks: int = 8
    query_counts: tuple[int, ...] = QUERY_COUNTS
    development_speedup_gate: float = 1.10
    max_seconds: float = 900.0

    def validate(self) -> None:
        if (
            not self.run_id
            or self.blocks != len(METHODS)
            or tuple(self.query_counts) != QUERY_COUNTS
            or self.development_speedup_gate != 1.10
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 60 <= self.max_seconds <= 1800
        ):
            raise ValueError("invalid multi-query development bounds")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False) + "\n")


def build_schedule(
    cases: Sequence[Mapping[str, Any]], blocks: int, seed: int,
) -> list[dict[str, Any]]:
    orders = balanced_orders(METHODS)[:len(METHODS)]
    if blocks != len(orders):
        raise ValueError("multi-query schedule requires one counterbalance cycle")
    rows: list[dict[str, Any]] = []
    for block in range(blocks):
        cells = [(case, query_count) for case in cases for query_count in QUERY_COUNTS]
        random.Random(f"multi-query-batch:{seed}:{block}").shuffle(cells)
        method_order = orders[(block + seed) % len(orders)]
        for position, (case, query_count) in enumerate(cells):
            core = {
                "block": block,
                "cell_position": position,
                "case_id": case["case_id"],
                "family": case["family"],
                "n_vars": case["n_vars"],
                "query_count": query_count,
                "method_order": list(method_order),
            }
            core["order_sha256"] = _digest(core)
            rows.append(core)
    return rows


def validate_schedule(
    rows: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]], blocks: int,
) -> None:
    if len(rows) != len(cases) * len(QUERY_COUNTS) * blocks:
        raise ValueError("multi-query schedule cardinality")
    case_ids = {case["case_id"] for case in cases}
    for row in rows:
        core = {key: row[key] for key in (
            "block", "cell_position", "case_id", "family", "n_vars",
            "query_count", "method_order")}
        if (
            row.get("order_sha256") != _digest(core)
            or row["case_id"] not in case_ids
            or row["query_count"] not in QUERY_COUNTS
            or set(row["method_order"]) != set(METHODS)
        ):
            raise ValueError("multi-query schedule identity")
    for case_id in case_ids:
        for query_count in QUERY_COUNTS:
            selected = [row for row in rows if (
                row["case_id"] == case_id and row["query_count"] == query_count)]
            if Counter(row["block"] for row in selected) != Counter(range(blocks)):
                raise ValueError("multi-query case/query block balance")
            for method in METHODS:
                positions = Counter(row["method_order"].index(method) for row in selected)
                if positions != Counter({index: 1 for index in range(len(METHODS))}):
                    raise ValueError("multi-query arm-position balance")


def _sample_rss(samples: list[int], process_peaks: list[int]) -> None:
    current, peak = _rss_snapshot()
    if current is not None:
        samples.append(current)
    if peak is not None:
        process_peaks.append(peak)


def _expected_prefix(case: Mapping[str, Any], query_count: int) -> dict[str, Any]:
    full = oracle_document(case, case["c36_trace"])
    return semantic_document(case["case_id"], full["rows"][:query_count])


def execute_session(
    *,
    case: Mapping[str, Any],
    method: str,
    query_count: int,
    role: str,
    clock: Callable[[], int] = time.perf_counter_ns,
    profile_python_allocations: bool = False,
) -> dict[str, Any]:
    normalized = validate_wide_case(case)
    if (
        method not in METHODS
        or query_count not in QUERY_COUNTS
        or role not in ("performance", "memory_profile")
    ):
        raise ValueError("invalid multi-query session")
    full_trace = validate_query_trace(
        case.get("c36_trace"), normalized["case_id"], normalized["n_vars"])
    trace = full_trace[:query_count]
    expected = _expected_prefix(case, query_count)
    expected_digest = _digest(expected)
    if profile_python_allocations:
        tracemalloc.start()
    rss_samples: list[int] = []
    process_peaks: list[int] = []
    _sample_rss(rss_samples, process_peaks)

    started = clock()
    expression = expr_from_json(case["expression_v2"])
    input_decode_ns = max(1, clock() - started)
    _sample_rss(rss_samples, process_peaks)

    arena = node = program = truth_vector = None
    resources: dict[str, Any] = {}
    started = clock()
    if method in ("r2_per_query", *BATCH_METHODS):
        arena = compile_restricted_arena(case["expression_v2"])
    elif method in ("cse_bigint", "cse_words"):
        program = get_expr_cse_program(expression, flatten=True)
    elif method in ("cm_ir_bigint", "cm_ir_words"):
        node = compile_expr_to_cm_ir(
            expression, reuse_cache=False, persistent_cache=False,
            share_aware_flatten=True)
        program = get_flat_program(node)
    else:
        names = tuple(f"x{i}" for i in range(normalized["n_vars"]))
        full_bits = eval_expr_bitset(expression, build_bitset_env(names))
        truth_vector = bitset_to_bool_array(full_bits, normalized["n_vars"])
    representation_ns = max(1, clock() - started)
    if arena is not None:
        resources.update(arena_structural_profile(arena))
    if program is not None:
        resources.update(program_metrics(program))
    _sample_rss(rss_samples, process_peaks)

    query_inputs: list[tuple[dict[str, int], tuple[str, ...]]] = []
    batch_plan = prepared_batch = projection_plans = None
    started = clock()
    if method in BATCH_METHODS:
        mode = "concatenated" if method == "concatenated_r2" else "union_care"
        batch_plan = build_multi_query_batch_plan(trace, normalized["n_vars"], mode)
        prepared_batch = prepare_arbitrary_assignment_lanes(
            batch_plan.assignments, normalized["n_vars"])
    else:
        for query in trace:
            fixed = {row["variable"]: row["value"] for row in query["fixed"]}
            query_inputs.append((fixed, tuple(query["remaining_order"])))
        if method == "full_projection":
            projection_plans = [
                projection_indices(normalized["n_vars"], fixed, remaining)
                for fixed, remaining in query_inputs
            ]
    restriction_setup_ns = max(1, clock() - started)
    if batch_plan is not None:
        resources.update(batch_plan_metrics(batch_plan))
    if projection_plans is not None:
        resources.update({
            "materialized_truth_bits": 1 << normalized["n_vars"],
            "compiled_projection_index_bytes": sum(
                plan.nbytes for plan in projection_plans),
        })
    _sample_rss(rss_samples, process_peaks)

    started = clock()
    if method == "r2_per_query":
        outputs = tuple(eval_restricted_r2(
            arena, prepare_restriction(fixed, remaining))
            for fixed, remaining in query_inputs)
    elif method == "cse_bigint":
        outputs = tuple(eval_expr_flat_cse(
            expression, remaining, fixed=fixed, flatten=True)
            for fixed, remaining in query_inputs)
    elif method == "cse_words":
        outputs = tuple(eval_expr_words_cse(
            expression, remaining, fixed=fixed, flatten=True)
            for fixed, remaining in query_inputs)
    elif method == "cm_ir_bigint":
        outputs = tuple(eval_cm_node_flat(node, remaining, fixed=fixed)
                        for fixed, remaining in query_inputs)
    elif method == "cm_ir_words":
        outputs = tuple(eval_cm_node_words(node, remaining, fixed=fixed)
                        for fixed, remaining in query_inputs)
    elif method in BATCH_METHODS:
        packed = eval_restricted_r2(arena, prepared_batch)
        outputs = gather_multi_query_batch(packed, batch_plan)
    else:
        outputs = tuple(project_truth_vector(truth_vector, plan)
                        for plan in projection_plans)
    evaluation_ns = max(1, clock() - started)
    _sample_rss(rss_samples, process_peaks)

    started = clock()
    semantic_rows = [semantic_row(query, int(reduced), normalized["n_vars"])
                     for query, reduced in zip(trace, outputs, strict=True)]
    output_hashes = [_digest(row) for row in semantic_rows]
    document = semantic_document(normalized["case_id"], semantic_rows)
    actual_digest = _digest(document)
    delivery_ns = max(1, clock() - started)
    if actual_digest != expected_digest:
        raise RuntimeError(f"{method} failed the exact multi-query prefix oracle")

    started = clock()
    expression = arena = node = program = truth_vector = None
    batch_plan = prepared_batch = projection_plans = query_inputs = None
    cleanup_ns = max(1, clock() - started)
    _sample_rss(rss_samples, process_peaks)
    accounted_total_ns = (
        input_decode_ns + representation_ns + restriction_setup_ns
        + evaluation_ns + delivery_ns + cleanup_ns)
    resources.update({
        "session_sampled_start_rss_bytes": rss_samples[0] if rss_samples else None,
        "session_sampled_peak_rss_bytes": max(rss_samples) if rss_samples else None,
        "session_sampled_peak_rss_delta_bytes": (
            max(rss_samples) - rss_samples[0] if rss_samples else None),
        "process_peak_rss_bytes": max(process_peaks) if process_peaks else None,
        "rss_sampling_points": len(rss_samples),
    })
    if profile_python_allocations:
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        resources["tracemalloc_peak_bytes"] = int(peak)
    return {
        "schema": RAW_SCHEMA,
        "role": role,
        "case_id": normalized["case_id"],
        "family": case["family"],
        "n_vars": normalized["n_vars"],
        "query_count": query_count,
        "method": method,
        "status": "ok",
        "timings_ns": {
            "input_decode_ns": input_decode_ns,
            "representation_ns": representation_ns,
            "restriction_setup_ns": restriction_setup_ns,
            "evaluation_ns": evaluation_ns,
            "delivery_ns": delivery_ns,
            "cleanup_ns": cleanup_ns,
            "accounted_total_ns": accounted_total_ns,
        },
        "query_output_sha256": output_hashes,
        "artifact_sha256": actual_digest,
        "artifact_bytes": len(canonical_bytes(document)),
        "resources": resources,
        "exact_check_passed": True,
    }


def _medians(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[tuple[str, str, int], int], list[str]]:
    values: dict[tuple[str, str, int], list[int]] = {}
    cases = sorted({row["case_id"] for row in rows if row["role"] == "performance"})
    for row in rows:
        if row["role"] == "performance":
            values.setdefault((row["case_id"], row["method"], row["query_count"]), []).append(
                row["timings_ns"]["accounted_total_ns"])
    medians = {key: int(statistics.median(samples)) for key, samples in values.items()}
    if len(medians) != len(cases) * len(METHODS) * len(QUERY_COUNTS):
        raise ValueError("incomplete multi-query medians")
    return medians, cases


def _method_totals(
    selected: Sequence[str], medians: Mapping[tuple[str, str, int], int], query_count: int,
) -> dict[str, int]:
    return {method: sum(medians[(case, method, query_count)] for case in selected)
            for method in METHODS}


def summarize(
    rows: Sequence[Mapping[str, Any]], geometry: Mapping[str, Mapping[str, Any]],
    speedup_gate: float,
) -> dict[str, Any]:
    medians, cases = _medians(rows)
    metadata = {row["case_id"]: (row["family"], row["n_vars"])
                for row in rows if row["role"] == "performance"}
    checkpoints: dict[str, Any] = {}
    for query_count in QUERY_COUNTS:
        totals = _method_totals(cases, medians, query_count)
        best = min(METHODS, key=lambda method: (totals[method], method))
        best_baseline = min(BASELINE_METHODS,
                            key=lambda method: (totals[method], method))
        best_batch = min(BATCH_METHODS,
                         key=lambda method: (totals[method], method))
        winners = {case: min(
            METHODS, key=lambda method: (medians[(case, method, query_count)], method))
            for case in cases}
        oracle = sum(medians[(case, winners[case], query_count)] for case in cases)
        checkpoints[str(query_count)] = {
            "method_total_ns": totals,
            "best_fixed_method": best,
            "best_nonbatch_baseline": best_baseline,
            "best_batch_method": best_batch,
            "best_batch_speedup_over_best_nonbatch": totals[best_baseline] / totals[best_batch],
            "per_case_winners": winners,
            "per_case_oracle_total_ns": oracle,
            "oracle_speedup_over_best_fixed": totals[best] / oracle,
            "cse_words_speedup_over_bigint": totals["cse_bigint"] / totals["cse_words"],
            "cm_words_speedup_over_bigint": totals["cm_ir_bigint"] / totals["cm_ir_words"],
            "preferred_cse_engine": min(
                ("cse_bigint", "cse_words"), key=lambda method: (totals[method], method)),
            "preferred_cm_engine": min(
                ("cm_ir_bigint", "cm_ir_words"), key=lambda method: (totals[method], method)),
        }
    by_width: dict[str, Any] = {}
    for width in sorted({value[1] for value in metadata.values()}):
        selected = [case for case in cases if metadata[case][1] == width]
        totals = _method_totals(selected, medians, 64)
        by_width[str(width)] = {
            "cases": len(selected),
            "method_total_ns": totals,
            "best_fixed_method": min(METHODS, key=lambda method: (totals[method], method)),
            "preferred_cse_engine": min(
                ("cse_bigint", "cse_words"), key=lambda method: (totals[method], method)),
            "preferred_cm_engine": min(
                ("cm_ir_bigint", "cm_ir_words"), key=lambda method: (totals[method], method)),
        }
    memory_rows = [row for row in rows if row["role"] == "memory_profile"]
    memory = {}
    for method in METHODS:
        selected = [row for row in memory_rows if row["method"] == method]
        memory[method] = {
            "profile_sessions": len(selected),
            "max_session_sampled_peak_rss_delta_bytes": max(
                (row["resources"]["session_sampled_peak_rss_delta_bytes"] or 0)
                for row in selected),
            "max_tracemalloc_peak_bytes": max(
                row["resources"].get("tracemalloc_peak_bytes", 0) for row in selected),
        }
    final = checkpoints["64"]
    return {
        "cases": len(cases),
        "performance_sessions": sum(row["role"] == "performance" for row in rows),
        "memory_profile_sessions": len(memory_rows),
        "checkpoints": checkpoints,
        "by_width_at_q64": by_width,
        "batch_geometry": dict(geometry),
        "memory_profiles": memory,
        "decision": {
            "development_speedup_gate": speedup_gate,
            "best_batch_at_q64": final["best_batch_method"],
            "best_batch_speedup_over_best_nonbatch_at_q64": (
                final["best_batch_speedup_over_best_nonbatch"]),
            "batch_continuation_gate_passed": (
                final["best_batch_speedup_over_best_nonbatch"] >= speedup_gate),
            "best_fixed_at_q64": final["best_fixed_method"],
            "formal_confirmation_or_production_promotion_permitted": False,
        },
        "timing_is_local_and_machine_specific": True,
        "memory_timing_excluded_from_performance_summary": True,
    }


def render_protocol(
    config: MultiQueryBatchConfig, dataset_path: Path,
    dataset_verification_path: Path, root: Path,
) -> str:
    return "\n".join([
        "# Multi-query exact batching development protocol",
        "",
        f"Run ID: `{config.run_id}`",
        "",
        "Development-only use of the exposed C36 corpus; not C37 confirmation.",
        "The frozen relation/count/SAT/witness delivery semantics and variable order",
        "are retained for independent q1, q4, q16, and q64 prefix tasks.",
        "",
        "Arms: repaired R2 per-query restriction, CSE bigint/words, CM-IR",
        "bigint/words, concatenated arbitrary lanes, union-care arbitrary lanes,",
        "and compiled full-truth projection.",
        "",
        f"Dataset: `{dataset_path.relative_to(root).as_posix()}`",
        f"Dataset verification: `{dataset_verification_path.relative_to(root).as_posix()}`",
        f"Blocks: {config.blocks}; seed: {config.seed}; continuation gate: "
        f"{config.development_speedup_gate:.2f}x over the best nonbatch backend at q64.",
        "",
        "All decode, representation, batch/restriction setup, evaluation, delivery,",
        "and cleanup costs are charged. Memory sessions are separate and excluded",
        "from performance summaries. No threshold/model fitting or promotion is allowed.",
        "",
    ])


def render_report(result: Mapping[str, Any]) -> str:
    lines = [
        "# Multi-query exact batching development result",
        "",
        f"Status: **{result['status']}**",
        "",
        "All eight methods delivered byte-identical exact prefix documents.",
        "",
        "| Q | Best fixed | Best batch | Batch vs best nonbatch | CSE words vs bigint | CM words vs bigint |",
        "|---:|---|---|---:|---:|---:|",
    ]
    for query_count in QUERY_COUNTS:
        row = result["summary"]["checkpoints"][str(query_count)]
        lines.append(
            f"| {query_count} | {row['best_fixed_method']} | {row['best_batch_method']} | "
            f"{row['best_batch_speedup_over_best_nonbatch']:.4f}x | "
            f"{row['cse_words_speedup_over_bigint']:.4f}x | "
            f"{row['cm_words_speedup_over_bigint']:.4f}x |")
    decision = result["summary"]["decision"]
    lines += [
        "",
        "## Decision",
        "",
        f"The q64 batch continuation gate **{'passed' if decision['batch_continuation_gate_passed'] else 'did not pass'}**. "
        f"The best batch was `{decision['best_batch_at_q64']}` at "
        f"{decision['best_batch_speedup_over_best_nonbatch_at_q64']:.4f}x versus the "
        "best nonbatch backend.",
        "",
        f"The overall q64 best fixed arm was `{decision['best_fixed_at_q64']}`.",
        "No formal confirmation or production promotion is permitted by this exposed-data run.",
        "",
    ]
    return "\n".join(lines)


def _geometry(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for case in cases:
        rows: dict[str, Any] = {}
        for query_count in QUERY_COUNTS:
            trace = case["c36_trace"][:query_count]
            concat = build_multi_query_batch_plan(trace, case["n_vars"], "concatenated")
            care = build_multi_query_batch_plan(trace, case["n_vars"], "union_care")
            rows[str(query_count)] = {
                "requested_lane_count": concat.requested_lane_count,
                "union_lane_count": care.lane_count,
                "full_truth_lane_count": 1 << case["n_vars"],
                "union_coverage": care.lane_count / (1 << case["n_vars"]),
                "deduplication_fraction": (
                    1 - care.lane_count / concat.requested_lane_count),
            }
        output[case["case_id"]] = rows
    return output


def run(
    config: MultiQueryBatchConfig,
    output: Path,
    dataset_path: Path,
    dataset_verification_path: Path,
    root: Path,
    *,
    progress: Callable[[str, int, int, str], None] | None = None,
) -> dict[str, Any]:
    config.validate()
    wall_started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    (output / "protocol.md").write_text(
        render_protocol(config, dataset_path, dataset_verification_path, root),
        encoding="utf-8", newline="\n")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    verification = json.loads(dataset_verification_path.read_text(encoding="utf-8"))
    if (
        verification.get("status") != "verified"
        or verification.get("dataset_sha256") != _sha256(dataset_path)
    ):
        raise ValueError("multi-query dataset verification binding")
    validate_dataset(dataset)
    cases = list(dataset["cases"])
    geometry = _geometry(cases)
    schedule = build_schedule(cases, config.blocks, config.seed)
    validate_schedule(schedule, cases, config.blocks)
    case_map = {case["case_id"]: case for case in cases}
    rows: list[dict[str, Any]] = []
    for index, planned in enumerate(schedule):
        case = case_map[planned["case_id"]]
        for method_position, method in enumerate(planned["method_order"]):
            session = execute_session(
                case=case, method=method, query_count=planned["query_count"],
                role="performance")
            session.update({
                "block": planned["block"],
                "cell_position": planned["cell_position"],
                "method_position": method_position,
                "method_order": planned["method_order"],
                "order_sha256": planned["order_sha256"],
            })
            rows.append(session)
        if progress is not None:
            progress("performance", index + 1, len(schedule), case["case_id"])
        if time.perf_counter() - wall_started > config.max_seconds:
            raise TimeoutError("multi-query experiment exceeded wall bound")

    memory_total = len(cases) * len(METHODS)
    memory_index = 0
    orders = balanced_orders(METHODS)
    for case_index, case in enumerate(cases):
        order = orders[case_index % len(orders)]
        for method_position, method in enumerate(order):
            session = execute_session(
                case=case, method=method, query_count=64, role="memory_profile",
                profile_python_allocations=True)
            session.update({
                "block": None,
                "cell_position": case_index,
                "method_position": method_position,
                "method_order": list(order),
                "order_sha256": _digest({
                    "role": "memory_profile", "case_id": case["case_id"],
                    "method_order": list(order)}),
            })
            rows.append(session)
            memory_index += 1
            if progress is not None:
                progress("memory", memory_index, memory_total, case["case_id"])
        if time.perf_counter() - wall_started > config.max_seconds:
            raise TimeoutError("multi-query experiment exceeded wall bound")

    _write_jsonl(output / "raw_measurements.jsonl", rows)
    summary = summarize(rows, geometry, config.development_speedup_gate)
    result = {
        "schema": SCHEMA,
        "status": "complete",
        "run_id": config.run_id,
        "config": {**asdict(config), "query_counts": list(config.query_counts)},
        "methods": list(METHODS),
        "dataset": {
            "path": dataset_path.relative_to(root).as_posix(),
            "sha256": _sha256(dataset_path),
            "verification_path": dataset_verification_path.relative_to(root).as_posix(),
            "verification_sha256": _sha256(dataset_verification_path),
            "classification": "development_exposed_c36_not_confirmation",
        },
        "summary": summary,
        "correctness": {
            "relation_mismatches": 0,
            "count_mismatches": 0,
            "sat_mismatches": 0,
            "witness_mismatches": 0,
            "canonical_delivery_mismatches": 0,
        },
        "decision": {
            "training_performed": False,
            "threshold_refit": False,
            "prospective_data_consumed": False,
            "production_write": False,
            "production_promotion": False,
        },
        "elapsed_seconds": time.perf_counter() - wall_started,
    }
    _write_json(output / "results.json", result)
    (output / "report.md").write_text(
        render_report(result), encoding="utf-8", newline="\n")
    environment = _environment(root, dataset_path, dataset_verification_path)
    environment["schema"] = "crse-multi-query-batch-environment/v1"
    _write_json(output / "environment.json", environment)
    artifact_names = (
        "protocol.md", "raw_measurements.jsonl", "environment.json",
        "results.json", "report.md")
    artifacts = {name: _sha256(output / name) for name in artifact_names}
    _write_json(output / "manifest.json", collect_reproducibility_manifest(
        root, artifacts, EXTRA_MANIFEST_SOURCES))
    return result
