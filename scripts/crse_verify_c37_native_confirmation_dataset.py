"""Independently replay the frozen C37 prospective dataset."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.gf2_multi_root import prospective_sibling_output_workloads
from cmbench.comparative.gf2_wide_repeated_queries import semantic_row
from cmbench.recognition.yosys_native_confirmation_data import (
    prospective_candidates,
    reference_bits_unbounded,
    validate_dataset,
)
from cmbench.recognition.yosys_unused_gf2_data import candidate_identity, scalar_bits
from cmbench.recognition.yosys_wide_restriction_data import truth_sha256_wide
from scripts.crse_verify_c36_wide_repeated_query_dataset import (
    independent_output,
    independent_reduced,
    independent_trace,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def independent_multi_digest(workload) -> str:
    full_truths = tuple(reference_bits_unbounded(root, workload.n_vars)
                        for root in workload.roots)
    rows = []
    for query in workload.trace:
        values = tuple(
            independent_reduced(bits, workload.n_vars, query["fixed"])
            for bits in full_truths
        )
        rows.append({
            "query": query["query"],
            "query_sha256": query["query_sha256"],
            "outputs": [
                {"output_index": index,
                 "semantic": semantic_row(query, value, workload.n_vars)}
                for index, value in enumerate(values)
            ],
        })
    return digest({
        "schema": "crse-native-multi-root-output/v1",
        "workload_id": workload.workload_id,
        "rows": rows,
    })


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path,
        default=ROOT / "docs/recognition/c37_native_exact_confirmation_dataset.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "docs/recognition/c37_native_exact_confirmation_dataset_verification.json",
    )
    args = parser.parse_args()
    dataset_path = args.dataset.resolve()
    dataset = load(dataset_path)
    validate_dataset(dataset)
    freeze_path = ROOT.joinpath(*Path(dataset["provenance"]["freeze_path"]).parts)
    freeze = load(freeze_path)
    if sha256(freeze_path) != dataset["provenance"]["freeze_sha256"]:
        raise ValueError("C37 dataset/freeze binding mismatch")
    source_mismatches = 0
    for relative, identity in freeze["sources"].items():
        path = ROOT.joinpath(*Path(relative).parts)
        source_mismatches += int(
            not path.is_file() or path.stat().st_size != identity["bytes"]
            or sha256(path) != identity["sha256"]
        )
    c36_path = ROOT.joinpath(*Path(dataset["provenance"]["c36_dataset_path"]).parts)
    if sha256(c36_path) != dataset["provenance"]["c36_dataset_sha256"]:
        raise ValueError("C37 prior dataset binding mismatch")
    c36_semantics = {(row["n_vars"], row["truth_sha256"])
                     for row in load(c36_path)["cases"]}
    candidates = {candidate_identity(candidate): candidate
                  for candidate in prospective_candidates()}
    semantic_mismatches = trace_mismatches = selection_mismatches = 0
    truth_overlaps = 0
    observed_semantics: set[tuple[int, str]] = set()
    for row in dataset["cases"]:
        candidate = candidates.get(row["selection_sha256"])
        selection_mismatches += int(
            candidate is None or len(candidate.variable_specs) != row["n_vars"]
            or candidate.family != row["family"]
            or candidate.parameters != row["parameters"]
        )
        if candidate is None:
            continue
        scalar = scalar_bits(candidate)
        expression = reference_bits_unbounded(candidate.expression, row["n_vars"])
        semantic = (row["n_vars"], truth_sha256_wide(scalar, row["n_vars"]))
        truth_overlaps += int(semantic in c36_semantics or semantic in observed_semantics)
        observed_semantics.add(semantic)
        semantic_mismatches += int(
            scalar != expression or scalar != int(row["truth_bits_hex"], 16)
            or semantic[1] != row["truth_sha256"]
        )
        trace = independent_trace(row["case_id"], row["n_vars"])
        trace_mismatches += int(trace != row["c36_trace"])
        semantic_mismatches += int(
            digest(independent_output(row, trace))
            != row["c36_required_output_sha256"]
        )
    workloads = prospective_sibling_output_workloads()
    published_multi = dataset["multi_root"]["workloads"]
    multi_mismatches = int(
        [row["workload_id"] for row in published_multi]
        != [workload.workload_id for workload in workloads]
    )
    for workload, row in zip(workloads, published_multi):
        multi_mismatches += int(
            row["n_vars"] != workload.n_vars
            or row["roots"] != 3
            or row["trace_sha256"] != digest(workload.trace)
            or row["union_document"] != workload.union_document
            or row["separate_document_sha256"]
            != [digest(value) for value in workload.separate_documents]
            or row["sum_separate_nodes"]
            != sum(len(value["nodes"]) for value in workload.separate_documents)
            or row["union_nodes"] != len(workload.union_document["nodes"])
            or row["required_output_sha256"] != independent_multi_digest(workload)
        )
    failures = {
        "source_mismatches": source_mismatches,
        "selection_mismatches": selection_mismatches,
        "semantic_mismatches": semantic_mismatches,
        "trace_mismatches": trace_mismatches,
        "truth_overlaps_with_c36_or_within_c37": truth_overlaps,
        "multi_root_mismatches": multi_mismatches,
    }
    if any(failures.values()):
        raise RuntimeError(f"C37 dataset verification failed: {failures}")
    result = {
        "schema": "crse-c37-native-confirmation-dataset-verification/v1",
        "status": "verified",
        "single_root_cases_replayed": len(dataset["cases"]),
        "single_root_queries_replayed": len(dataset["cases"]) * 64,
        "multi_root_workloads_replayed": len(workloads),
        "multi_root_output_queries_replayed": len(workloads) * 64 * 3,
        "dataset_sha256": sha256(dataset_path),
        "freeze_sha256": sha256(freeze_path),
        "c36_dataset_sha256": sha256(c36_path),
        "selection_recomputed": True,
        "timing_or_method_output_used": False,
        **failures,
    }
    write_new(args.output.resolve(), result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
