#!/usr/bin/env python3
"""Current CM preparation, kernel, dispatch, and memory audit.

The harness replays accepted immutable corpora.  It keeps preparation and
steady-state kernel windows separate, alternates paired kernel order, validates
every packed result exactly, and refuses to overwrite output files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bitset_backend import (  # noqa: E402
    compile_expr_flat,
    compile_flat,
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_flat_bitset,
    eval_expr_words_bitset,
    get_expr_flat_program,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json, expr_to_json_dag  # noqa: E402
from cm_ir import (  # noqa: E402
    _cm_node_count,
    clear_cm_ir_compile_cache,
    clear_cm_ir_persistent_cache,
    compile_expr_to_cm_ir,
    expr_structural_hash,
    materialize_hybrid_no_reinflate,
)
from cmbench.backends.bitset_engine import WORDS_AUTO_MIN_VARS  # noqa: E402
from scripts.cm_benchmark_provenance import (  # noqa: E402
    capture_source_snapshot,
    source_hashes,
)


CORPORA = {
    "bx1": REPO_ROOT
    / "deliverables_n22_24"
    / "bx1_crossover_2026_08_03"
    / "CM_bx1_crossover_corpus_2026_08_03.jsonl",
    "b2": REPO_ROOT
    / "deliverables_n22_24"
    / "b2_wrapper_2026_08_03"
    / "CM_b2_wrapper_corpus_2026_08_03.jsonl",
    "epfl": REPO_ROOT
    / "deliverables_n22_24"
    / "CM_gap_epfl_corpus_2026_08_03.jsonl",
}

SOURCE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cmbench/backends/bitset_engine.py",
    "cmbench/output_budget.py",
    "cmbench/reporting/__init__.py",
    "cmbench/reporting/provenance.py",
    "cmbench/reporting/summary_tables.py",
    "scripts/cm_benchmark_provenance.py",
    "scripts/cm_deep_performance_audit.py",
)


def _natural_key(name: str) -> tuple[int, object]:
    if name.startswith("x") and name[1:].isdigit():
        return (0, int(name[1:]))
    return (1, name)


def _median_ns(fn: Callable[[], Any], repetitions: int) -> tuple[float, Any]:
    samples: list[int] = []
    result: Any = None
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        result = fn()
        samples.append(time.perf_counter_ns() - start)
    return float(statistics.median(samples)), result


def _paired_per_call_ns(
    left: Callable[[], int],
    right: Callable[[], int],
    *,
    batch: int,
    rounds: int,
) -> tuple[float, float, int, int]:
    left_samples: list[float] = []
    right_samples: list[float] = []
    left_value = right_value = 0

    def run(fn: Callable[[], int]) -> tuple[float, int]:
        value = 0
        start = time.perf_counter_ns()
        for _ in range(batch):
            value = fn()
        return (time.perf_counter_ns() - start) / batch, value

    left_value = left()
    right_value = right()
    for round_index in range(rounds):
        if round_index % 2:
            right_ns, right_value = run(right)
            left_ns, left_value = run(left)
        else:
            left_ns, left_value = run(left)
            right_ns, right_value = run(right)
        left_samples.append(left_ns)
        right_samples.append(right_ns)
    return (
        float(statistics.median(left_samples)),
        float(statistics.median(right_samples)),
        int(left_value),
        int(right_value),
    )


def _per_call_ns(fn: Callable[[], int], *, batch: int, rounds: int) -> tuple[float, int]:
    samples: list[float] = []
    value = fn()
    for _ in range(rounds):
        start = time.perf_counter_ns()
        for _ in range(batch):
            value = fn()
        samples.append((time.perf_counter_ns() - start) / batch)
    return float(statistics.median(samples)), int(value)


def _batch_for(k: int) -> int:
    if k <= 8:
        return 100
    if k <= 10:
        return 50
    if k <= 12:
        return 20
    return 5


def _records(corpus: str) -> Iterable[dict[str, Any]]:
    path = CORPORA[corpus]
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if "expression_v2" in record:
                yield record


def _sample_records(corpus: str, suite: str) -> list[dict[str, Any]]:
    records = list(_records(corpus))
    if suite != "smoke":
        return records
    selected: list[dict[str, Any]] = []
    seen: set[int] = set()
    for record in records:
        k = int(
            record.get("live_k")
            or record.get("stratum_live_k")
            or record.get("sem_support_size")
        )
        if k not in seen:
            selected.append(record)
            seen.add(k)
    return selected


def _expr_tree_occurrences(expr: Any) -> int:
    total = 0
    stack = [expr]
    while stack:
        cur = stack.pop()
        total += 1
        if hasattr(cur, "a"):
            stack.append(cur.a)
        if hasattr(cur, "b"):
            stack.append(cur.b)
    return total


def _ir_nodes(node: Any) -> int:
    seen: set[int] = set()
    stack = [node]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        stack.extend(cur.args)
    return len(seen)


def _compile_profile(expr: Any, repetitions: int) -> tuple[dict[str, float], Any]:
    phase_keys = (
        "ir_compile_time_s",
        "ir_canonicalize_time_s",
        "ir_rewrite_time_s",
        "ir_intern_time_s",
        "ir_live_vars_time_s",
    )
    external: list[int] = []
    phases: dict[str, list[float]] = {key: [] for key in phase_keys}
    node = None
    for _ in range(repetitions):
        diag: dict[str, Any] = {"ir_timing_enabled": 1}
        start = time.perf_counter_ns()
        node = compile_expr_to_cm_ir(expr, diagnostics=diag)
        external.append(time.perf_counter_ns() - start)
        for key in phase_keys:
            phases[key].append(float(diag.get(key, 0.0)) * 1e9)
    result = {"compile_external_ns": float(statistics.median(external))}
    result.update({key.replace("_time_s", "_ns"): float(statistics.median(values)) for key, values in phases.items()})
    return result, node


def _evaluation_context(
    corpus: str,
    record: Mapping[str, Any],
    expr: Any,
    live_k: int,
) -> tuple[tuple[str, ...], dict[str, int]]:
    all_variables = tuple(
        sorted((f"x{i}" for i in {n.i for n in _walk_vars(expr)}), key=_natural_key)
    )
    if corpus != "epfl":
        if len(all_variables) != live_k:
            raise AssertionError(
                f"{record.get('id')}: live_k={live_k}, variables={all_variables!r}"
            )
        return all_variables, {}

    syntactic_inputs = list(record.get("synt_support_inputs") or ())
    semantic_inputs = set(record.get("sem_support_inputs") or ())
    if len(syntactic_inputs) != len(all_variables):
        raise AssertionError(
            f"{record.get('id')}: cannot map syntactic to semantic support"
        )
    live_positions = {
        index
        for index, original_input in enumerate(syntactic_inputs)
        if original_input in semantic_inputs
    }
    # The frozen EPFL corpus hashes cone_truth_bigint's LSB-first axes. Packed
    # evaluators use the first key as the MSB axis, so reverse the live key.
    variables = tuple(
        reversed(
            tuple(
                name
                for name in all_variables
                if int(name[1:]) in live_positions
            )
        )
    )
    fixed = {
        name: 0 for name in all_variables if int(name[1:]) not in live_positions
    }
    if len(variables) != live_k:
        raise AssertionError(
            f"{record.get('id')}: live_k={live_k}, variables={variables!r}"
        )
    return variables, fixed


def _require_truth_digest(record: Mapping[str, Any], packed: int, live_k: int) -> str:
    output_bytes = max(1, (1 << live_k) // 8)
    actual = hashlib.sha256(int(packed).to_bytes(output_bytes, "little")).hexdigest()
    expected = record.get("truth_sha256")
    if not isinstance(expected, str) or not expected:
        raise AssertionError(f"{record.get('id')}: missing frozen truth digest")
    if actual != expected:
        raise AssertionError(
            f"{record.get('id')}: truth drift: expected {expected}, got {actual}"
        )
    return actual


def _verify_frozen_truth(
    corpus: str,
    record: Mapping[str, Any],
    expr: Any,
    packed_live_result: int,
    live_k: int,
) -> str:
    """Verify the corpus digest at the width/order in which it was frozen."""
    if corpus != "epfl":
        return _require_truth_digest(record, packed_live_result, live_k)

    # EPFL truth_sha256 covers the original syntactic-support truth table, even
    # when semantic-support analysis later identifies a dead input. Expand the
    # reduced result across those proven-dead axes before checking the immutable
    # artifact. This validates the variable map/order without reevaluating a
    # potentially huge expression tree a second time.
    syntactic_k = int(record.get("synt_support_size") or 0)
    if syntactic_k <= 0:
        raise AssertionError(f"{record.get('id')}: missing syntactic support size")
    syntactic_inputs = list(record.get("synt_support_inputs") or ())
    semantic_inputs = set(record.get("sem_support_inputs") or ())
    if len(syntactic_inputs) != syntactic_k:
        raise AssertionError(f"{record.get('id')}: malformed syntactic support")
    live_positions = tuple(
        position
        for position, original_input in enumerate(syntactic_inputs)
        if original_input in semantic_inputs
    )
    if len(live_positions) != live_k:
        raise AssertionError(f"{record.get('id')}: malformed semantic support")
    if syntactic_k == live_k:
        frozen_packed = packed_live_result
    else:
        live_bytes = int(packed_live_result).to_bytes(
            max(1, (1 << live_k) // 8), "little"
        )
        frozen_bytes = bytearray(max(1, (1 << syntactic_k) // 8))
        for syntactic_row in range(1 << syntactic_k):
            semantic_row = 0
            for semantic_position, syntactic_position in enumerate(live_positions):
                semantic_row |= (
                    (syntactic_row >> syntactic_position) & 1
                ) << semantic_position
            if live_bytes[semantic_row >> 3] & (1 << (semantic_row & 7)):
                frozen_bytes[syntactic_row >> 3] |= 1 << (syntactic_row & 7)
        frozen_packed = int.from_bytes(frozen_bytes, "little")
    return _require_truth_digest(record, frozen_packed, syntactic_k)


def _node_count_profile(node: Any, repetitions: int) -> tuple[float, float]:
    cold_samples: list[int] = []
    warm_samples: list[int] = []
    for _ in range(repetitions):
        if "_node_count" in node.__dict__:
            object.__delattr__(node, "_node_count")
        start = time.perf_counter_ns()
        _cm_node_count(node)
        cold_samples.append(time.perf_counter_ns() - start)
        start = time.perf_counter_ns()
        _cm_node_count(node)
        warm_samples.append(time.perf_counter_ns() - start)
    return (
        float(statistics.median(cold_samples)),
        float(statistics.median(warm_samples)),
    )


def _measure_record(
    corpus: str,
    record: Mapping[str, Any],
    repetitions: int,
    rounds: int,
    max_kernel_temporary_bytes: int,
) -> dict[str, Any]:
    expression_doc = record["expression_v2"]
    expr = expr_from_json(expression_doc)
    k = int(
        record.get("live_k")
        or record.get("stratum_live_k")
        or record.get("sem_support_size")
    )
    variables, fixed = _evaluation_context(corpus, record, expr, k)

    hash_ns, structural_hash = _median_ns(lambda: expr_structural_hash(expr), repetitions)
    serde_ns, serde_doc = _median_ns(lambda: expr_to_json_dag(expr), repetitions)
    json_ns, serde_text = _median_ns(
        lambda: json.dumps(serde_doc, separators=(",", ":"), sort_keys=True), repetitions
    )
    compile_profile, node = _compile_profile(expr, repetitions)
    assert node is not None
    node_count_cold_ns, node_count_warm_ns = _node_count_profile(node, repetitions)
    lower_ns, lowered = _median_ns(lambda: compile_flat(node), repetitions)
    raw_arm_allowed = str(record.get("raw_arm", "ok")) == "ok"
    raw_lower_ns = None
    raw_program = None
    if raw_arm_allowed:
        raw_lower_ns, raw_program = _median_ns(lambda: compile_expr_flat(expr), repetitions)
    cm_program = get_flat_program(node)
    cm_metrics = program_metrics(cm_program)
    raw_metrics = program_metrics(raw_program) if raw_program is not None else None

    batch = _batch_for(k)
    n_words = 0 if k < 6 else (1 << k) // 64
    output_bytes = max(1, (1 << k) // 8)
    raw_flat_temporary = (
        int(raw_program.n_slots) * output_bytes if raw_program is not None else None
    )
    raw_words_temporary = (
        int(raw_metrics["peak_live_word_buffers"]) * n_words * 8 + k * n_words * 8
        if raw_metrics is not None
        else None
    )
    raw_kernel_eligible = bool(
        raw_arm_allowed
        and raw_flat_temporary is not None
        and raw_words_temporary is not None
        and max(raw_flat_temporary, raw_words_temporary) <= max_kernel_temporary_bytes
    )
    raw_flat_ns = raw_words_ns = None
    raw_flat = raw_words = None
    if raw_kernel_eligible:
        raw_flat_ns, raw_words_ns, raw_flat, raw_words = _paired_per_call_ns(
            lambda: eval_expr_flat_bitset(expr, variables, fixed=fixed),
            lambda: eval_expr_words_bitset(expr, variables, fixed=fixed),
            batch=batch,
            rounds=rounds,
        )
    cm_flat_ns, cm_words_ns, cm_flat, cm_words = _paired_per_call_ns(
        lambda: eval_cm_node_flat(node, variables, fixed=fixed),
        lambda: eval_cm_node_words(node, variables, fixed=fixed),
        batch=batch,
        rounds=rounds,
    )
    if cm_flat != cm_words or (
        raw_kernel_eligible and not (raw_flat == raw_words == cm_flat)
    ):
        raise AssertionError(f"{record.get('id')}: packed engine mismatch")
    frozen_truth_sha256_verified = _verify_frozen_truth(
        corpus, record, expr, cm_flat, k
    )
    packed_sha256 = hashlib.sha256(
        int(cm_flat).to_bytes(output_bytes, "little")
    ).hexdigest()

    wrapper_ns, wrapper_result = _median_ns(
        lambda: materialize_hybrid_no_reinflate(
            node,
            variables,
            fixed=fixed,
            hybrid_threshold=16,
            flat_eval=True,
            words_eval=True,
            output_budget=None,
        ),
        repetitions,
    )
    if int(wrapper_result.bits) != cm_flat:
        raise AssertionError(f"{record.get('id')}: wrapper mismatch")

    end_to_end_ns, end_result = _median_ns(
        lambda: _compile_and_evaluate(expr, variables, fixed), repetitions
    )
    if int(end_result.bits) != cm_flat:
        raise AssertionError(f"{record.get('id')}: end-to-end mismatch")

    return {
        "corpus": corpus,
        "role": "tuning" if corpus == "bx1" else "validation_reused",
        "id": str(record.get("id")),
        "seed": record.get("seed"),
        "truth_sha256_expected": record.get("truth_sha256"),
        "frozen_truth_sha256_verified": frozen_truth_sha256_verified,
        "source_circuit_sha256": record.get("circuit_sha256"),
        "cluster": str(record.get("circuit") or record.get("op_family") or "unknown"),
        "live_k": k,
        "structural_dag_nodes_source": int(record.get("structural_dag_nodes") or len(expression_doc["nodes"])),
        "unfolded_tree_nodes": int(record.get("unfolded_occurrences") or _expr_tree_occurrences(expr)),
        "ir_nodes": _ir_nodes(node),
        "node_count_cold_ns_median": node_count_cold_ns,
        "node_count_warm_ns_median": node_count_warm_ns,
        "cm_instructions": int(cm_metrics["flat_instructions"]),
        "cm_executed_bigint_ops": int(cm_metrics["executed_bigint_ops"]),
        "cm_executed_word_ops": int(cm_metrics["executed_word_ops"]),
        "cm_peak_live_word_buffers": int(cm_metrics["peak_live_word_buffers"]),
        "raw_instructions": int(raw_metrics["flat_instructions"]) if raw_metrics else None,
        "raw_executed_bigint_ops": int(raw_metrics["executed_bigint_ops"]) if raw_metrics else None,
        "raw_executed_word_ops": int(raw_metrics["executed_word_ops"]) if raw_metrics else None,
        "hash_ns_median": hash_ns,
        "serde_ns_median": serde_ns,
        "json_encode_ns_median": json_ns,
        "serde_bytes": len(serde_text.encode("utf-8")),
        **compile_profile,
        "lower_cm_ns_median": lower_ns,
        "lower_raw_ns_median": raw_lower_ns,
        "raw_kernel_status": (
            "ok"
            if raw_kernel_eligible
            else "skipped_source_protocol"
            if not raw_arm_allowed
            else "refused_temporary_budget"
        ),
        "raw_flat_ns_median": raw_flat_ns,
        "raw_words_ns_median": raw_words_ns,
        "cm_flat_ns_median": cm_flat_ns,
        "cm_words_ns_median": cm_words_ns,
        "wrapper_current_ns_median": wrapper_ns,
        "end_to_end_current_ns_median": end_to_end_ns,
        "raw_words_over_flat": (
            raw_words_ns / raw_flat_ns if raw_kernel_eligible else None
        ),
        "cm_words_over_flat": cm_words_ns / cm_flat_ns,
        "wrapper_over_selected_bare": wrapper_ns / (
            cm_words_ns if k >= WORDS_AUTO_MIN_VARS else cm_flat_ns
        ),
        "packed_sha256": packed_sha256,
        "packed_digest_scope": "semantic_live_support",
        "packed_equal": True,
        "output_bytes_exact": output_bytes,
        "words_environment_bytes_estimate": k * n_words * 8,
        "raw_flat_temporary_bytes_estimate": raw_flat_temporary,
        "raw_word_scratch_bytes_estimate": (
            int(raw_metrics["peak_live_word_buffers"]) * n_words * 8
            if raw_metrics
            else None
        ),
        "cm_word_scratch_bytes_estimate": int(cm_metrics["peak_live_word_buffers"]) * n_words * 8,
        "max_kernel_temporary_bytes": max_kernel_temporary_bytes,
        "kernel_batch": batch,
        "kernel_rounds": rounds,
        "structural_hash": structural_hash,
    }


def _walk_vars(expr: Any) -> Iterable[Any]:
    seen: set[int] = set()
    stack = [expr]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if type(cur).__name__ == "Var":
            yield cur
        else:
            if hasattr(cur, "a"):
                stack.append(cur.a)
            if hasattr(cur, "b"):
                stack.append(cur.b)


def _compile_and_evaluate(
    expr: Any, variables: Sequence[str], fixed: Mapping[str, int]
) -> Any:
    node = compile_expr_to_cm_ir(expr)
    return materialize_hybrid_no_reinflate(
        node,
        variables,
        fixed=dict(fixed),
        hybrid_threshold=16,
        flat_eval=True,
        words_eval=True,
        output_budget=None,
    )


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    index = fraction * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _geomean(values: Sequence[float]) -> float:
    return float(statistics.geometric_mean(values)) if values else float("nan")


def _cluster_bootstrap_geomean(
    rows_and_regrets: Sequence[tuple[Mapping[str, Any], float]],
    *,
    seed_label: str,
    repetitions: int = 2_000,
) -> tuple[int, float, float]:
    by_cluster: dict[tuple[str, str], list[float]] = {}
    for row, regret in rows_and_regrets:
        key = (str(row["corpus"]), str(row["cluster"]))
        by_cluster.setdefault(key, []).append(regret)
    clusters = sorted(by_cluster)
    if not clusters:
        return 0, float("nan"), float("nan")
    seed = int.from_bytes(hashlib.sha256(seed_label.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    estimates = []
    for _ in range(repetitions):
        sampled = [rng.choice(clusters) for _ in clusters]
        estimates.append(
            _geomean([value for cluster in sampled for value in by_cluster[cluster]])
        )
    return len(clusters), _percentile(estimates, 0.025), _percentile(estimates, 0.975)


def _selector_summary(rows: Sequence[Mapping[str, Any]], arm: str) -> list[dict[str, Any]]:
    flat_key = f"{arm}_flat_ns_median"
    words_key = f"{arm}_words_ns_median"

    def selected(row: Mapping[str, Any], threshold: int) -> float:
        k = int(row["live_k"])
        flat = float(row[flat_key])
        words = float(row[words_key])
        return words if k >= threshold else flat

    summaries: list[dict[str, Any]] = []
    roles = sorted(
        {str(row["role"]) for row in rows},
        key=lambda role: (role != "tuning", role),
    )
    for role in roles:
        role_subset = [row for row in rows if row["role"] == role]
        subset = [
            row
            for row in role_subset
            if row.get(flat_key) not in (None, "") and row.get(words_key) not in (None, "")
        ]
        for threshold in range(6, 17):
            regrets = []
            rows_and_regrets = []
            catastrophic = 0
            for row in subset:
                best = min(float(row[flat_key]), float(row[words_key]))
                regret = selected(row, threshold) / best
                regrets.append(regret)
                rows_and_regrets.append((row, regret))
                catastrophic += int(regret >= 2.0)
            cluster_count, ci_low, ci_high = _cluster_bootstrap_geomean(
                rows_and_regrets,
                seed_label=f"{arm}:{role}:{threshold}",
            )
            summaries.append(
                {
                    "arm": arm,
                    "role": role,
                    "policy": f"threshold_k{threshold}",
                    "words_auto_min_vars": threshold,
                    "is_current_policy": threshold == WORDS_AUTO_MIN_VARS,
                    "n": len(subset),
                    "refused_or_ineligible_count": len(role_subset) - len(subset),
                    "cluster_count": cluster_count,
                    "regret_geomean": _geomean(regrets),
                    "regret_geomean_cluster_bootstrap_ci95_low": ci_low,
                    "regret_geomean_cluster_bootstrap_ci95_high": ci_high,
                    "regret_median": float(statistics.median(regrets)) if regrets else None,
                    "regret_p90": _percentile(regrets, 0.9),
                    "regret_max": max(regrets) if regrets else None,
                    "catastrophic_ge_2_count": catastrophic,
                    "catastrophic_ge_2_rate": catastrophic / len(subset) if subset else None,
                }
            )
    return summaries


def _phase_summary(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for corpus in sorted({str(row["corpus"]) for row in rows}):
        subset = [row for row in rows if row["corpus"] == corpus]
        compile_ns = [float(row["compile_external_ns"]) for row in subset]
        for field in (
            "hash_ns_median",
            "ir_canonicalize_ns",
            "ir_rewrite_ns",
            "ir_intern_ns",
            "ir_live_vars_ns",
            "lower_cm_ns_median",
            "wrapper_current_ns_median",
            "end_to_end_current_ns_median",
        ):
            values = [float(row[field]) for row in subset]
            output.append(
                {
                    "corpus": corpus,
                    "field": field,
                    "n": len(values),
                    "median_ns": float(statistics.median(values)),
                    "p10_ns": _percentile(values, 0.1),
                    "p90_ns": _percentile(values, 0.9),
                    "median_fraction_of_compile": (
                        float(statistics.median([v / c for v, c in zip(values, compile_ns)]))
                        if field not in {"wrapper_current_ns_median", "end_to_end_current_ns_median"}
                        else None
                    ),
                }
            )
    return output


def _git(*args: str) -> str:
    import subprocess

    try:
        return subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()
    except OSError:
        # Source-only benchmark archives intentionally may not contain a git
        # executable or checkout.  Source and corpus SHA-256 fields remain the
        # controlling provenance in that environment.
        return ""


def _process_affinity() -> dict[str, Any]:
    if hasattr(os, "sched_getaffinity"):
        cpus = sorted(os.sched_getaffinity(0))
        return {"kind": "cpu_indices", "cpus": cpus, "logical_cpu_count": len(cpus)}
    if os.name == "nt":
        import ctypes

        process_mask = ctypes.c_size_t()
        system_mask = ctypes.c_size_t()
        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.GetProcessAffinityMask.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.POINTER(ctypes.c_size_t),
        )
        kernel32.GetProcessAffinityMask.restype = ctypes.c_int
        ok = kernel32.GetProcessAffinityMask(
            kernel32.GetCurrentProcess(),
            ctypes.byref(process_mask),
            ctypes.byref(system_mask),
        )
        if ok:
            return {
                "kind": "windows_mask",
                "process_mask_hex": hex(process_mask.value),
                "system_mask_hex": hex(system_mask.value),
                "logical_cpu_count": process_mask.value.bit_count(),
            }
    return {"kind": "unavailable"}


def _version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _environment(command: Sequence[str], suite: str, corpora: Sequence[str]) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "command": list(command),
        "suite": suite,
        "corpora": list(corpora),
        "git_branch": _git("branch", "--show-current"),
        "git_head": _git("rev-parse", "HEAD"),
        "git_status_short": _git("status", "--short").splitlines(),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "process_affinity": _process_affinity(),
        "thread_settings": {
            name: os.environ.get(name)
            for name in (
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS",
            )
        },
        "seed_policy": "per-record seeds when present; otherwise immutable circuit/root IDs",
        "role_policy": (
            "BX1 is tuning; B2 and EPFL are reused selection-validation data, "
            "not untouched held-out data"
        ),
        "dependencies": {name: _version(name) for name in ("numpy", "pandas", "sympy", "dd", "numba")},
        "source_sha256": source_hashes(REPO_ROOT, SOURCE_PATHS),
        "corpus_sha256": {
            name: hashlib.sha256(CORPORA[name].read_bytes()).hexdigest() for name in corpora
        },
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("smoke", "representative"), default="smoke")
    parser.add_argument("--corpora", default="bx1,b2,epfl")
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--prep-repetitions", type=int, default=5)
    parser.add_argument("--kernel-rounds", type=int, default=7)
    parser.add_argument("--max-kernel-temporary-bytes", type=int, default=1 << 28)
    args = parser.parse_args()
    corpora = tuple(item.strip() for item in args.corpora.split(",") if item.strip())
    unknown = set(corpora) - set(CORPORA)
    if unknown:
        parser.error(f"unknown corpora: {sorted(unknown)}")
    if args.prep_repetitions < 3 or args.kernel_rounds < 3:
        parser.error("repetition counts must be at least 3")

    prefix = args.output_prefix
    paths = {
        "raw": prefix.with_name(prefix.name + "_raw.csv"),
        "summary": prefix.with_name(prefix.name + "_summary.json"),
        "selector": prefix.with_name(prefix.name + "_selector.csv"),
        "phases": prefix.with_name(prefix.name + "_phases.csv"),
        "environment": prefix.with_name(prefix.name + "_environment.json"),
    }
    snapshot_dir = prefix.with_name(prefix.name + "_source_snapshot")
    existing = [str(path) for path in (*paths.values(), snapshot_dir) if path.exists()]
    if existing:
        parser.error("refusing to overwrite existing outputs: " + ", ".join(existing))
    prefix.parent.mkdir(parents=True, exist_ok=True)

    clear_cm_ir_compile_cache()
    clear_cm_ir_persistent_cache()
    rows: list[dict[str, Any]] = []
    for corpus in corpora:
        records = _sample_records(corpus, args.suite)
        for index, record in enumerate(records, 1):
            row = _measure_record(
                corpus,
                record,
                args.prep_repetitions,
                args.kernel_rounds,
                args.max_kernel_temporary_bytes,
            )
            rows.append(row)
            print(
                f"{corpus} {index}/{len(records)} {row['id']}: "
                f"compile={row['compile_external_ns']/1e3:.1f}us "
                f"raw words/flat={row['raw_words_over_flat'] if row['raw_words_over_flat'] is not None else row['raw_kernel_status']} "
                f"cm words/flat={row['cm_words_over_flat']:.2f}"
            )

    selector = _selector_summary(rows, "raw") + _selector_summary(rows, "cm")
    phases = _phase_summary(rows)
    environment = _environment(sys.argv, args.suite, corpora)
    environment["source_snapshot"] = capture_source_snapshot(
        REPO_ROOT, snapshot_dir, SOURCE_PATHS
    )
    summary = {"environment": environment, "selector": selector, "phases": phases}
    _write_csv(paths["raw"], rows)
    _write_csv(paths["selector"], selector)
    _write_csv(paths["phases"], phases)
    paths["summary"].write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["environment"].write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for path in paths.values():
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
