from __future__ import annotations

import json
from pathlib import Path

from bitset_backend import _eval_words, compile_expr_cse
from scripts.crse_linux_one_pass_confirmation import (
    EXPECTED_PACK_FILE_SHA256, load_cases, scalar_reference, sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "docs" / "recognition" / "linux_confirmation"


def test_frozen_linux_confirmation_package_and_scalar_oracle() -> None:
    cases, document = load_cases(FROZEN / "natural_normalization_cases.json")
    first = cases[0]
    variables = tuple(f"x{i}" for i in range(first["n_vars"]))
    packed = _eval_words(compile_expr_cse(first["expression"], flatten=True), variables, {})

    assert len(cases) == 32
    assert document["training_use"] is False
    assert scalar_reference(first["expression"], first["n_vars"]) == packed
    assert sha256_file(FROZEN / "proved_rule_pack.json") == EXPECTED_PACK_FILE_SHA256


def test_historical_linux_manifest_is_immutable_and_live_source_drift_is_explicit() -> None:
    manifest = json.loads((FROZEN / "linux_one_pass_upload_manifest.json").read_text(encoding="utf-8"))

    assert manifest["authorization_status"] == "pending"
    assert manifest["file_count"] == len(manifest["files"]) == 16
    assert manifest["bytes"] == sum(row["bytes"] for row in manifest["files"])
    mismatches = []
    for row in manifest["files"]:
        path = ROOT / row["source"]
        if path.stat().st_size != row["bytes"] or sha256_file(path) != row["sha256"]:
            mismatches.append(row["source"])
    assert mismatches == ["bitset_backend.py", "cm_exprlib.py"]
