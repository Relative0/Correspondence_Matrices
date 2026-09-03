"""Development-only ANF-basis GF(2)-rank validation and timing study."""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import statistics
import time
import tracemalloc
from typing import Any

from bitset_backend import build_bitset_env, eval_expr_bitset
from cm_expr_serde import expr_from_json
from cmbench.recognition.decomposition_data import packed_sha256
from cmbench.recognition.gf2_anf_rank import (
    anf_rank,
    anf_rank_factor_to_truth,
    normalize_source_anf,
    packed_anf_from_truth,
    truth_partition_rows,
)
from cmbench.recognition.gf2_decomposition import candidate_partitions, gf2_rank_factor
from cmbench.recognition.source_anf_hybrid import source_anf_packed

from .contracts import canonical_bytes
from .gf2_restricted_evaluator_experiment import (
    _environment,
    _rss_snapshot,
    collect_reproducibility_manifest,
)
from .schedule import balanced_orders


SCHEMA = "crse-anf-rank-development/v1"
RAW_SCHEMA = "crse-anf-rank-raw-session/v1"
METHODS = (
    "truth_rank_screen",
    "anf_rank_screen_from_truth",
    "anf_rank_factor_from_truth",
    "anf_rank_screen_precomputed",
)
QUERY_PARTITIONS = 64
EXTRA_MANIFEST_SOURCES = (
    "cmbench/recognition/gf2_anf_rank.py",
    "cmbench/comparative/gf2_anf_rank_experiment.py",
    "scripts/cm_comparative_anf_rank_development.py",
    "scripts/crse_anf_rank_development_verify.py",
    "docs/recognition/c16_linux_confirmation/c16_dataset.json",
)


@dataclass(frozen=True)
class ANFRankConfig:
    run_id: str
    seed: int = 20260902
    blocks: int = 4
    development_speedup_gate: float = 1.10
    max_seconds: float = 900.0

    def validate(self) -> None:
        if (
            not self.run_id or self.blocks != len(METHODS)
            or self.development_speedup_gate != 1.10
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 60 <= self.max_seconds <= 1800
        ):
            raise ValueError("invalid ANF-rank development bounds")


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


def four_variable_partitions() -> tuple[tuple[int, ...], ...]:
    return tuple(row for size in range(1, 4)
                 for row in itertools.combinations(range(4), size) if 0 in row)


def exhaustive_four_variable_validation(
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Check all 65,536 functions, seven unique nontrivial partitions each."""
    partitions = four_variable_partitions()
    accumulator = hashlib.sha256()
    checks = 0
    for bits in range(1 << (1 << 4)):
        polynomial = packed_anf_from_truth(bits, 4)
        for row in partitions:
            factor = anf_rank_factor_to_truth(
                polynomial, 4, row, expected_truth_bits=bits)
            accumulator.update(bytes((factor.rank,)))
            checks += 1
        if progress is not None and (bits + 1) % 8192 == 0:
            progress(bits + 1, 1 << (1 << 4))
    return {
        "functions": 1 << (1 << 4),
        "partitions_per_function": len(partitions),
        "function_partition_checks": checks,
        "rank_and_factor_mismatches": 0,
        "rank_trace_sha256": accumulator.hexdigest(),
    }


def prepare_c16_cases(dataset: Mapping[str, Any]) -> list[dict[str, Any]]:
    cases = dataset.get("cases")
    if dataset.get("schema") != "crse-c16-gf2-screened-tail-dataset/v1" \
            or not isinstance(cases, list) or len(cases) != 40:
        raise ValueError("invalid C16 ANF-rank dataset")
    prepared = []
    for case in cases:
        n_vars = case["n_vars"]
        expression = expr_from_json(case["expression_v2"])
        names = tuple(f"x{i}" for i in range(n_vars))
        bits = eval_expr_bitset(expression, build_bitset_env(names))
        if packed_sha256(bits, n_vars) != case["semantic_sha256"]:
            raise ValueError("C16 ANF-rank semantic binding")
        polynomial = packed_anf_from_truth(bits, n_vars)
        source_polynomial, _stats = source_anf_packed(case["expression_v2"], n_vars)
        if normalize_source_anf(source_polynomial, n_vars) != polynomial:
            raise ValueError("C16 source/truth ANF mismatch")
        partitions = candidate_partitions(bits, n_vars, QUERY_PARTITIONS)
        expected_ranks = tuple(gf2_rank_factor(
            truth_partition_rows(bits, n_vars, row), 1 << (n_vars - len(row)))[0]
            for row in partitions)
        prepared.append({
            "case_id": case["case_id"],
            "family": case["family"],
            "n_vars": n_vars,
            "bits": bits,
            "polynomial": polynomial,
            "anf_terms": polynomial.bit_count(),
            "partitions": partitions,
            "expected_ranks": expected_ranks,
            "expected_sha256": _digest({
                "partitions": [list(row) for row in partitions],
                "ranks": list(expected_ranks),
            }),
        })
    return prepared


def build_schedule(cases: Sequence[Mapping[str, Any]], blocks: int,
                   seed: int) -> list[dict[str, Any]]:
    orders = balanced_orders(METHODS)[:len(METHODS)]
    if blocks != len(orders):
        raise ValueError("ANF-rank schedule requires one counterbalance cycle")
    rows = []
    for block in range(blocks):
        shuffled = list(cases)
        random.Random(f"anf-rank:{seed}:{block}").shuffle(shuffled)
        order = orders[(block + seed) % len(orders)]
        for position, case in enumerate(shuffled):
            core = {
                "block": block,
                "cell_position": position,
                "case_id": case["case_id"],
                "family": case["family"],
                "n_vars": case["n_vars"],
                "method_order": list(order),
            }
            core["order_sha256"] = _digest(core)
            rows.append(core)
    return rows


def validate_schedule(rows: Sequence[Mapping[str, Any]],
                      cases: Sequence[Mapping[str, Any]], blocks: int) -> None:
    if len(rows) != len(cases) * blocks:
        raise ValueError("ANF-rank schedule cardinality")
    case_ids = {case["case_id"] for case in cases}
    for row in rows:
        core = {key: row[key] for key in (
            "block", "cell_position", "case_id", "family", "n_vars", "method_order")}
        if row.get("order_sha256") != _digest(core) \
                or row["case_id"] not in case_ids \
                or set(row["method_order"]) != set(METHODS):
            raise ValueError("ANF-rank schedule identity")
    for case_id in case_ids:
        selected = [row for row in rows if row["case_id"] == case_id]
        if Counter(row["block"] for row in selected) != Counter(range(blocks)):
            raise ValueError("ANF-rank block balance")
        for method in METHODS:
            positions = Counter(row["method_order"].index(method) for row in selected)
            if positions != Counter({index: 1 for index in range(len(METHODS))}):
                raise ValueError("ANF-rank arm-position balance")


def _rss() -> tuple[int | None, int | None]:
    return _rss_snapshot()


def execute_session(
    *, case: Mapping[str, Any], method: str, role: str,
    clock: Callable[[], int] = time.perf_counter_ns,
    profile_python_allocations: bool = False,
) -> dict[str, Any]:
    if method not in METHODS or role not in ("performance", "memory_profile"):
        raise ValueError("invalid ANF-rank session")
    if profile_python_allocations:
        tracemalloc.start()
    start_rss, _start_peak = _rss()
    bits = case["bits"]
    n_vars = case["n_vars"]
    partitions = case["partitions"]
    polynomial = case["polynomial"] if method == "anf_rank_screen_precomputed" else None

    started = clock()
    if method in ("anf_rank_screen_from_truth", "anf_rank_factor_from_truth"):
        polynomial = packed_anf_from_truth(bits, n_vars)
    anf_construction_ns = max(1, clock() - started)

    started = clock()
    reconstructed_rows: list[tuple[int, ...]] | None = None
    if method == "truth_rank_screen":
        ranks = tuple(gf2_rank_factor(
            truth_partition_rows(bits, n_vars, row), 1 << (n_vars - len(row)))[0]
            for row in partitions)
    elif method in ("anf_rank_screen_from_truth", "anf_rank_screen_precomputed"):
        ranks = tuple(anf_rank(polynomial, n_vars, row) for row in partitions)
    else:
        factors = tuple(anf_rank_factor_to_truth(polynomial, n_vars, row)
                        for row in partitions)
        ranks = tuple(factor.rank for factor in factors)
        reconstructed_rows = [factor.reconstruct_truth_rows() for factor in factors]
    rank_or_factor_ns = max(1, clock() - started)

    started = clock()
    document = {"partitions": [list(row) for row in partitions], "ranks": list(ranks)}
    artifact_sha256 = _digest(document)
    delivery_ns = max(1, clock() - started)
    if ranks != case["expected_ranks"] or artifact_sha256 != case["expected_sha256"]:
        raise RuntimeError("ANF-rank method failed rank oracle")
    if reconstructed_rows is not None:
        expected_rows = [truth_partition_rows(bits, n_vars, row) for row in partitions]
        if reconstructed_rows != expected_rows:
            raise RuntimeError("ANF-rank timed factor failed truth reconstruction")
    total_ns = anf_construction_ns + rank_or_factor_ns + delivery_ns
    end_rss, process_peak = _rss()
    resources = {
        "partitions": len(partitions),
        "anf_terms": case["anf_terms"],
        "anf_density": case["anf_terms"] / (1 << n_vars),
        "input_lifecycle": (
            "precomputed_existing_anf" if method == "anf_rank_screen_precomputed"
            else "truth_input"),
        "session_sampled_peak_rss_delta_bytes": (
            max(0, end_rss - start_rss)
            if start_rss is not None and end_rss is not None else None),
        "process_peak_rss_bytes": process_peak,
    }
    if profile_python_allocations:
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        resources["tracemalloc_peak_bytes"] = int(peak)
    return {
        "schema": RAW_SCHEMA,
        "role": role,
        "case_id": case["case_id"],
        "family": case["family"],
        "n_vars": n_vars,
        "method": method,
        "status": "ok",
        "timings_ns": {
            "anf_construction_ns": anf_construction_ns,
            "rank_or_factor_ns": rank_or_factor_ns,
            "delivery_ns": delivery_ns,
            "accounted_total_ns": total_ns,
        },
        "artifact_sha256": artifact_sha256,
        "exact_check_passed": True,
        "resources": resources,
    }


def summarize(rows: Sequence[Mapping[str, Any]], speedup_gate: float) -> dict[str, Any]:
    performance = [row for row in rows if row["role"] == "performance"]
    cases = sorted({row["case_id"] for row in performance})
    samples: dict[tuple[str, str], list[int]] = {}
    for row in performance:
        samples.setdefault((row["case_id"], row["method"]), []).append(
            row["timings_ns"]["accounted_total_ns"])
    medians = {key: int(statistics.median(values)) for key, values in samples.items()}
    totals = {method: sum(medians[(case, method)] for case in cases) for method in METHODS}
    speedups = {method: totals["truth_rank_screen"] / total
                for method, total in totals.items()}
    by_width = {}
    metadata = {row["case_id"]: row["n_vars"] for row in performance}
    for width in sorted(set(metadata.values())):
        selected = [case for case in cases if metadata[case] == width]
        width_totals = {method: sum(medians[(case, method)] for case in selected)
                        for method in METHODS}
        by_width[str(width)] = {
            "cases": len(selected),
            "method_total_ns": width_totals,
            "best_method": min(METHODS,
                               key=lambda method: (width_totals[method], method)),
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
    complete_speedup = speedups["anf_rank_screen_from_truth"]
    precomputed_speedup = speedups["anf_rank_screen_precomputed"]
    return {
        "cases": len(cases),
        "performance_sessions": len(performance),
        "memory_profile_sessions": len(memory_rows),
        "method_total_ns": totals,
        "speedup_over_truth_rank_screen": speedups,
        "best_method": min(METHODS, key=lambda method: (totals[method], method)),
        "by_width": by_width,
        "memory_profiles": memory,
        "decision": {
            "development_speedup_gate": speedup_gate,
            "complete_from_truth_speedup": complete_speedup,
            "precomputed_anf_speedup": precomputed_speedup,
            "complete_from_truth_gate_passed": complete_speedup >= speedup_gate,
            "precomputed_anf_gate_passed": precomputed_speedup >= speedup_gate,
            "production_integration_permitted": False,
        },
        "timing_is_local_and_machine_specific": True,
        "memory_timing_excluded_from_performance_summary": True,
    }


def render_protocol(config: ANFRankConfig, dataset_path: Path, root: Path) -> str:
    return "\n".join([
        "# ANF-basis GF(2)-rank development protocol", "",
        f"Run ID: `{config.run_id}`", "",
        "Development-only mathematical and performance adjudication; not C37.",
        "All 65,536 four-variable Boolean functions and seven unique nontrivial",
        "partitions are checked for rank equality and exact factor conversion.",
        "The exposed C16 cohort then compares truth-basis rank screening, ANF",
        "screening including ANF construction, ANF factor conversion, and ANF",
        "screening when the exact source ANF already exists.", "",
        f"Dataset: `{dataset_path.relative_to(root).as_posix()}`",
        f"Blocks: {config.blocks}; seed: {config.seed}; gate: "
        f"{config.development_speedup_gate:.2f}x.", "",
    ])


def render_report(result: Mapping[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# ANF-basis GF(2)-rank development result", "",
        f"Status: **{result['status']}**", "",
        f"Exhaustive checks: {result['exhaustive_validation']['function_partition_checks']:,}; mismatches: 0.",
        "", "| Method | Total ms | Speedup vs truth rank |",
        "|---|---:|---:|",
    ]
    for method in METHODS:
        lines.append(
            f"| {method} | {summary['method_total_ns'][method] / 1e6:.3f} | "
            f"{summary['speedup_over_truth_rank_screen'][method]:.4f}x |")
    decision = summary["decision"]
    lines += ["", "## Decision", "",
              f"Complete ANF-from-truth gate: **{'passed' if decision['complete_from_truth_gate_passed'] else 'did not pass'}**.",
              f"Precomputed-ANF gate: **{'passed' if decision['precomputed_anf_gate_passed'] else 'did not pass'}**.",
              "No production integration is permitted by this development run.", ""]
    return "\n".join(lines)


def run(
    config: ANFRankConfig, output: Path, dataset_path: Path, root: Path,
    *, progress: Callable[[str, int, int, str], None] | None = None,
) -> dict[str, Any]:
    config.validate()
    wall_started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    (output / "protocol.md").write_text(
        render_protocol(config, dataset_path, root), encoding="utf-8", newline="\n")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    exhaustive = exhaustive_four_variable_validation(
        None if progress is None else lambda current, total: progress(
            "exhaustive", current, total, "all-four-variable-functions"))
    cases = prepare_c16_cases(dataset)
    schedule = build_schedule(cases, config.blocks, config.seed)
    validate_schedule(schedule, cases, config.blocks)
    case_map = {case["case_id"]: case for case in cases}
    rows: list[dict[str, Any]] = []
    for index, planned in enumerate(schedule):
        case = case_map[planned["case_id"]]
        for method_position, method in enumerate(planned["method_order"]):
            session = execute_session(case=case, method=method, role="performance")
            session.update({
                "block": planned["block"], "cell_position": planned["cell_position"],
                "method_position": method_position,
                "method_order": planned["method_order"],
                "order_sha256": planned["order_sha256"],
            })
            rows.append(session)
        if progress is not None:
            progress("performance", index + 1, len(schedule), case["case_id"])
        if time.perf_counter() - wall_started > config.max_seconds:
            raise TimeoutError("ANF-rank experiment exceeded wall bound")
    memory_total = len(cases) * len(METHODS)
    memory_index = 0
    orders = balanced_orders(METHODS)
    for case_index, case in enumerate(cases):
        order = orders[case_index % len(orders)]
        for method_position, method in enumerate(order):
            session = execute_session(
                case=case, method=method, role="memory_profile",
                profile_python_allocations=True)
            session.update({
                "block": None, "cell_position": case_index,
                "method_position": method_position, "method_order": list(order),
                "order_sha256": _digest({
                    "role": "memory_profile", "case_id": case["case_id"],
                    "method_order": list(order)}),
            })
            rows.append(session)
            memory_index += 1
            if progress is not None:
                progress("memory", memory_index, memory_total, case["case_id"])
    _write_jsonl(output / "raw_measurements.jsonl", rows)
    summary = summarize(rows, config.development_speedup_gate)
    result = {
        "schema": SCHEMA, "status": "complete", "run_id": config.run_id,
        "config": asdict(config),
        "methods": list(METHODS),
        "dataset": {"path": dataset_path.relative_to(root).as_posix(),
                    "sha256": _sha256(dataset_path),
                    "classification": "development_exposed_c16_not_confirmation"},
        "exhaustive_validation": exhaustive,
        "source_anf_validation": {"cases": len(cases), "mismatches": 0},
        "summary": summary,
        "decision": {"production_write": False, "production_promotion": False,
                     "prospective_data_consumed": False},
        "elapsed_seconds": time.perf_counter() - wall_started,
    }
    _write_json(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    environment = _environment(root, dataset_path, dataset_path)
    environment["schema"] = "crse-anf-rank-environment/v1"
    _write_json(output / "environment.json", environment)
    artifact_names = ("protocol.md", "raw_measurements.jsonl", "environment.json",
                      "results.json", "report.md")
    artifacts = {name: _sha256(output / name) for name in artifact_names}
    _write_json(output / "manifest.json", collect_reproducibility_manifest(
        root, artifacts, EXTRA_MANIFEST_SOURCES))
    return result
