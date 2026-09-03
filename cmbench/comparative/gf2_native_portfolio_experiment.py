"""Cache-isolated development comparison of native slots and exact C36 engines."""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random
import shutil
import statistics
import sys
import time
from typing import Any

from bitset_backend import clear_bitset_env_cache, clear_words_env_cache

from .gf2_multi_query_batch_experiment import execute_session as execute_engine_session
from .gf2_native_slot_experiment import (
    _environment,
    _rss_bytes,
    execute_native_session,
)
from .gf2_native_slots import NativeSlotLibrary, load_native_slot_library
from .gf2_projection_optimization_experiment import (
    _digest,
    _sha256,
    _write_json,
    _write_text,
    execute_session as execute_projection_session,
)
from .gf2_wide_repeated_queries import oracle_document, validate_dataset
from .schedule import balanced_orders


SCHEMA = "crse-native-portfolio-development/v1"
RAW_SCHEMA = "crse-native-portfolio-raw-session/v1"
MANIFEST_SCHEMA = "crse-native-portfolio-manifest/v1"
METHODS = (
    "r2_per_query",
    "cse_bigint",
    "cse_words",
    "cm_ir_bigint",
    "cm_ir_words",
    "projection_u16_tuple",
    "native_fused_slots",
)
NON_NATIVE_METHODS = METHODS[:-1]
STAGES = (
    "input_decode_ns",
    "representation_ns",
    "restriction_setup_ns",
    "evaluation_ns",
    "delivery_ns",
    "query_total_ns",
    "cleanup_ns",
    "accounted_total_ns",
)
REQUIRED_SOURCE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/gf2_multi_query_batch_experiment.py",
    "cmbench/comparative/gf2_native_portfolio_experiment.py",
    "cmbench/comparative/gf2_native_slot_experiment.py",
    "cmbench/comparative/gf2_native_slots.py",
    "cmbench/comparative/gf2_projection_optimization_experiment.py",
    "cmbench/comparative/gf2_projection_optimized.py",
    "cmbench/comparative/gf2_restricted_evaluators.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/schedule.py",
    "docs/recognition/c36_wide_repeated_query_dataset.json",
    "docs/recognition/c36_wide_repeated_query_dataset_verification.json",
    "native/cm_fused_slots/CMakeLists.txt",
    "native/cm_fused_slots/build_msvc.cmd",
    "native/cm_fused_slots/fused_slot_executor.c",
    "scripts/build_cm_fused_slots.py",
    "scripts/cm_native_portfolio_development.py",
    "scripts/crse_native_portfolio_development_verify.py",
    "scripts/crse_verify_c36_wide_repeated_query_dataset.py",
)


@dataclass(frozen=True)
class NativePortfolioConfig:
    run_id: str
    seed: int = 20260903
    max_seconds: float = 900.0

    @property
    def blocks(self) -> int:
        return len(balanced_orders(METHODS))


def _normalize_engine_row(row: dict[str, Any]) -> dict[str, Any]:
    timings = row["timings_ns"]
    timings["query_total_ns"] = (
        timings["restriction_setup_ns"]
        + timings["evaluation_ns"]
        + timings["delivery_ns"]
    )
    row["output_sha256"] = row["artifact_sha256"]
    row["schema"] = RAW_SCHEMA
    return row


def execute_portfolio_session(
    *,
    case: Mapping[str, Any],
    method: str,
    library: NativeSlotLibrary,
    expected_digest: str,
    role: str = "performance",
    profile_python_allocations: bool = False,
) -> dict[str, Any]:
    """Execute one complete q64 task with process-global input caches isolated."""
    if method not in METHODS or role not in ("performance", "memory_profile"):
        raise ValueError("invalid native portfolio session")
    clear_bitset_env_cache()
    clear_words_env_cache()
    if method == "native_fused_slots":
        row = execute_native_session(
            case=case,
            library=library,
            expected_digest=expected_digest,
            role=role,
            profile_python_allocations=profile_python_allocations,
        )
        row["schema"] = RAW_SCHEMA
    elif method == "projection_u16_tuple":
        row = execute_projection_session(
            case=case,
            method=method,
            expected_digest=expected_digest,
            role=role,
            profile_python_allocations=profile_python_allocations,
        )
        row["schema"] = RAW_SCHEMA
    else:
        row = _normalize_engine_row(execute_engine_session(
            case=case,
            method=method,
            query_count=64,
            role=role,
            profile_python_allocations=profile_python_allocations,
        ))
    if row.get("output_sha256") != expected_digest:
        raise RuntimeError(f"{method} failed the native portfolio exact oracle")
    timings = row["timings_ns"]
    if "query_total_ns" not in timings:
        timings["query_total_ns"] = (
            timings["restriction_setup_ns"]
            + timings["evaluation_ns"]
            + timings["delivery_ns"]
        )
    return row


def summarize(rows: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    performance = [row for row in rows if row["role"] == "performance"]
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in performance:
        grouped[(row["case_id"], row["method"])].append(row)
    medians = {
        (case["case_id"], method): {
            stage: int(statistics.median_low(
                row["timings_ns"][stage]
                for row in grouped[(case["case_id"], method)]
            ))
            for stage in STAGES
        }
        for case in cases for method in METHODS
    }
    totals = {
        method: {
            stage: sum(medians[(case["case_id"], method)][stage] for case in cases)
            for stage in STAGES
        }
        for method in METHODS
    }
    q64 = {method: totals[method]["accounted_total_ns"] for method in METHODS}
    best_method = min(METHODS, key=lambda method: (q64[method], method))
    best_non_native = min(
        NON_NATIVE_METHODS, key=lambda method: (q64[method], method))
    winners = {}
    for case in cases:
        case_id = case["case_id"]
        winners[case_id] = min(
            METHODS,
            key=lambda method: (
                medians[(case_id, method)]["accounted_total_ns"], method),
        )
    oracle_ns = sum(
        medians[(case["case_id"], winners[case["case_id"]])]["accounted_total_ns"]
        for case in cases
    )
    memory = {}
    for method in METHODS:
        selected = [
            row for row in rows
            if row["role"] == "memory_profile" and row["method"] == method
        ]
        memory[method] = {
            "sessions": len(selected),
            "max_tracemalloc_peak_bytes": max(
                row["resources"].get("tracemalloc_peak_bytes", 0)
                for row in selected
            ),
            "max_sampled_rss_delta_bytes": max(
                row["resources"].get(
                    "session_sampled_peak_rss_delta_bytes",
                    row["resources"].get("rss_end_minus_start_bytes", 0),
                ) or 0
                for row in selected
            ),
        }
    native_ns = q64["native_fused_slots"]
    best_ns = q64[best_method]
    headroom = best_ns / oracle_ns
    return {
        "cases": len(cases),
        "performance_sessions": len(performance),
        "memory_profile_sessions": sum(
            row["role"] == "memory_profile" for row in rows),
        "timed_queries": len(performance) * 64,
        "aggregate_case_median_stage_ns": totals,
        "q64_accounted_total_ns": q64,
        "best_fixed_method": best_method,
        "best_non_native_method": best_non_native,
        "native_speedup_over_best_non_native": q64[best_non_native] / native_ns,
        "native_ten_percent_gate": q64[best_non_native] / native_ns >= 1.10,
        "per_case_winners": dict(sorted(winners.items())),
        "per_case_winner_counts": dict(sorted(Counter(winners.values()).items())),
        "native_case_wins": sum(method == "native_fused_slots" for method in winners.values()),
        "per_case_oracle_total_ns": oracle_ns,
        "oracle_speedup_over_best_fixed": headroom,
        "selector_development_headroom_gate": headroom >= 1.10,
        "memory_profiles": memory,
    }


def _source_manifest(project_root: Path) -> dict[str, dict[str, Any]]:
    root = project_root.resolve()
    relative_paths = set(REQUIRED_SOURCE_PATHS)
    for module in tuple(sys.modules.values()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        try:
            path = Path(raw).resolve()
        except (OSError, RuntimeError):
            continue
        if path.is_file() and path.is_relative_to(root):
            relative_paths.add(path.relative_to(root).as_posix())
    sources = {}
    for relative in sorted(relative_paths):
        path = root.joinpath(*Path(relative).parts).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise FileNotFoundError(relative)
        sources[relative] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    return sources


def _write_artifacts(
    *,
    output_dir: Path,
    project_root: Path,
    result: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    library: NativeSlotLibrary,
) -> None:
    raw_path = output_dir / "raw_measurements.jsonl"
    with raw_path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(
                row, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                allow_nan=False) + "\n")
    _write_json(output_dir / "results.json", result)
    _write_json(output_dir / "environment.json", _environment(project_root))
    _write_text(output_dir / "protocol.md", (
        "# Native exact-portfolio development protocol\n\n"
        "Development-only, cache-isolated q64 comparison on the exposed C36 "
        "cohort. The arms are R2, CSE bigint/words, CM-IR bigint/words, uint16 "
        "projection, and fused native slots. Every arm returns the identical "
        "relation/count/SAT/witness delivery. Memory sessions are excluded from "
        "timing. No prospective data, training, routing, or production promotion.\n"
    ))
    summary = result["summary"]
    totals = summary["q64_accounted_total_ns"]
    _write_text(output_dir / "report.md", (
        "# Native exact-portfolio development result\n\n"
        f"Best fixed method: `{summary['best_fixed_method']}`. "
        f"Native: {totals['native_fused_slots'] / 1e6:.3f} ms; "
        f"best non-native `{summary['best_non_native_method']}`: "
        f"{totals[summary['best_non_native_method']] / 1e6:.3f} ms. "
        f"Native speedup over that baseline: "
        f"{summary['native_speedup_over_best_non_native']:.4f}x. "
        f"Per-case oracle headroom: {summary['oracle_speedup_over_best_fixed']:.6f}x. "
        f"Prospective gate: {str(result['decision']['prospective_confirmation_allowed']).lower()}.\n"
    ))
    artifacts = {}
    for name in (
        "raw_measurements.jsonl", "results.json", "environment.json",
        "protocol.md", "report.md", f"native/{library.path.name}",
    ):
        path = output_dir / name
        artifacts[name] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    executable = Path(sys.executable).resolve()
    _write_json(output_dir / "manifest.json", {
        "schema": MANIFEST_SCHEMA,
        "run_id": result["run_id"],
        "artifacts": artifacts,
        "sources": _source_manifest(project_root),
        "native_library": {
            "path": library.path.relative_to(project_root).as_posix(),
            "bytes": library.path.stat().st_size,
            "sha256": library.sha256,
            "abi_version": library.abi_version,
        },
        "interpreter": {
            "path": str(executable),
            "bytes": executable.stat().st_size,
            "sha256": _sha256(executable),
        },
        "closure_method": (
            "required experiment/verifier sources plus all loaded project modules, "
            "the resident native binary, and interpreter executable"
        ),
    })


def run(
    config: NativePortfolioConfig,
    output_dir: Path,
    dataset_path: Path,
    library_path: Path,
    project_root: Path,
    *,
    progress: Callable[[str, int, int, str], None] | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    output_dir = output_dir.resolve()
    dataset_path = dataset_path.resolve()
    library_path = library_path.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    native_dir = output_dir / "native"
    native_dir.mkdir()
    resident_library = native_dir / library_path.name
    shutil.copyfile(library_path, resident_library)
    library = load_native_slot_library(resident_library)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    cases = list(dataset["cases"])
    expected = {
        case["case_id"]: _digest(oracle_document(case, case["c36_trace"]))
        for case in cases
    }
    started = time.perf_counter()
    for method in METHODS:
        execute_portfolio_session(
            case=cases[0], method=method, library=library,
            expected_digest=expected[cases[0]["case_id"]])

    rows: list[dict[str, Any]] = []
    orders = balanced_orders(METHODS)
    total = len(orders) * len(cases) * len(METHODS)
    completed = 0
    for block, order in enumerate(orders):
        case_order = list(cases)
        random.Random(config.seed + block).shuffle(case_order)
        for case_position, case in enumerate(case_order):
            for method_position, method in enumerate(order):
                if time.perf_counter() - started > config.max_seconds:
                    raise TimeoutError("native portfolio experiment exceeded max_seconds")
                row = execute_portfolio_session(
                    case=case, method=method, library=library,
                    expected_digest=expected[case["case_id"]])
                row.update({
                    "block": block,
                    "case_position": case_position,
                    "method_position": method_position,
                    "method_order": list(order),
                })
                rows.append(row)
                completed += 1
                if progress:
                    progress("performance", completed, total, case["case_id"])

    memory_total = len(cases) * len(METHODS)
    completed = 0
    for case_position, case in enumerate(cases):
        order = orders[case_position % len(orders)]
        for method_position, method in enumerate(order):
            row = execute_portfolio_session(
                case=case, method=method, library=library,
                expected_digest=expected[case["case_id"]],
                role="memory_profile", profile_python_allocations=True)
            row.update({
                "block": None,
                "case_position": case_position,
                "method_position": method_position,
                "method_order": list(order),
            })
            rows.append(row)
            completed += 1
            if progress:
                progress("memory_profile", completed, memory_total, case["case_id"])

    summary = summarize(rows, cases)
    decision = {
        "native_fixed_improvement_gate": summary["native_ten_percent_gate"],
        "selector_development_headroom_gate": summary["selector_development_headroom_gate"],
        "prospective_confirmation_allowed": (
            summary["native_ten_percent_gate"]
            and summary["selector_development_headroom_gate"]
        ),
        "training_allowed": False,
        "training_performed": False,
        "prospective_data_consumed": False,
        "production_write": False,
        "production_promotion": False,
    }
    result = {
        "schema": SCHEMA,
        "run_id": config.run_id,
        "status": "complete",
        "config": {
            "seed": config.seed,
            "blocks": config.blocks,
            "max_seconds": config.max_seconds,
            "query_count": 64,
            "bitset_environment_cache_policy": "cleared_before_each_complete_task",
            "words_environment_cache_policy": "cleared_before_each_complete_task",
        },
        "dataset": {
            "path": dataset_path.relative_to(project_root).as_posix(),
            "sha256": _sha256(dataset_path),
            "classification": "development_exposed_c36_not_confirmation",
            "cases": len(cases),
            "queries_per_case": 64,
        },
        "native_library": {
            "path": library.path.relative_to(project_root).as_posix(),
            "sha256": library.sha256,
            "abi_version": library.abi_version,
        },
        "methods": list(METHODS),
        "correctness": {
            "canonical_delivery_mismatches": 0,
            "exact_query_checks": len(rows) * 64,
        },
        "summary": summary,
        "decision": decision,
        "elapsed_seconds": time.perf_counter() - started,
    }
    _write_artifacts(
        output_dir=output_dir, project_root=project_root,
        result=result, rows=rows, library=library)
    return result
