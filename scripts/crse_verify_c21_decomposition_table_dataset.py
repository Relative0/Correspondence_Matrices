"""Independent source replay for the frozen C21 task-matched dataset."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cmbench.comparative.contracts import canonical_bytes
from cmbench.recognition.blif import parse_blif
from cmbench.recognition.gf2_decomposition import truth_sha256
from cmbench.recognition.portfolio import reference_bits

DATASET = ROOT / "docs/recognition/c21_decomposition_table_dataset.json"
OUTPUT = ROOT / "docs/recognition/c21_decomposition_table_dataset_verification.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    dataset = load(DATASET)
    provenance = dataset["provenance"]
    source_path = ROOT / provenance["source_dataset"]
    source_verify_path = ROOT / provenance["source_verification"]
    source, source_verify = load(source_path), load(source_verify_path)
    if (
        sha256(source_path) != provenance["source_dataset_sha256"]
        or sha256(source_verify_path) != provenance["source_verification_sha256"]
        or source_verify.get("status") != "verified"
        or source_verify.get("cases_replayed") != 96
        or source_verify.get("split_cluster_overlap") != 0
    ):
        raise ValueError("C21 prerequisite fingerprint or replay mismatch")
    source_cases = {case["case_id"]: case for case in source["cases"]}
    cases = dataset["cases"]
    if len(cases) != 96 or len(source_cases) != 96 or len({case["case_id"] for case in cases}) != 96:
        raise ValueError("C21 case identity mismatch")
    netlists = {}
    truth_mismatches = expression_mismatches = source_mismatches = 0
    for case in cases:
        original = source_cases.get(case["case_id"])
        if original is None:
            source_mismatches += 1
            continue
        expected = {**original, "expression_v2": case["expression_v2"],
                    "expression_v2_sha256": case["expression_v2_sha256"],
                    "c21_training_use": False, "c21_policy_selection_use": False,
                    "c21_benchmark_only": True}
        if case != expected:
            source_mismatches += 1
        path = ROOT / case["blif_path"]
        if sha256(path) != case["blif_sha256"]:
            source_mismatches += 1
            continue
        netlist = netlists.setdefault(case["blif_path"], parse_blif(path))
        source_expression, support = netlist.build_expr(case["root_node"], max_identity_nodes=4096)
        source_document = expr_to_json_dag(source_expression)
        loaded_expression = expr_from_json(case["expression_v2"])
        if (
            source_document != case["expression_v2"]
            or expr_to_json_dag(loaded_expression) != case["expression_v2"]
            or hashlib.sha256(canonical_bytes(case["expression_v2"])).hexdigest()
            != case["expression_v2_sha256"]
        ):
            expression_mismatches += 1
        bits = reference_bits(loaded_expression, case["n_vars"])
        if (
            tuple(support) != tuple(case["support"])
            or bits != int(case["truth_bits_hex"], 16)
            or truth_sha256(bits, case["n_vars"]) != case["truth_sha256"]
        ):
            truth_mismatches += 1
    clusters = {
        split: {case["cluster_id"] for case in cases if case["split"] == split}
        for split in ("development", "validation", "confirmation")
    }
    split_overlap = sum(len(clusters[left] & clusters[right]) for left, right in (
        ("development", "validation"), ("development", "confirmation"),
        ("validation", "confirmation")))
    verification = {
        "schema": "crse-c21-task-matched-gf2-dataset-verification/v1",
        "status": "verified" if not (truth_mismatches or expression_mismatches or source_mismatches or split_overlap) else "failed",
        "cases_replayed": len(cases),
        "blif_files_replayed": len(netlists),
        "truth_mismatches": truth_mismatches,
        "expression_mismatches": expression_mismatches,
        "source_record_mismatches": source_mismatches,
        "split_cluster_overlap": split_overlap,
        "timing_based_selection": False,
        "fresh_confirmation": False,
        "network_used": False,
        "production_promotion": False,
    }
    if verification["status"] != "verified":
        raise ValueError(f"C21 dataset verification failed: {verification}")
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
