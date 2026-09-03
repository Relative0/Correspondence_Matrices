"""Complete-task C16 adjudication for ANF-rank pre-screening."""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import random
import statistics
import time
import tracemalloc
from typing import Any

from cmbench.recognition.gf2_anf_screened import analyze_screened_exact_gf2_anf_rank
from cmbench.recognition.gf2_decomposition import analyze_screened_exact_gf2

from .contracts import canonical_bytes
from .gf2_anf_rank_experiment import prepare_c16_cases
from .gf2_restricted_evaluator_experiment import (
    _environment,
    _rss_snapshot,
    collect_reproducibility_manifest,
)


SCHEMA = "crse-anf-rank-full-screen-development/v1"
RAW_SCHEMA = "crse-anf-rank-full-screen-raw-session/v1"
METHODS = (
    "truth_screen",
    "anf_rank_screen_from_truth",
    "anf_rank_screen_precomputed",
)
EXTRA_MANIFEST_SOURCES = (
    "cmbench/recognition/gf2_anf_rank.py",
    "cmbench/recognition/gf2_anf_screened.py",
    "cmbench/comparative/gf2_anf_rank_experiment.py",
    "cmbench/comparative/gf2_anf_full_screen_experiment.py",
    "scripts/cm_comparative_anf_full_screen_development.py",
    "scripts/crse_anf_full_screen_development_verify.py",
    "docs/recognition/c16_linux_confirmation/c16_dataset.json",
)


@dataclass(frozen=True)
class ANFFullScreenConfig:
    run_id: str
    seed: int = 20260902
    blocks: int = 3
    materialize_budget: int = 4
    development_speedup_gate: float = 1.10
    max_seconds: float = 600.0

    def validate(self) -> None:
        if (not self.run_id or self.blocks != len(METHODS)
                or self.materialize_budget != 4
                or self.development_speedup_gate != 1.10
                or type(self.max_seconds) not in (int, float)
                or not 60 <= self.max_seconds <= 1200):
            raise ValueError("invalid ANF full-screen bounds")


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


def expected_artifact(case: Mapping[str, Any], budget: int = 4) -> tuple[str, list[dict[str, Any]]]:
    analysis = analyze_screened_exact_gf2(
        case["bits"], case["n_vars"], max_partitions=64,
        materialize_budget=budget)
    documents = [artifact.to_dict() for artifact in analysis.candidates]
    return _digest(documents), documents


def execute_session(
    *, case: Mapping[str, Any], method: str, expected_sha256: str,
    expected_documents: Sequence[Mapping[str, Any]], role: str,
    clock: Callable[[], int] = time.perf_counter_ns,
    profile_python_allocations: bool = False,
) -> dict[str, Any]:
    if method not in METHODS or role not in ("performance", "memory_profile"):
        raise ValueError("invalid ANF full-screen session")
    if profile_python_allocations:
        tracemalloc.start()
    start_rss, _peak = _rss_snapshot()
    started = clock()
    if method == "truth_screen":
        analysis = analyze_screened_exact_gf2(
            case["bits"], case["n_vars"], max_partitions=64,
            materialize_budget=4)
    else:
        analysis = analyze_screened_exact_gf2_anf_rank(
            case["bits"], case["n_vars"], max_partitions=64,
            materialize_budget=4,
            polynomial=(case["polynomial"]
                        if method == "anf_rank_screen_precomputed" else None))
    compute_ns = max(1, clock() - started)
    started = clock()
    documents = [artifact.to_dict() for artifact in analysis.candidates]
    artifact_sha256 = _digest(documents)
    delivery_ns = max(1, clock() - started)
    if artifact_sha256 != expected_sha256 or documents != list(expected_documents):
        raise RuntimeError("ANF full-screen candidate changed exact artifacts")
    end_rss, process_peak = _rss_snapshot()
    resources = {
        "partitions_tested": analysis.partitions_tested,
        "descriptors_screened": analysis.descriptors_screened,
        "artifacts_materialized": analysis.artifacts_materialized,
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
        "schema": RAW_SCHEMA, "role": role, "case_id": case["case_id"],
        "family": case["family"], "n_vars": case["n_vars"], "method": method,
        "status": "ok", "artifact_sha256": artifact_sha256,
        "timings_ns": {"compute_ns": compute_ns, "delivery_ns": delivery_ns,
                       "accounted_total_ns": compute_ns + delivery_ns},
        "resources": resources, "exact_check_passed": True,
    }


def build_schedule(cases: Sequence[Mapping[str, Any]], blocks: int,
                   seed: int) -> list[dict[str, Any]]:
    orders = tuple(METHODS[index:] + METHODS[:index] for index in range(len(METHODS)))
    rows = []
    for block in range(blocks):
        shuffled = list(cases)
        random.Random(f"anf-full-screen:{seed}:{block}").shuffle(shuffled)
        order = orders[(block + seed) % len(orders)]
        for position, case in enumerate(shuffled):
            core = {"block": block, "cell_position": position,
                    "case_id": case["case_id"], "family": case["family"],
                    "n_vars": case["n_vars"], "method_order": list(order)}
            core["order_sha256"] = _digest(core)
            rows.append(core)
    return rows


def validate_schedule(rows: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]],
                      blocks: int) -> None:
    if len(rows) != len(cases) * blocks:
        raise ValueError("ANF full-screen schedule cardinality")
    for case in cases:
        selected = [row for row in rows if row["case_id"] == case["case_id"]]
        if Counter(row["block"] for row in selected) != Counter(range(blocks)):
            raise ValueError("ANF full-screen block balance")
        for method in METHODS:
            if Counter(row["method_order"].index(method) for row in selected) \
                    != Counter({index: 1 for index in range(len(METHODS))}):
                raise ValueError("ANF full-screen position balance")
    for row in rows:
        core = {key: row[key] for key in (
            "block", "cell_position", "case_id", "family", "n_vars", "method_order")}
        if row.get("order_sha256") != _digest(core) \
                or set(row["method_order"]) != set(METHODS):
            raise ValueError("ANF full-screen schedule identity")


def summarize(rows: Sequence[Mapping[str, Any]], gate: float) -> dict[str, Any]:
    performance = [row for row in rows if row["role"] == "performance"]
    cases = sorted({row["case_id"] for row in performance})
    samples: dict[tuple[str, str], list[int]] = {}
    for row in performance:
        samples.setdefault((row["case_id"], row["method"]), []).append(
            row["timings_ns"]["accounted_total_ns"])
    medians = {key: int(statistics.median(values)) for key, values in samples.items()}
    totals = {method: sum(medians[(case, method)] for case in cases) for method in METHODS}
    speedups = {method: totals["truth_screen"] / total for method, total in totals.items()}
    by_width = {}
    metadata = {row["case_id"]: row["n_vars"] for row in performance}
    for width in sorted(set(metadata.values())):
        selected = [case for case in cases if metadata[case] == width]
        width_totals = {method: sum(medians[(case, method)] for case in selected)
                        for method in METHODS}
        by_width[str(width)] = {"cases": len(selected), "method_total_ns": width_totals,
                                "speedup_from_truth": {
                                    method: width_totals["truth_screen"] / total
                                    for method, total in width_totals.items()}}
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
    from_truth = speedups["anf_rank_screen_from_truth"]
    precomputed = speedups["anf_rank_screen_precomputed"]
    return {
        "cases": len(cases), "performance_sessions": len(performance),
        "memory_profile_sessions": len(memory_rows), "method_total_ns": totals,
        "speedup_over_truth_screen": speedups, "by_width": by_width,
        "memory_profiles": memory,
        "decision": {"development_speedup_gate": gate,
                     "from_truth_speedup": from_truth,
                     "precomputed_speedup": precomputed,
                     "from_truth_gate_passed": from_truth >= gate,
                     "precomputed_gate_passed": precomputed >= gate,
                     "production_integration_permitted": False},
        "timing_is_local_and_machine_specific": True,
        "memory_timing_excluded_from_performance_summary": True,
    }


def run(config: ANFFullScreenConfig, output: Path, dataset_path: Path, root: Path,
        *, progress: Callable[[str, int, int, str], None] | None = None) -> dict[str, Any]:
    config.validate()
    wall_started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = prepare_c16_cases(dataset)
    expected = {case["case_id"]: expected_artifact(case, config.materialize_budget)
                for case in cases}
    schedule = build_schedule(cases, config.blocks, config.seed)
    validate_schedule(schedule, cases, config.blocks)
    case_map = {case["case_id"]: case for case in cases}
    rows: list[dict[str, Any]] = []
    for index, planned in enumerate(schedule):
        case = case_map[planned["case_id"]]
        expected_sha, documents = expected[case["case_id"]]
        for position, method in enumerate(planned["method_order"]):
            row = execute_session(case=case, method=method,
                                  expected_sha256=expected_sha,
                                  expected_documents=documents, role="performance")
            row.update({"block": planned["block"],
                        "cell_position": planned["cell_position"],
                        "method_position": position,
                        "method_order": planned["method_order"],
                        "order_sha256": planned["order_sha256"]})
            rows.append(row)
        if progress is not None:
            progress("performance", index + 1, len(schedule), case["case_id"])
        if time.perf_counter() - wall_started > config.max_seconds:
            raise TimeoutError("ANF full-screen experiment exceeded wall bound")
    representatives = []
    for width in sorted({case["n_vars"] for case in cases}):
        representatives.append(next(case for case in cases if case["n_vars"] == width))
    for case_index, case in enumerate(representatives):
        expected_sha, documents = expected[case["case_id"]]
        for position, method in enumerate(METHODS):
            row = execute_session(case=case, method=method,
                                  expected_sha256=expected_sha,
                                  expected_documents=documents, role="memory_profile",
                                  profile_python_allocations=True)
            row.update({"block": None, "cell_position": case_index,
                        "method_position": position, "method_order": list(METHODS),
                        "order_sha256": _digest({"role": "memory_profile",
                                                 "case_id": case["case_id"],
                                                 "method_order": list(METHODS)})})
            rows.append(row)
    _write_jsonl(output / "raw_measurements.jsonl", rows)
    summary = summarize(rows, config.development_speedup_gate)
    result = {"schema": SCHEMA, "status": "complete", "run_id": config.run_id,
              "config": asdict(config), "methods": list(METHODS),
              "dataset": {"path": dataset_path.relative_to(root).as_posix(),
                          "sha256": _sha256(dataset_path),
                          "classification": "development_exposed_c16_not_confirmation"},
              "correctness": {"candidate_document_mismatches": 0,
                              "best_artifact_mismatches": 0},
              "summary": summary,
              "decision": {"production_write": False, "production_promotion": False},
              "elapsed_seconds": time.perf_counter() - wall_started}
    _write_json(output / "results.json", result)
    report = ["# ANF rank full-screen development result", "",
              "All candidate documents and best artifacts were byte-identical.", "",
              "| Method | Total ms | Speedup |", "|---|---:|---:|"]
    for method in METHODS:
        report.append(f"| {method} | {summary['method_total_ns'][method] / 1e6:.3f} | "
                      f"{summary['speedup_over_truth_screen'][method]:.4f}x |")
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    (output / "protocol.md").write_text(
        "# ANF rank full-screen development protocol\n\n"
        "Three-position counterbalanced, exposed C16 cohort, byte-identical global-best contract.\n",
        encoding="utf-8", newline="\n")
    environment = _environment(root, dataset_path, dataset_path)
    environment["schema"] = "crse-anf-rank-full-screen-environment/v1"
    _write_json(output / "environment.json", environment)
    artifacts = {name: _sha256(output / name) for name in (
        "protocol.md", "raw_measurements.jsonl", "environment.json", "results.json", "report.md")}
    _write_json(output / "manifest.json", collect_reproducibility_manifest(
        root, artifacts, EXTRA_MANIFEST_SOURCES))
    return result
