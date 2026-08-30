"""Independent semantic replay of the retrieved C7 Linux timing artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.natural_decomposition import analyze_decomposition, partition_witness
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import ProductCache, source_packed_partition
from cmbench.recognition.source_interaction import source_exact_partition
from cmbench.recognition.yosys_source_anf_experiment import document_truth_bits

DEFAULT_STUDY = (ROOT / "docs" / "recognition" / "c7_linux_confirmation" /
                 "runpod-c7-linux-single-port-execute-001" / "evidence" / "run-output" /
                 "yosys-c7-linux-confirmation")
DEFAULT_DATASET = (ROOT / "docs" / "recognition" / "runs" /
                   "yosys-source-anf-confirmation-20260830-002" / "dataset.json")
DEFAULT_OUTPUT = (ROOT / "docs" / "recognition" / "verification" /
                  "yosys-source-anf-linux-confirmation-20260830-001.json")
METHODS = ("set_source_anf", "packed_source_anf", "cached_packed_cold",
           "cached_packed_warm", "bitset_truth_vector_anf", "numpy_truth_vector_anf")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, quantile):
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower, upper = int(index), min(int(index) + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def expected(method: str, row: dict, warm_cache: ProductCache | None):
    document, n_vars = row["expression_v2"], row["n_vars"]
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
        raise ValueError("unknown Linux replay method")
    if method in METHODS[:4] and partition is not None:
        witness = partition_witness(document_truth_bits(document, n_vars), n_vars, partition)
    canonical = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
    accepted = partition is not None and witness is not None
    return {"predicted": int(partition is not None), "accepted": accepted,
            "row_variables": list(partition) if partition is not None else None,
            "canonical_partition_match": partition == canonical,
            "semantic_mismatch": bool(accepted and not row["label"]),
            "instrumentation": instrumentation}


def recompute(measurements):
    samples = defaultdict(list)
    for row in measurements:
        samples[(row["method"], row["split"], row["case_id"])].append(row)
    per_case = []
    for key, values in sorted(samples.items()):
        first = values[0]
        per_case.append({**first,
            "signature_ns": int(statistics.median(row["signature_ns"] for row in values)),
            "exact_check_ns": int(statistics.median(row["exact_check_ns"] for row in values)),
            "total_ns": int(statistics.median(row["total_ns"] for row in values)),
            "timing_repetitions": len(values)})
    grouped = defaultdict(list)
    for row in per_case:
        grouped[(row["method"], row["split"])].append(row)
    method_summary = {}
    for (method, split), values in sorted(grouped.items()):
        totals = [row["total_ns"] for row in values]
        method_summary[f"{method}/{split}"] = {"cases": len(values),
            "median_total_ns": statistics.median(totals), "p95_total_ns": percentile(totals, .95),
            "maximum_total_ns": max(totals),
            "accuracy": statistics.fmean(row["predicted"] == row["label"] for row in values),
            "canonical_partition_accuracy": statistics.fmean(row["canonical_partition_match"] for row in values),
            "semantic_mismatches": sum(row["semantic_mismatch"] for row in values)}
    mismatches = sum(row["semantic_mismatch"] or row["predicted"] != row["label"]
                     or not row["canonical_partition_match"] for row in per_case)
    def faster(candidate, baseline):
        return all(method_summary[f"{candidate}/{split}"][metric]
                   <= method_summary[f"{baseline}/{split}"][metric]
                   for split in ("sealed_a", "sealed_b")
                   for metric in ("median_total_ns", "p95_total_ns"))
    criteria = {"exact": mismatches == 0,
        "packed_beats_direct_bitset": faster("cached_packed_warm", "bitset_truth_vector_anf"),
        "set_beats_packed": faster("set_source_anf", "cached_packed_warm"),
        "warm_cache_beats_cold": faster("cached_packed_warm", "cached_packed_cold")}
    return per_case, method_summary, criteria, mismatches


def verify(study: Path, dataset_path: Path, output: Path):
    study, dataset_path, output = study.resolve(), dataset_path.resolve(), output.resolve()
    dataset = load(dataset_path)
    if sha(dataset_path) != "3ca1ae22fd79bac68c37e78fe497701cb100713b0077130e5263cb1f66145864":
        raise ValueError("changed C7 dataset")
    manifest, summary = load(study / "manifest.json"), load(study / "summary.json")
    measurements = [json.loads(line) for line in (study / "measurements.jsonl").read_text().splitlines()]
    observed_per_case = load(study / "per_case.json")
    expected_hashes = {name: sha(study / name) for name in ("measurements.jsonl", "per_case.json", "summary.json")}
    if manifest.get("files_sha256") != expected_hashes:
        raise ValueError("changed Linux timing artifact")
    by_key = {(row["repetition"], row["method"], row["case_id"]): row for row in measurements}
    if len(by_key) != 2160:
        raise ValueError("unexpected or duplicate Linux measurement rows")
    replayed = 0
    for split in ("sealed_a", "sealed_b"):
        rows = [row for row in dataset if row["split"] == split]
        for repetition in range(9):
            for method in METHODS:
                cache = ProductCache(1024) if method == "cached_packed_warm" else None
                for row in rows:
                    observed = by_key[(repetition, method, row["case_id"])]
                    result = expected(method, row, cache)
                    if any(observed[field] != value for field, value in result.items()):
                        raise ValueError(f"Linux semantic replay mismatch: {repetition}/{method}/{row['case_id']}")
                    if any(type(observed[field]) is not int or observed[field] < 0
                           for field in ("signature_ns", "exact_check_ns", "total_ns")):
                        raise ValueError("invalid Linux timing")
                    replayed += 1
    per_case, method_summary, criteria, mismatches = recompute(measurements)
    if (per_case != observed_per_case or method_summary != summary.get("method_summary")
            or criteria != summary.get("criteria") or mismatches != summary.get("semantic_mismatches")
            or not criteria["exact"] or mismatches != 0):
        raise ValueError("Linux timing summaries or criteria did not independently replay")
    result = {"schema": "crse-yosys-source-anf-linux-confirmation-verification/v1",
        "status": "pass", "study": str(study.relative_to(ROOT)).replace("\\", "/"),
        "dataset_sha256": sha(dataset_path), "measurement_rows_replayed": replayed,
        "per_case_rows_recomputed": len(per_case), "semantic_mismatches": 0,
        "criteria": criteria, "method_summary": method_summary,
        "artifact_manifest_sha256": sha(study / "manifest.json"),
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.study, args.dataset, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
