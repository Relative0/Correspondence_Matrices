"""Independent replay verifier for the natural source-ANF hybrid run."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.natural_decomposition import analyze_decomposition
from cmbench.recognition.natural_decomposition_experiment import DEFAULT_SCOUT
from cmbench.recognition.natural_decomposition_matched_data import make_matched_natural_documents
from cmbench.recognition.natural_source_anf_experiment import (
    DEFAULT_C5_RUN,
    METHODS,
    _criteria,
    _gate_selection,
    _summaries,
    sha,
    source_fingerprints,
    verify_retained_c5,
)
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import (
    ProductCache,
    packed_monomials,
    packed_truth_bits,
    source_anf_packed,
    source_hybrid_partition,
    source_packed_partition,
)
from cmbench.recognition.source_interaction import source_anf_monomials, source_exact_partition

DEFAULT_RUN = ROOT / "docs" / "recognition" / "runs" / "natural-source-anf-hybrid-20260830-004"
DEFAULT_OUTPUT = ROOT / "docs" / "recognition" / "verification" / "natural-source-anf-hybrid-20260830-004.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _expected_partition(row: dict, method: str, cache: ProductCache | None, gate: int):
    document, n_vars = row["expression_v2"], row["n_vars"]
    if method == "set_source_anf":
        return source_exact_partition(document, n_vars), method, None
    if method == "packed_source_anf":
        partition, stats = source_packed_partition(document, n_vars)
        return partition, method, stats.to_dict()
    if method == "cached_packed_source_anf":
        partition, stats = source_packed_partition(document, n_vars, cache=cache)
        return partition, method, stats.to_dict()
    if method == "budgeted_hybrid":
        partition, path, stats = source_hybrid_partition(
            document, n_vars, cache=cache, product_pair_budget=gate
        )
        return partition, path, stats.to_dict()
    bits = reference_bits(expr_from_json(document), n_vars)
    return analyze_decomposition(bits, n_vars).row_variables, method, None


def verify(run: Path, output: Path, scout: Path, base: Path):
    run, output, scout, base = run.resolve(), output.resolve(), scout.resolve(), base.resolve()
    manifest, summary, spec = load(run / "manifest.json"), load(run / "summary.json"), load(run / "run_spec.json")
    if (manifest.get("schema") != "crse-natural-source-anf-hybrid-artifacts/v1"
            or manifest.get("status") != "complete" or summary.get("status") != "complete"
            or summary.get("schema") != "crse-natural-source-anf-hybrid-experiment/v1"):
        raise ValueError("invalid or incomplete natural source ANF run")
    for relative, expected in manifest["files_sha256"].items():
        if sha(run / relative) != expected:
            raise ValueError(f"changed source ANF artifact: {relative}")
    if source_fingerprints(scout) != manifest["source_sha256"]:
        raise ValueError("source ANF source seal changed")
    retained = verify_retained_c5(base)
    if retained["manifest_sha256"] != manifest["retained_c5_manifest_sha256"]:
        raise ValueError("retained C5 dependency changed")
    if sha(run / "dataset.json") != retained["dataset_sha256"]:
        raise ValueError("run dataset does not match retained C5 dataset")
    documents = load(run / "dataset.json")
    regenerated, _provenance = make_matched_natural_documents(scout, seed=spec["dataset_seed"])
    if documents != regenerated:
        raise ValueError("frozen natural source ANF dataset did not regenerate")

    gate = _gate_selection(documents, spec["validation_gate_quantile"], lambda: None)
    if gate != load(run / "gate_selection.json") or gate != summary["gate_selection"]:
        raise ValueError("validation-only product budget did not replay")
    raw = load_jsonl(run / "benchmark_raw.jsonl")
    if len(raw) != len(documents) * len(METHODS):
        raise ValueError("unexpected source ANF raw-row count")
    raw_by_key = {(row["method"], row["case_id"]): row for row in raw}
    if len(raw_by_key) != len(raw):
        raise ValueError("duplicate source ANF raw row")

    reconstructed = 0
    set_matches = 0
    for row in documents:
        polynomial, _stats = source_anf_packed(row["expression_v2"], row["n_vars"])
        if packed_monomials(polynomial, row["n_vars"]) != source_anf_monomials(
                row["expression_v2"], row["n_vars"]):
            raise ValueError(f"packed/set ANF disagreement: {row['case_id']}")
        bits = reference_bits(expr_from_json(row["expression_v2"]), row["n_vars"])
        if packed_truth_bits(polynomial, row["n_vars"]) != bits:
            raise ValueError(f"packed truth reconstruction failed: {row['case_id']}")
        reconstructed += 1
        set_matches += 1

    replayed = 0
    cache_replays = []
    for split in ("train", "validation", "test", "confirmatory"):
        split_rows = [row for row in documents if row["split"] == split]
        for method in METHODS:
            cache = ProductCache(spec["cache_capacity"]) if method in {
                "cached_packed_source_anf", "budgeted_hybrid"} else None
            for row in split_rows:
                partition, path, instrumentation = _expected_partition(
                    row, method, cache, gate["product_pair_budget"]
                )
                observed = raw_by_key[(method, row["case_id"])]
                canonical = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
                expected = {"path": path, "row_variables": list(partition) if partition is not None else None,
                    "predicted": int(partition is not None), "canonical_partition_match": partition == canonical,
                    "semantic_mismatch": bool(partition is not None and not row["label"]),
                    "truth_sha256": row["semantic_sha256"], "instrumentation": instrumentation}
                if any(observed[field] != value for field, value in expected.items()):
                    raise ValueError(f"source ANF replay mismatch: {method}/{row['case_id']}")
                if any(type(observed[field]) is not int or observed[field] < 0
                       for field in ("signature_ns", "exact_check_ns", "total_ns")):
                    raise ValueError("invalid source ANF timing")
                replayed += 1
            if cache is not None:
                cache_replays.append({"method": method, "split": split,
                    "final_entries": len(cache), "evictions": cache.evictions})

    observed_cache = summary["cache_telemetry"]
    for expected in cache_replays:
        matching = [row for row in observed_cache if all(row[key] == value for key, value in expected.items())]
        if len(matching) != spec["repetitions"]:
            raise ValueError("cache telemetry did not replay across repetitions")
    recomputed_summary = _summaries(raw)
    if recomputed_summary != summary["method_summary"]:
        raise ValueError("source ANF summaries did not recompute")
    criteria = _criteria(recomputed_summary, raw, observed_cache)
    criteria["safety"] = criteria["exact"] and not any(row["semantic_mismatch"] for row in raw)
    if criteria != summary["criteria"] or not all(
            criteria[key] for key in ("exact", "packed_core", "cached_packed_core", "safety")):
        raise ValueError("source ANF criteria did not independently pass")
    result = {"schema": "crse-natural-source-anf-hybrid-verification/v1", "status": "pass",
        "run": str(run.relative_to(ROOT)).replace("\\", "/"), "manifest_sha256": sha(run / "manifest.json"),
        "dataset_rows": len(documents), "raw_rows_replayed": replayed,
        "truth_tables_reconstructed": reconstructed, "packed_set_matches": set_matches,
        "cache_streams_replayed": len(cache_replays),
        "fallback_rows": sum(row["path"] == "truth_vector_anf_fallback" for row in raw),
        "semantic_mismatches": 0, "criteria": criteria,
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--scout", type=Path, default=DEFAULT_SCOUT)
    parser.add_argument("--base", type=Path, default=DEFAULT_C5_RUN)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.run, args.output, args.scout, args.base), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
