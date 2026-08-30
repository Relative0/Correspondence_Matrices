"""Independent replay verifier for the sealed Yosys source-ANF run."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.natural_decomposition import analyze_decomposition, partition_witness
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import (
    ProductCache,
    packed_monomials,
    packed_truth_bits,
    source_anf_packed,
    source_packed_partition,
)
from cmbench.recognition.source_interaction import source_anf_monomials, source_exact_partition
from cmbench.recognition.yosys_human_decomposition_data import make_yosys_human_documents
from cmbench.recognition.yosys_source_anf_experiment import (
    DEFAULT_C6_RUN,
    METHODS,
    RUN_SCHEMA,
    criteria,
    document_truth_bits,
    sha,
    source_fingerprints,
    summarize,
    verify_retained_c6,
)

DEFAULT_RUN = ROOT / "docs" / "recognition" / "runs" / "yosys-source-anf-confirmation-20260830-002"
DEFAULT_OUTPUT = ROOT / "docs" / "recognition" / "verification" / "yosys-source-anf-confirmation-20260830-002.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def expected_result(method: str, row: dict, cache: ProductCache | None):
    document, n_vars = row["expression_v2"], row["n_vars"]
    instrumentation = None
    if method == "set_source_anf":
        partition = source_exact_partition(document, n_vars)
        witness = None
    elif method == "packed_source_anf":
        partition, stats = source_packed_partition(document, n_vars)
        instrumentation = stats.to_dict()
        witness = None
    elif method == "cached_packed_source_anf":
        partition, stats = source_packed_partition(document, n_vars, cache=cache)
        instrumentation = stats.to_dict()
        witness = None
    elif method == "numpy_truth_vector_anf":
        analysis = analyze_decomposition(reference_bits(expr_from_json(document), n_vars), n_vars)
        partition, witness = analysis.row_variables, analysis.witness
    elif method == "bitset_truth_vector_anf":
        analysis = analyze_decomposition(document_truth_bits(document, n_vars), n_vars)
        partition, witness = analysis.row_variables, analysis.witness
    else:
        raise ValueError("unknown Yosys source ANF method")
    if method in {"set_source_anf", "packed_source_anf", "cached_packed_source_anf"} and partition is not None:
        witness = partition_witness(document_truth_bits(document, n_vars), n_vars, partition)
    canonical = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
    accepted = partition is not None and witness is not None
    return {
        "row_variables": list(partition) if partition is not None else None,
        "predicted": int(partition is not None),
        "accepted": accepted,
        "canonical_partition_match": partition == canonical,
        "semantic_mismatch": bool(accepted and not row["label"]),
        "truth_sha256": row["semantic_sha256"],
        "instrumentation": instrumentation,
    }


def verify(run: Path, output: Path, base: Path):
    run, output, base = run.resolve(), output.resolve(), base.resolve()
    manifest = load(run / "manifest.json")
    summary = load(run / "summary.json")
    spec = load(run / "run_spec.json")
    if (manifest.get("schema") != "crse-yosys-source-anf-confirmation-artifacts/v1"
            or manifest.get("status") != "complete" or summary.get("schema") != RUN_SCHEMA
            or summary.get("status") != "complete"):
        raise ValueError("invalid or incomplete Yosys source ANF run")
    for relative, expected in manifest["files_sha256"].items():
        if sha(run / relative) != expected:
            raise ValueError(f"changed Yosys source ANF artifact: {relative}")
    if source_fingerprints() != manifest["source_sha256"]:
        raise ValueError("Yosys source ANF source seal changed")
    retained = verify_retained_c6(base)
    if retained["manifest_sha256"] != manifest["retained_c6_manifest_sha256"]:
        raise ValueError("retained C6 dependency changed")

    documents = load(run / "dataset.json")
    regenerated, provenance = make_yosys_human_documents()
    if documents != regenerated or load(run / "dataset_provenance.json") != provenance:
        raise ValueError("sealed Yosys dataset or provenance did not regenerate")

    reconstructed = 0
    for row in documents:
        document, n_vars = row["expression_v2"], row["n_vars"]
        polynomial, _stats = source_anf_packed(document, n_vars)
        numpy_bits = reference_bits(expr_from_json(document), n_vars)
        bitset_bits = document_truth_bits(document, n_vars)
        if numpy_bits != bitset_bits or packed_truth_bits(polynomial, n_vars) != numpy_bits:
            raise ValueError(f"truth reconstruction mismatch: {row['case_id']}")
        if packed_monomials(polynomial, n_vars) != source_anf_monomials(document, n_vars):
            raise ValueError(f"packed/set ANF mismatch: {row['case_id']}")
        reconstructed += 1

    raw = load_jsonl(run / "benchmark_raw.jsonl")
    if len(raw) != len(documents) * len(METHODS):
        raise ValueError("unexpected Yosys source ANF raw-row count")
    raw_by_key = {(row["method"], row["case_id"]): row for row in raw}
    if len(raw_by_key) != len(raw):
        raise ValueError("duplicate Yosys source ANF raw row")

    replayed = 0
    cache_replays = []
    for split in ("sealed_a", "sealed_b"):
        split_rows = [row for row in documents if row["split"] == split]
        for method in METHODS:
            cache = ProductCache(spec["cache_capacity"]) if method == "cached_packed_source_anf" else None
            for row in split_rows:
                expected = expected_result(method, row, cache)
                observed = raw_by_key[(method, row["case_id"])]
                if any(observed[field] != value for field, value in expected.items()):
                    raise ValueError(f"Yosys source ANF replay mismatch: {method}/{row['case_id']}")
                if any(type(observed[field]) is not int or observed[field] < 0
                       for field in ("signature_ns", "exact_check_ns", "total_ns")):
                    raise ValueError("invalid Yosys source ANF timing")
                replayed += 1
            if cache is not None:
                cache_replays.append({"method": method, "split": split,
                    "final_entries": len(cache), "evictions": cache.evictions})

    for expected in cache_replays:
        matches = [row for row in summary["cache_telemetry"]
                   if all(row[key] == value for key, value in expected.items())]
        if len(matches) != spec["repetitions"]:
            raise ValueError("Yosys cache telemetry did not replay")
    recomputed = summarize(raw)
    if recomputed != summary["method_summary"]:
        raise ValueError("Yosys timing summaries did not recompute")
    measured = criteria(recomputed, raw, True)
    if measured != summary["criteria"] or not all(measured[key] for key in (
            "exact", "independent_source", "c6_baseline_cost", "strong_baseline_cost", "safety")):
        raise ValueError("Yosys source ANF confirmation criteria did not pass")

    result = {
        "schema": "crse-yosys-source-anf-confirmation-verification/v1",
        "status": "pass",
        "run": str(run.relative_to(ROOT)).replace("\\", "/"),
        "manifest_sha256": sha(run / "manifest.json"),
        "dataset_rows": len(documents),
        "raw_rows_replayed": replayed,
        "truth_tables_reconstructed": reconstructed,
        "packed_set_matches": reconstructed,
        "cache_streams_replayed": len(cache_replays),
        "semantic_mismatches": 0,
        "criteria": measured,
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--base", type=Path, default=DEFAULT_C6_RUN)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.run, args.output, args.base), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
