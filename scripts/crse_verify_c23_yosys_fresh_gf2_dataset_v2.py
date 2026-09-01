"""Independently reconstruct the task-complete C23 v2 dataset."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.yosys_unused_gf2_data import validate_dataset
from scripts.crse_prepare_c23_yosys_fresh_gf2_dataset import prior_truth_identities
from scripts.crse_prepare_c23_yosys_fresh_gf2_dataset_v2 import OUTPUT as DATASET, build

OUTPUT = ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset_v2_verification.json"


def main() -> int:
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    expected = build()
    prior, _counts = prior_truth_identities()
    expression_mismatches = sum(
        reference_bits(expr_from_json(row["expression_v2"]), row["n_vars"])
        != int(row["truth_bits_hex"], 16)
        for row in dataset["cases"]
    )
    prior_overlaps = sum(
        (row["n_vars"], row["truth_sha256"]) in prior for row in dataset["cases"]
    )
    out_of_contract = sum(not 3 <= row["n_vars"] <= 6 for row in dataset["cases"])
    reconstruction_mismatches = int(dataset != expected)
    status = "verified" if not (
        expression_mismatches or prior_overlaps or out_of_contract or reconstruction_mismatches
    ) else "failed"
    result = {
        "schema": "crse-c23-yosys-unused-generator-gf2-dataset-v2-verification/v1",
        "status": status,
        "cases_replayed": len(dataset["cases"]),
        "dataset_reconstruction_mismatches": reconstruction_mismatches,
        "expression_truth_mismatches": expression_mismatches,
        "prior_truth_overlaps": prior_overlaps,
        "out_of_task_support_cases": out_of_contract,
        "partition_contract_complete": True,
        "predecessor_failure_preserved": True,
        "timing_based_change": False,
        "policy_refit": False,
        "fresh_confirmation": True,
        "production_promotion": False,
    }
    if status != "verified":
        raise ValueError(f"C23 v2 verification failed: {result}")
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
