"""Portable second-machine timing for the frozen C7 Yosys dataset."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.natural_decomposition import analyze_decomposition, partition_witness
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import ProductCache, source_packed_partition
from cmbench.recognition.source_interaction import source_exact_partition

EXPECTED_DATASET_SHA256 = "3ca1ae22fd79bac68c37e78fe497701cb100713b0077130e5263cb1f66145864"
METHODS = (
    "set_source_anf",
    "packed_source_anf",
    "cached_packed_cold",
    "cached_packed_warm",
    "bitset_truth_vector_anf",
    "numpy_truth_vector_anf",
)
SPLITS = ("sealed_a", "sealed_b")


def write_json(path: Path, value):
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, quantile):
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower, upper = int(index), min(int(index) + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


@lru_cache(maxsize=9)
def variable_masks(n_vars: int):
    rows = 1 << n_vars
    result = []
    for variable in range(n_vars):
        mask = 0
        for assignment in range(rows):
            mask |= ((assignment >> (n_vars - 1 - variable)) & 1) << assignment
        result.append(mask)
    return tuple(result)


def document_truth_bits(document: dict, n_vars: int):
    nodes, root = document["nodes"], document["root"]
    rows = 1 << n_vars
    full_mask = (1 << rows) - 1
    masks = variable_masks(n_vars)
    values = []
    for index, node in enumerate(nodes):
        op = node["op"]
        if op == "var":
            value = masks[node["i"]]
        elif op == "not":
            value = ~values[node["a"]] & full_mask
        else:
            left, right = values[node["a"]], values[node["b"]]
            if op == "and":
                value = left & right
            elif op == "or":
                value = left | right
            elif op == "xor":
                value = left ^ right
            elif op == "imp":
                value = (~left | right) & full_mask
            elif op == "eqv":
                value = ~(left ^ right) & full_mask
            else:
                raise ValueError(f"unsupported source operation at node {index}")
        values.append(value)
    return values[root]


def execute(method: str, row: dict, warm_cache: ProductCache | None):
    document, n_vars = row["expression_v2"], row["n_vars"]
    started = time.perf_counter_ns()
    instrumentation = None
    witness = None
    if method == "set_source_anf":
        partition = source_exact_partition(document, n_vars)
    elif method == "packed_source_anf":
        partition, stats = source_packed_partition(document, n_vars)
        instrumentation = stats.to_dict()
    elif method == "cached_packed_cold":
        partition, stats = source_packed_partition(document, n_vars, cache=ProductCache(1024))
        instrumentation = stats.to_dict()
    elif method == "cached_packed_warm":
        partition, stats = source_packed_partition(document, n_vars, cache=warm_cache)
        instrumentation = stats.to_dict()
    elif method == "bitset_truth_vector_anf":
        analysis = analyze_decomposition(document_truth_bits(document, n_vars), n_vars)
        partition, witness = analysis.row_variables, analysis.witness
    elif method == "numpy_truth_vector_anf":
        analysis = analyze_decomposition(reference_bits(expr_from_json(document), n_vars), n_vars)
        partition, witness = analysis.row_variables, analysis.witness
    else:
        raise ValueError("unknown portable confirmation method")
    proposed = time.perf_counter_ns()
    if method in {"set_source_anf", "packed_source_anf", "cached_packed_cold", "cached_packed_warm"} and partition is not None:
        witness = partition_witness(document_truth_bits(document, n_vars), n_vars, partition)
    checked = time.perf_counter_ns()
    canonical = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
    accepted = partition is not None and witness is not None
    return {
        "schema": "crse-yosys-source-anf-linux-measurement/v1",
        "method": method,
        "split": row["split"],
        "case_id": row["case_id"],
        "n_vars": n_vars,
        "label": row["label"],
        "predicted": int(partition is not None),
        "accepted": accepted,
        "row_variables": list(partition) if partition is not None else None,
        "canonical_partition_match": partition == canonical,
        "semantic_mismatch": bool(accepted and not row["label"]),
        "signature_ns": proposed - started,
        "exact_check_ns": checked - proposed,
        "total_ns": checked - started,
        "instrumentation": instrumentation,
    }


def validate_dataset(path: Path):
    if sha(path) != EXPECTED_DATASET_SHA256:
        raise ValueError("frozen C7 dataset hash mismatch")
    rows = json.loads(path.read_text(encoding="utf-8"))
    if type(rows) is not list or len(rows) != 40:
        raise ValueError("invalid frozen C7 row count")
    identities = set()
    for row in rows:
        if (row.get("schema") != "crse-yosys-human-decomposition-dataset/v1"
                or row.get("split") not in SPLITS or row.get("training_use") is not False
                or row.get("source_commit") != "52ff6fa991f2ab509618d8aaad02f307aac78848"
                or row.get("case_id") in identities):
            raise ValueError("invalid frozen C7 row")
        identities.add(row["case_id"])
        numpy_bits = reference_bits(expr_from_json(row["expression_v2"]), row["n_vars"])
        if numpy_bits != document_truth_bits(row["expression_v2"], row["n_vars"]):
            raise ValueError("independent truth controls disagree")
    for split in SPLITS:
        for label in (0, 1):
            if sum(row["split"] == split and row["label"] == label for row in rows) != 10:
                raise ValueError("unbalanced frozen C7 split")
    return rows


def summarize(rows):
    samples = defaultdict(list)
    for row in rows:
        samples[(row["method"], row["split"], row["case_id"])].append(row)
    per_case = []
    for key, values in sorted(samples.items()):
        first = values[0]
        for field in ("predicted", "accepted", "row_variables", "canonical_partition_match", "semantic_mismatch"):
            if any(row[field] != first[field] for row in values[1:]):
                raise ValueError(f"nondeterministic portable result: {key}/{field}")
        per_case.append({**first,
            "signature_ns": int(statistics.median(row["signature_ns"] for row in values)),
            "exact_check_ns": int(statistics.median(row["exact_check_ns"] for row in values)),
            "total_ns": int(statistics.median(row["total_ns"] for row in values)),
            "timing_repetitions": len(values)})
    grouped = defaultdict(list)
    for row in per_case:
        grouped[(row["method"], row["split"])].append(row)
    result = {}
    for (method, split), values in sorted(grouped.items()):
        totals = [row["total_ns"] for row in values]
        result[f"{method}/{split}"] = {
            "cases": len(values),
            "median_total_ns": statistics.median(totals),
            "p95_total_ns": percentile(totals, .95),
            "maximum_total_ns": max(totals),
            "accuracy": statistics.fmean(row["predicted"] == row["label"] for row in values),
            "canonical_partition_accuracy": statistics.fmean(row["canonical_partition_match"] for row in values),
            "semantic_mismatches": sum(row["semantic_mismatch"] for row in values),
        }
    return per_case, result


def run(dataset: Path, output: Path, repetitions: int = 9):
    if type(repetitions) is not int or not 5 <= repetitions <= 15:
        raise ValueError("repetitions must be an integer in 5..15")
    output.mkdir(parents=True, exist_ok=False)
    documents = validate_dataset(dataset)
    for n_vars in sorted({row["n_vars"] for row in documents}):
        variable_masks(n_vars)
    started = time.perf_counter()
    measurements = []
    cache_telemetry = []
    for split in SPLITS:
        split_rows = [row for row in documents if row["split"] == split]
        for repetition in range(repetitions):
            order = METHODS[repetition % len(METHODS):] + METHODS[:repetition % len(METHODS)]
            for method in order:
                warm_cache = ProductCache(1024) if method == "cached_packed_warm" else None
                for row in split_rows:
                    measurements.append({"repetition": repetition, **execute(method, row, warm_cache)})
                if warm_cache is not None:
                    cache_telemetry.append({"split": split, "repetition": repetition,
                        "final_entries": len(warm_cache), "evictions": warm_cache.evictions})
    per_case, method_summary = summarize(measurements)
    mismatches = sum(row["semantic_mismatch"] or row["predicted"] != row["label"]
                     or not row["canonical_partition_match"] for row in per_case)
    def faster(candidate, baseline):
        return all(method_summary[f"{candidate}/{split}"][metric]
                   <= method_summary[f"{baseline}/{split}"][metric]
                   for split in SPLITS for metric in ("median_total_ns", "p95_total_ns"))
    criteria = {
        "exact": mismatches == 0,
        "packed_beats_direct_bitset": faster("cached_packed_warm", "bitset_truth_vector_anf"),
        "set_beats_packed": faster("set_source_anf", "cached_packed_warm"),
        "warm_cache_beats_cold": faster("cached_packed_warm", "cached_packed_cold"),
    }
    summary = {
        "schema": "crse-yosys-source-anf-linux-confirmation/v1",
        "status": "complete",
        "scientific_scope": "second-machine timing of the unchanged sealed C7 Yosys source-ANF dataset",
        "config": {"cases": 40, "repetitions": repetitions, "cpu_threads": 1,
                   "cache_capacity": 1024, "methods": list(METHODS)},
        "input": {"dataset_sha256": sha(dataset), "training_use": False,
                  "source_commit": "52ff6fa991f2ab509618d8aaad02f307aac78848"},
        "runtime": {"platform": platform.platform(), "python": sys.version.split()[0],
                    "numpy": np.__version__},
        "wall_seconds": time.perf_counter() - started,
        "method_summary": method_summary,
        "cache_telemetry": cache_telemetry,
        "semantic_mismatches": mismatches,
        "criteria": criteria,
    }
    with (output / "measurements.jsonl").open("wb") as handle:
        for row in measurements:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    write_json(output / "per_case.json", per_case)
    write_json(output / "summary.json", summary)
    files = ("measurements.jsonl", "per_case.json", "summary.json")
    write_json(output / "manifest.json", {"schema": "crse-yosys-source-anf-linux-artifacts/v1",
        "status": "complete", "files_sha256": {name: sha(output / name) for name in files}})
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=9)
    args = parser.parse_args(argv)
    result = run(args.dataset, args.output, args.repetitions)
    print(json.dumps({"status": result["status"], "wall_seconds": result["wall_seconds"],
                      "semantic_mismatches": result["semantic_mismatches"],
                      "criteria": result["criteria"]}, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" and result["semantic_mismatches"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
