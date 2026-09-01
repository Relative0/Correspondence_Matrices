"""Freeze the task-complete support-3..6 revision of the C23 corpus."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.yosys_unused_gf2_data import (
    admitted_rows,
    dataset_document,
    validate_dataset,
)
from scripts.crse_prepare_c23_yosys_fresh_gf2_dataset import (
    C7_DATASET,
    C16_DATASET,
    C18_DATASET,
    C19_DATASET,
    prior_truth_identities,
    sha256,
    write_new,
)

INVENTORY = ROOT / "docs/recognition/c23_yosys_fresh_source_inventory.json"
OUTPUT = ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset_v2.json"


def build() -> dict:
    prior, prior_counts = prior_truth_identities()
    rows, rejected = admitted_rows(prior)
    bounded = [row for row in rows if row["n_vars"] <= 6]
    rejected = {**rejected, "task_support_7_to_10_excluded": len(rows) - len(bounded)}
    document = dataset_document(
        bounded,
        rejected,
        str(INVENTORY.relative_to(ROOT)).replace("\\", "/"),
        sha256(INVENTORY),
        48,
    )
    document["revision"] = {
        "id": "task-complete-v2",
        "predecessor": "docs/recognition/c23_yosys_fresh_gf2_dataset.json",
        "predecessor_sha256": sha256(ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset.json"),
        "reason": "support 3..6 makes the unchanged 64-partition comparison set complete",
        "timing_based_change": False,
        "predecessor_timing_result_complete": False,
    }
    document["provenance"]["task_support"] = [3, 4, 5, 6]
    document["provenance"]["partition_contract_complete"] = True
    document["prior_truth_exclusion"] = {
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
    validate_dataset(document)
    return document


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite frozen C23 v2 dataset")
    document = build()
    write_new(OUTPUT, document)
    print(json.dumps(document["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
