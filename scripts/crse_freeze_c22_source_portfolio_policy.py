"""Freeze the opt-in C22 source-ANF exact portfolio policy from verified C21 evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.gf2_source_portfolio import (
    freeze_source_portfolio_policy, save_source_portfolio_policy)

RUN = ROOT / "docs/recognition/runs/c21-task-matched-gf2-table-windows-20260831-001"
DATASET = ROOT / "docs/recognition/c21_decomposition_table_dataset.json"
OUTPUT = ROOT / "docs/recognition/c22_source_portfolio_policy.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    verification = json.loads((RUN / "independent_verification.json").read_text(encoding="utf-8"))
    result = json.loads((RUN / "results.json").read_text(encoding="utf-8"))
    if (
        verification.get("status") != "verified"
        or verification.get("measurement_rows_checked") != 3360
        or verification.get("semantic_or_artifact_mismatches") != 0
        or result.get("status") != "complete"
        or result["summary"].get("best_fixed_method") != "source_packed_anf"
        or result["claims"].get("fresh_confirmation") is not False
        or result["claims"].get("production_promotion") is not False
    ):
        raise ValueError("refusing C22 policy freeze: C21 evidence incomplete")
    policy = freeze_source_portfolio_policy(
        c21_manifest_sha256=sha256(RUN / "manifest.json"),
        c21_dataset_sha256=sha256(DATASET))
    save_source_portfolio_policy(policy, OUTPUT)
    print(json.dumps({"path": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
                      "policy_sha256": policy["policy_sha256"],
                      "production_promotion": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
