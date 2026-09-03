"""Complete-task development experiment for bounded rank elimination."""
from __future__ import annotations
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

from cmbench.recognition.gf2_bounded_rank import analyze_screened_exact_gf2_bounded_rank
from cmbench.recognition.gf2_decomposition import analyze_screened_exact_gf2
from .contracts import canonical_bytes
from .gf2_anf_rank_experiment import prepare_c16_cases
from .gf2_restricted_evaluator_experiment import _environment, _rss_snapshot, collect_reproducibility_manifest

SCHEMA = "crse-bounded-rank-development/v1"
RAW_SCHEMA = "crse-bounded-rank-raw-session/v1"
METHODS = ("unbounded_rank_screen", "bounded_rank_screen")
EXTRA_MANIFEST_SOURCES = (
    "cmbench/recognition/gf2_bounded_rank.py",
    "cmbench/comparative/gf2_bounded_rank_experiment.py",
    "scripts/cm_comparative_bounded_rank_development.py",
    "scripts/crse_bounded_rank_development_verify.py",
    "docs/recognition/c16_linux_confirmation/c16_dataset.json",
)

@dataclass(frozen=True)
class BoundedRankConfig:
    run_id: str
    seed: int = 20260902
    blocks: int = 2
    development_speedup_gate: float = 1.10
    pruning_gate: float = 0.30
    max_seconds: float = 600.0

    def validate(self) -> None:
        if (not self.run_id or self.blocks != 2 or self.development_speedup_gate != 1.10
                or self.pruning_gate != 0.30 or not 60 <= self.max_seconds <= 1200):
            raise ValueError("invalid bounded-rank experiment")

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def _write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")

def _write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False) + "\n")

def expected(case: Mapping[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    analysis = analyze_screened_exact_gf2(
        case["bits"], case["n_vars"], max_partitions=64, materialize_budget=4)
    documents = [artifact.to_dict() for artifact in analysis.candidates]
    return _digest(documents), documents

def execute_session(*, case: Mapping[str, Any], method: str, expected_sha: str,
                    expected_documents: Sequence[Mapping[str, Any]], role: str,
                    clock: Callable[[], int] = time.perf_counter_ns,
                    allocations: bool = False) -> dict[str, Any]:
    if method not in METHODS or role not in ("performance", "memory_profile"):
        raise ValueError("bounded-rank session")
    if allocations:
        tracemalloc.start()
    start_rss, _ = _rss_snapshot()
    started = clock()
    if method == "unbounded_rank_screen":
        analysis = analyze_screened_exact_gf2(
            case["bits"], case["n_vars"], max_partitions=64, materialize_budget=4)
        metrics = {"rank_partitions": analysis.partitions_tested,
                   "rank_partitions_pruned": 0, "rank_rows_total": 0,
                   "rank_rows_scanned": 0, "rank_rows_pruned": 0}
    else:
        analysis, metrics = analyze_screened_exact_gf2_bounded_rank(
            case["bits"], case["n_vars"], max_partitions=64, materialize_budget=4)
    compute_ns = max(1, clock() - started)
    documents = [artifact.to_dict() for artifact in analysis.candidates]
    artifact_sha = _digest(documents)
    if artifact_sha != expected_sha or documents != list(expected_documents):
        raise RuntimeError("bounded rank changed exact candidates")
    end_rss, process_peak = _rss_snapshot()
    resources = {**metrics,
                 "session_sampled_peak_rss_delta_bytes": (
                     max(0, end_rss - start_rss)
                     if start_rss is not None and end_rss is not None else None),
                 "process_peak_rss_bytes": process_peak}
    if allocations:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        resources["tracemalloc_peak_bytes"] = int(peak)
    return {"schema": RAW_SCHEMA, "role": role, "case_id": case["case_id"],
            "family": case["family"], "n_vars": case["n_vars"], "method": method,
            "status": "ok", "timings_ns": {"accounted_total_ns": compute_ns},
            "artifact_sha256": artifact_sha, "resources": resources,
            "exact_check_passed": True}

def summarize(rows: Sequence[Mapping[str, Any]], speed_gate: float,
              pruning_gate: float) -> dict[str, Any]:
    performance = [row for row in rows if row["role"] == "performance"]
    cases = sorted({row["case_id"] for row in performance})
    samples: dict[tuple[str, str], list[int]] = {}
    for row in performance:
        samples.setdefault((row["case_id"], row["method"]), []).append(
            row["timings_ns"]["accounted_total_ns"])
    medians = {key: int(statistics.median(value)) for key, value in samples.items()}
    totals = {method: sum(medians[(case, method)] for case in cases) for method in METHODS}
    bounded_rows = [row for row in performance if row["method"] == "bounded_rank_screen"]
    rows_total = sum(row["resources"]["rank_rows_total"] for row in bounded_rows)
    rows_pruned = sum(row["resources"]["rank_rows_pruned"] for row in bounded_rows)
    pruning_fraction = rows_pruned / rows_total
    speedup = totals["unbounded_rank_screen"] / totals["bounded_rank_screen"]
    memory_rows = [row for row in rows if row["role"] == "memory_profile"]
    memory = {method: {"profile_sessions": len([row for row in memory_rows if row["method"] == method]),
                       "max_tracemalloc_peak_bytes": max(
                           row["resources"].get("tracemalloc_peak_bytes", 0)
                           for row in memory_rows if row["method"] == method)}
              for method in METHODS}
    return {"cases": len(cases), "performance_sessions": len(performance),
            "memory_profile_sessions": len(memory_rows), "method_total_ns": totals,
            "bounded_speedup": speedup, "rank_rows_total": rows_total,
            "rank_rows_pruned": rows_pruned, "rank_row_pruning_fraction": pruning_fraction,
            "memory_profiles": memory,
            "decision": {"development_speedup_gate": speed_gate,
                         "pruning_gate": pruning_gate,
                         "speed_gate_passed": speedup >= speed_gate,
                         "pruning_gate_passed": pruning_fraction >= pruning_gate,
                         "integration_gate_passed": speedup >= speed_gate and pruning_fraction >= pruning_gate,
                         "production_integration_permitted": False}}

def run(config: BoundedRankConfig, output: Path, dataset_path: Path, root: Path,
        *, progress: Callable[[int, int, str], None] | None = None) -> dict[str, Any]:
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = prepare_c16_cases(dataset)
    oracles = {case["case_id"]: expected(case) for case in cases}
    rows = []
    for block in range(config.blocks):
        shuffled = list(cases)
        random.Random(f"bounded-rank:{config.seed}:{block}").shuffle(shuffled)
        order = METHODS if block == 0 else tuple(reversed(METHODS))
        for position, case in enumerate(shuffled):
            expected_sha, documents = oracles[case["case_id"]]
            for method_position, method in enumerate(order):
                row = execute_session(case=case, method=method,
                                      expected_sha=expected_sha,
                                      expected_documents=documents, role="performance")
                row.update({"block": block, "cell_position": position,
                            "method_position": method_position,
                            "method_order": list(order)})
                rows.append(row)
            if progress:
                progress(block * len(cases) + position + 1, config.blocks * len(cases), case["case_id"])
    representatives = [next(case for case in cases if case["n_vars"] == width)
                       for width in sorted({case["n_vars"] for case in cases})]
    for case in representatives:
        expected_sha, documents = oracles[case["case_id"]]
        for method in METHODS:
            rows.append(execute_session(case=case, method=method,
                                        expected_sha=expected_sha,
                                        expected_documents=documents,
                                        role="memory_profile", allocations=True))
    _write_rows(output / "raw_measurements.jsonl", rows)
    summary = summarize(rows, config.development_speedup_gate, config.pruning_gate)
    result = {"schema": SCHEMA, "status": "complete", "run_id": config.run_id,
              "config": asdict(config), "methods": list(METHODS),
              "dataset": {"path": dataset_path.relative_to(root).as_posix(),
                          "sha256": _sha(dataset_path)},
              "correctness": {"candidate_document_mismatches": 0},
              "summary": summary, "decision": {"production_promotion": False}}
    _write(output / "results.json", result)
    (output / "protocol.md").write_text(
        "# Bounded GF(2) rank development protocol\n\nTwo-order exposed-C16 complete-task comparison.\n",
        encoding="utf-8", newline="\n")
    (output / "report.md").write_text(
        f"# Bounded GF(2) rank result\n\nSpeedup: {summary['bounded_speedup']:.4f}x. "
        f"Rank rows pruned: {summary['rank_row_pruning_fraction']:.2%}.\n",
        encoding="utf-8", newline="\n")
    environment = _environment(root, dataset_path, dataset_path)
    environment["schema"] = "crse-bounded-rank-environment/v1"
    _write(output / "environment.json", environment)
    artifacts = {name: _sha(output / name) for name in (
        "protocol.md", "raw_measurements.jsonl", "environment.json", "results.json", "report.md")}
    _write(output / "manifest.json", collect_reproducibility_manifest(
        root, artifacts, EXTRA_MANIFEST_SOURCES))
    return result
