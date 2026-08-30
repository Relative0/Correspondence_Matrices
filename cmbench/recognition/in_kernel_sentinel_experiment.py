"""C13 bounded confirmation of the base-kernel ANF tail sentinel."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import platform
from pathlib import Path
import statistics
import sys
import time
from typing import Any

from .adaptive_exact_dispatcher import (
    adaptive_exact_partition, adaptive_exact_partition_fast,
)
from .natural_decomposition import partition_witness
from .source_anf_hybrid import ProductCache
from .source_interaction import source_exact_partition
from .yosys_source_anf_experiment import document_truth_bits, percentile


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "docs/recognition/runs/adaptive-exact-dispatcher-robust-20260830-002/evaluation_dataset.json"
EXPECTED_INPUT_SHA256 = "9ba84b3625d748de81150614e619c7a815abb87e4375c6dac56f8dff6b9ce038"
PRIOR_SUMMARY = ROOT / "docs/recognition/runs/adaptive-exact-dispatcher-robust-20260830-002/summary.json"
SCHEMA = "crse-in-kernel-tail-sentinel-experiment/v1"
MEASUREMENT_SCHEMA = "crse-in-kernel-tail-sentinel-measurement/v1"
METHODS = ("set_no_sentinel", "advice_disabled", "sentinel_fast", "sentinel_measured")
SPLITS = ("c6_test_dev", "c6_confirmatory_dev", "c7_a_dev", "c7_b_dev",
          "c11_a_dev", "c11_b_dev", "c12_sealed_a", "c12_sealed_b")
FROZEN_PRODUCT_PAIR_BUDGET = 4096


@dataclass(frozen=True)
class InKernelSentinelConfig:
    repetitions: int = 15
    cache_capacity: int = 1024
    threads: int = 1
    max_seconds: int = 120

    def validate(self) -> None:
        if (type(self.repetitions) is not int or not 5 <= self.repetitions <= 20
                or type(self.cache_capacity) is not int
                or not 1 <= self.cache_capacity <= 16_384
                or self.threads != 1 or type(self.max_seconds) is not int
                or not 1 <= self.max_seconds <= 120):
            raise ValueError("invalid C13 in-kernel sentinel configuration")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def source_fingerprints() -> dict[str, str]:
    paths = (
        ROOT / "cmbench/recognition/source_interaction.py",
        ROOT / "cmbench/recognition/adaptive_exact_dispatcher.py",
        ROOT / "cmbench/recognition/in_kernel_sentinel_experiment.py",
        ROOT / "scripts/cm_recognition_in_kernel_sentinel.py",
    )
    return {relative(path): sha(path) for path in paths}


def _solve(method: str, row: dict, cache: ProductCache | None):
    document, n_vars = row["expression_v2"], row["n_vars"]
    instrumentation = None
    if method in {"set_no_sentinel", "advice_disabled"}:
        # The advice-off engine is selected before execution and is exactly the
        # original no-sentinel kernel, with no sentinel branch or counters.
        partition = source_exact_partition(document, n_vars)
        selected = "set_source_anf"
    elif method == "sentinel_fast":
        partition, selected = adaptive_exact_partition_fast(
            document, n_vars, product_pair_budget=FROZEN_PRODUCT_PAIR_BUDGET,
            cache=cache)
    elif method == "sentinel_measured":
        partition, selected, stats = adaptive_exact_partition(
            document, n_vars, product_pair_budget=FROZEN_PRODUCT_PAIR_BUDGET,
            cache=cache)
        instrumentation = stats.to_dict()
    else:  # pragma: no cover
        raise ValueError("unknown C13 method")
    return partition, selected, instrumentation


def run_in_kernel_sentinel_experiment(
    config: InKernelSentinelConfig,
    output: Path,
    *,
    input_path: Path = DEFAULT_INPUT,
    progress=print,
) -> dict:
    config.validate()
    output, input_path = output.resolve(), input_path.resolve()
    if sha(input_path) != EXPECTED_INPUT_SHA256:
        raise ValueError("changed frozen C6-C12 evaluation input")
    documents = json.loads(input_path.read_text(encoding="utf-8"))
    if (len(documents) != 188 or Counter(row["evaluation_split"] for row in documents)
            != Counter({"c6_test_dev": 32, "c6_confirmatory_dev": 36,
                        "c7_a_dev": 20, "c7_b_dev": 20,
                        "c11_a_dev": 20, "c11_b_dev": 20,
                        "c12_sealed_a": 20, "c12_sealed_b": 20})):
        raise ValueError("changed C13 split cardinality")
    output.mkdir(parents=True, exist_ok=False)
    before = source_fingerprints()
    run_spec = {
        "schema": "crse-in-kernel-tail-sentinel-run-spec/v1",
        "purpose": "C13 engineering confirmation of the base-kernel sentinel and exact prefix reuse",
        "input": relative(input_path), "input_sha256": EXPECTED_INPUT_SHA256,
        "methods": list(METHODS), "splits": list(SPLITS),
        "product_pair_budget": FROZEN_PRODUCT_PAIR_BUDGET,
        "config": asdict(config), "estimated_memory_mib": 384,
        "network": False, "training": False, "production_write": False,
        "primary_timing": "solve_ns; independent exact check reported separately and included in total_ns",
        "advice_disabled_contract": "select the unchanged source_exact_partition function before execution",
    }
    write_json(output / "run_spec.json", run_spec)

    started = time.perf_counter()
    measurements = []
    for split in SPLITS:
        split_rows = [row for row in documents if row["evaluation_split"] == split]
        progress(f"C13 {split}: {len(split_rows)} cases")
        for repetition in range(config.repetitions):
            order = METHODS[repetition % len(METHODS):] + METHODS[:repetition % len(METHODS)]
            for method in order:
                cache = (ProductCache(config.cache_capacity)
                         if method in {"sentinel_fast", "sentinel_measured"} else None)
                for row in split_rows:
                    if time.perf_counter() - started > config.max_seconds:
                        raise TimeoutError("C13 cooperative wall budget exceeded")
                    solve_started = time.perf_counter_ns()
                    partition, selected, instrumentation = _solve(method, row, cache)
                    solve_ns = time.perf_counter_ns() - solve_started
                    check_started = time.perf_counter_ns()
                    bits = document_truth_bits(row["expression_v2"], row["n_vars"])
                    witness = (partition_witness(bits, row["n_vars"], partition)
                               if partition is not None else None)
                    exact_check_ns = time.perf_counter_ns() - check_started
                    canonical = (tuple(row["witness"]["row_variables"])
                                 if row["witness"] is not None else None)
                    accepted = partition is not None and witness is not None
                    measurements.append({
                        "schema": MEASUREMENT_SCHEMA, "repetition": repetition,
                        "method": method, "split": split, "case_id": row["case_id"],
                        "n_vars": row["n_vars"], "label": row["label"],
                        "selected_arm": selected, "predicted": int(partition is not None),
                        "accepted": accepted,
                        "row_variables": list(partition) if partition is not None else None,
                        "canonical_partition_match": partition == canonical,
                        "semantic_mismatch": bool(accepted and not row["label"]),
                        "solve_ns": solve_ns, "exact_check_ns": exact_check_ns,
                        "total_ns": solve_ns + exact_check_ns,
                        "instrumentation": instrumentation,
                    })

    grouped = defaultdict(list)
    for row in measurements:
        grouped[(row["method"], row["split"], row["case_id"])].append(row)
    per_case = []
    semantic_fields = ("selected_arm", "predicted", "accepted", "row_variables",
                       "canonical_partition_match", "semantic_mismatch")
    for (method, split, case_id), values in sorted(grouped.items()):
        first = values[0]
        if len(values) != config.repetitions:
            raise ValueError("incomplete C13 timing repetitions")
        if any(any(value[field] != first[field] for field in semantic_fields)
               for value in values[1:]):
            raise ValueError("nondeterministic C13 semantic result")
        source = next(row for row in documents if row["case_id"] == case_id)
        per_case.append({
            "method": method, "split": split, "case_id": case_id,
            "n_vars": first["n_vars"], "label": first["label"],
            **{field: first[field] for field in semantic_fields},
            "median_solve_ns": int(statistics.median(row["solve_ns"] for row in values)),
            "median_exact_check_ns": int(statistics.median(
                row["exact_check_ns"] for row in values)),
            "median_total_ns": int(statistics.median(row["total_ns"] for row in values)),
            "timing_repetitions": config.repetitions,
            "source_scope": source["source_scope"],
        })

    method_summary = {}
    for method in METHODS:
        for split in SPLITS:
            values = [row for row in per_case
                      if row["method"] == method and row["split"] == split]
            solve = [row["median_solve_ns"] for row in values]
            total = [row["median_total_ns"] for row in values]
            method_summary[f"{method}/{split}"] = {
                "cases": len(values),
                "sequence_solve_ns": sum(solve),
                "median_solve_ns": statistics.median(solve),
                "p95_solve_ns": percentile(solve, .95),
                "maximum_solve_ns": max(solve),
                "sequence_total_ns": sum(total),
                "selection_counts": dict(sorted(Counter(
                    row["selected_arm"] for row in values).items())),
            }
    split_summary = {}
    for split in SPLITS:
        baseline = method_summary[f"set_no_sentinel/{split}"]
        advice_off = method_summary[f"advice_disabled/{split}"]
        fast = method_summary[f"sentinel_fast/{split}"]
        measured = method_summary[f"sentinel_measured/{split}"]
        split_summary[split] = {
            "sentinel_fast_speedup_over_set": (
                baseline["sequence_solve_ns"] / fast["sequence_solve_ns"]),
            "sentinel_fast_p95_speedup_over_set": (
                baseline["p95_solve_ns"] / fast["p95_solve_ns"]),
            "sentinel_measured_speedup_over_fast": (
                fast["sequence_solve_ns"] / measured["sequence_solve_ns"]),
            "advice_disabled_speedup_over_set": (
                baseline["sequence_solve_ns"] / advice_off["sequence_solve_ns"]),
            "sentinel_fast_selection_counts": fast["selection_counts"],
            "set_sequence_solve_ns": baseline["sequence_solve_ns"],
            "sentinel_fast_sequence_solve_ns": fast["sequence_solve_ns"],
        }

    exact = all(row["predicted"] == row["label"]
                and row["canonical_partition_match"]
                and not row["semantic_mismatch"] for row in measurements)
    by_semantic_key = defaultdict(dict)
    for row in per_case:
        by_semantic_key[(row["split"], row["case_id"])][row["method"]] = tuple(
            row[field] for field in semantic_fields)
    advice_off_exact = all(
        values.get("set_no_sentinel") == values.get("advice_disabled")
        for values in by_semantic_key.values())
    sparse_no_regret = all(
        split_summary[split]["sentinel_fast_speedup_over_set"] >= 1 / 1.05
        for split in ("c12_sealed_a", "c12_sealed_b"))
    dense_tail_guard = (
        split_summary["c6_confirmatory_dev"]["sentinel_fast_p95_speedup_over_set"] >= 2)
    prior = json.loads(PRIOR_SUMMARY.read_text(encoding="utf-8"))["split_summary"]
    prior_c12 = {split: prior[split]["adaptive_speedup_over_best_fixed"]
                 for split in ("c12_sealed_a", "c12_sealed_b")}
    sparse_regret_improved = all(
        abs(1 - split_summary[split]["sentinel_fast_speedup_over_set"])
        < abs(1 - prior_c12[split]) for split in prior_c12)
    criteria = {
        "exact": exact, "advice_disabled_exact": advice_off_exact,
        "frozen_budget_4096": True, "detailed_counters_measurement_only": True,
        "sparse_no_material_regret": sparse_no_regret,
        "dense_tail_guard": dense_tail_guard,
        "sparse_regret_improved_over_c12": sparse_regret_improved,
        "local_engineering_gate": exact and advice_off_exact and sparse_no_regret and dense_tail_guard,
        "production_promotion": False,
    }
    result = {
        "schema": SCHEMA, "status": "complete",
        "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0],
        "config": asdict(config), "product_pair_budget": FROZEN_PRODUCT_PAIR_BUDGET,
        "input": relative(input_path), "input_sha256": EXPECTED_INPUT_SHA256,
        "evaluation_cases": len(documents), "measurement_rows": len(measurements),
        "per_case_rows": len(per_case), "method_summary": method_summary,
        "split_summary": split_summary, "prior_c12_speedup": prior_c12,
        "criteria": criteria,
        "semantic_mismatches": sum(row["semantic_mismatch"] for row in measurements),
        "source_unchanged": before == source_fingerprints(),
    }
    measurements_path = output / "measurements.jsonl"
    measurements_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n"
                                         for row in measurements), encoding="utf-8")
    write_json(output / "per_case.json", per_case)
    write_json(output / "summary.json", result)
    files = ("run_spec.json", "measurements.jsonl", "per_case.json", "summary.json")
    write_json(output / "manifest.json", {
        "schema": "crse-in-kernel-tail-sentinel-artifacts/v1",
        "status": "complete", "files_sha256": {name: sha(output / name) for name in files},
        "source_sha256": before,
    })
    return result
