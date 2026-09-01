"""Independent source/scalar replay for the frozen C23 Yosys dataset."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.yosys_unused_gf2_data import (
    admitted_rows,
    candidate_identity,
    candidates,
    dataset_document,
    scalar_bits,
    select_rows,
    validate_dataset,
)
from scripts.crse_prepare_c23_yosys_fresh_gf2_dataset import (
    C7_DATASET,
    C16_DATASET,
    C18_DATASET,
    C19_DATASET,
    git,
    prior_truth_identities,
    sha256,
)

DATASET = ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset.json"
INVENTORY = ROOT / "docs/recognition/c23_yosys_fresh_source_inventory.json"
OUTPUT = ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset_verification.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    dataset, inventory = load(DATASET), load(INVENTORY)
    validate_dataset(dataset)
    if (inventory.get("status") != "frozen"
            or inventory.get("generator_path_overlap_with_c7") != 0
            or inventory.get("network_used") is not False
            or inventory.get("checkout_modified") is not False):
        raise ValueError("invalid C23 source inventory")
    source_mismatches = 0
    for row in inventory["files"]:
        content = git("show", f"HEAD:{row['path']}")
        blob = git("rev-parse", f"HEAD:{row['path']}").decode().strip()
        if (len(content) != row["bytes"]
                or hashlib.sha256(content).hexdigest() != row["sha256"]
                or blob != row["git_blob_sha1"]):
            source_mismatches += 1
    prior, prior_counts = prior_truth_identities()
    rows, rejected = admitted_rows(prior)
    selected = select_rows(rows, dataset["counts"]["cases"])
    expected = dataset_document(
        rows,
        rejected,
        str(INVENTORY.relative_to(ROOT)).replace("\\", "/"),
        sha256(INVENTORY),
        dataset["counts"]["cases"],
    )
    expected["prior_truth_exclusion"] = {
        "identities": len(prior),
        "new_identities_by_source": prior_counts,
        "sources": {
            "c16": str(C16_DATASET.relative_to(ROOT)).replace("\\", "/"),
            "c18": str(C18_DATASET.relative_to(ROOT)).replace("\\", "/"),
            "c19": str(C19_DATASET.relative_to(ROOT)).replace("\\", "/"),
            "c7": str(C7_DATASET.relative_to(ROOT)).replace("\\", "/"),
        },
        "source_sha256": {name: sha256(path) for name, path in (
            ("c16", C16_DATASET), ("c18", C18_DATASET),
            ("c19", C19_DATASET), ("c7", C7_DATASET))},
    }
    dataset_mismatch = int(dataset != expected)
    candidate_by_id = {row["case_id"]: row for row in rows}
    source_candidates = {
        candidate_identity(candidate): candidate for candidate in candidates()
    }
    scalar_mismatches = expression_mismatches = prior_overlaps = 0
    for frozen in selected:
        replay = candidate_by_id[frozen["case_id"]]
        expression_bits = reference_bits(
            expr_from_json(frozen["expression_v2"]), frozen["n_vars"])
        candidate = source_candidates[replay["selection_sha256"]]
        scalar = scalar_bits(candidate)
        scalar_mismatches += int(scalar != expression_bits)
        expression_mismatches += int(expression_bits != int(frozen["truth_bits_hex"], 16))
        prior_overlaps += int((frozen["n_vars"], frozen["truth_sha256"]) in prior)
    status = "verified" if not (
        source_mismatches or dataset_mismatch or scalar_mismatches
        or expression_mismatches or prior_overlaps
    ) else "failed"
    verification = {
        "schema": "crse-c23-yosys-unused-generator-gf2-dataset-verification/v1",
        "status": status,
        "cases_replayed": len(selected),
        "source_files_replayed": len(inventory["files"]),
        "source_mismatches": source_mismatches,
        "dataset_reconstruction_mismatches": dataset_mismatch,
        "scalar_oracle_mismatches": scalar_mismatches,
        "expression_truth_mismatches": expression_mismatches,
        "prior_truth_overlaps": prior_overlaps,
        "generator_path_overlap_with_c7": 0,
        "timing_based_selection": False,
        "policy_refit": False,
        "network_used": False,
        "fresh_confirmation": True,
        "production_promotion": False,
    }
    if status != "verified":
        raise ValueError(f"C23 dataset verification failed: {verification}")
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
