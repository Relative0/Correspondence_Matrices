"""Independently rebuild and verify the frozen C27 confirmation corpus."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.gf2_decomposition import truth_sha256
from cmbench.recognition.gf2_support_aware_policy import load_support_aware_policy
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.yosys_c27_gf2_data import (
    SOURCE_COMMIT, SOURCE_FILES, SOURCE_GENERATORS, SOURCE_URL,
    admitted_rows, candidate_identity, dataset_document, scalar_bits, candidates,
    validate_dataset,
)
from scripts.crse_prepare_c27_confirmation_corpus import PRIOR, prior_truths

REPOSITORY = ROOT / "external/yosys-bench-confirmation-20260830"
POLICY = ROOT / "docs/recognition/c27_support_aware_policy.json"
INVENTORY = ROOT / "docs/recognition/c27_yosys_source_inventory.json"
DATASET = ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset.json"
OUTPUT = ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset_verification.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=REPOSITORY, check=True, stdout=subprocess.PIPE,
    ).stdout


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rebuilt_inventory(prior_generators: set[str]) -> dict:
    files = []
    for name in ("LICENSE.txt", *SOURCE_FILES):
        content = git("show", f"HEAD:{name}")
        files.append({
            "path": name,
            "bytes": len(content),
            "sha256": sha256_bytes(content),
            "git_blob_sha1": git("rev-parse", f"HEAD:{name}").decode().strip(),
        })
    return {
        "schema": "crse-c27-yosys-unused-generator-source-inventory/v1",
        "status": "frozen",
        "repository": SOURCE_URL,
        "commit": SOURCE_COMMIT,
        "license": "ISC",
        "files": files,
        "prior_generators": sorted(prior_generators),
        "c27_generators": list(SOURCE_GENERATORS),
        "generator_path_overlap_with_prior": 0,
        "network_used": False,
        "checkout_modified": False,
    }


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite frozen C27 corpus verification")
    if git("rev-parse", "HEAD").decode().strip() != SOURCE_COMMIT:
        raise ValueError("pinned Yosys-bench checkout changed")
    policy = load_support_aware_policy(POLICY)
    inventory = load(INVENTORY)
    dataset = load(DATASET)
    validate_dataset(dataset)
    prior, prior_counts, prior_generators = prior_truths()
    expected_inventory = rebuilt_inventory(prior_generators)
    if inventory != expected_inventory:
        raise ValueError("C27 source inventory reconstruction mismatch")
    if prior_generators & set(SOURCE_GENERATORS):
        raise ValueError("C27 generator group overlaps prior evidence")

    rows, rejected = admitted_rows(prior)
    expected = dataset_document(
        rows,
        rejected,
        inventory_path=str(INVENTORY.relative_to(ROOT)).replace("\\", "/"),
        inventory_sha256=sha256(INVENTORY),
        policy_path=str(POLICY.relative_to(ROOT)).replace("\\", "/"),
        policy_file_sha256=sha256(POLICY),
        policy_sha256=policy["policy_sha256"],
    )
    expected["prior_truth_exclusion"] = {
        "identities": len(prior),
        "new_identities_by_source": prior_counts,
        "sources": [str(path.relative_to(ROOT)).replace("\\", "/") for path in PRIOR],
        "source_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path) for path in PRIOR
        },
    }
    reconstruction_mismatches = int(dataset != expected)
    by_identity = {candidate_identity(item): item for item in candidates()}
    # Dataset selection identities use canonical JSON; replay selected expressions and
    # their scalar oracles directly, then also compare against all excluded prior truths.
    expression_truth_mismatches = scalar_oracle_mismatches = prior_overlaps = 0
    for row in dataset["cases"]:
        expression = expr_from_json(row["expression_v2"])
        bits = reference_bits(expression, row["n_vars"])
        expression_truth_mismatches += bits != int(row["truth_bits_hex"], 16)
        prior_overlaps += (row["n_vars"], row["truth_sha256"]) in prior
        selected_candidate = by_identity.get(row["selection_sha256"])
        if selected_candidate is None or scalar_bits(selected_candidate) != bits:
            scalar_oracle_mismatches += 1

    failures = (
        reconstruction_mismatches + expression_truth_mismatches
        + scalar_oracle_mismatches + prior_overlaps
    )
    result = {
        "schema": "crse-c27-yosys-unused-generator-gf2-dataset-verification/v1",
        "status": "verified" if failures == 0 else "failed",
        "cases_replayed": len(dataset["cases"]),
        "candidate_pool_rebuilt": len(rows),
        "source_files_replayed": len(inventory["files"]),
        "dataset_reconstruction_mismatches": reconstruction_mismatches,
        "expression_truth_mismatches": expression_truth_mismatches,
        "scalar_oracle_mismatches": scalar_oracle_mismatches,
        "prior_truth_overlaps": prior_overlaps,
        "generator_path_overlaps": len(prior_generators & set(SOURCE_GENERATORS)),
        "balanced_widths": dataset["counts"]["by_n_vars"] == {
            str(n): 12 for n in range(3, 7)
        },
        "policy_frozen_before_dataset": True,
        "timing_based_selection": False,
        "policy_refit": False,
        "fresh_confirmation": True,
        "production_promotion": False,
    }
    if result["status"] != "verified" or result["balanced_widths"] is not True:
        raise ValueError(f"C27 corpus verification failed: {result}")
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
