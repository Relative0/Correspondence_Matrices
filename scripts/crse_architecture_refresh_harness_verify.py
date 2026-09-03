"""Independently replay a four-lane functional-admission artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.architecture_refresh_harness import (
    find_native_library,
    run_functional_validation,
    validate_functional_result,
    validate_plan,
)
from cmbench.comparative.contracts import canonical_bytes


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json",
    )
    parser.add_argument("--native-library", type=Path)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    plan = json.loads((artifact / "PLAN.json").read_text(encoding="utf-8"))
    recorded = json.loads((artifact / "RESULT.json").read_text(encoding="utf-8"))
    validate_plan(plan)
    validate_functional_result(recorded, plan)
    dataset_bytes = args.dataset.resolve().read_bytes()
    if hashlib.sha256(dataset_bytes).hexdigest() != recorded["dataset_sha256"]:
        raise ValueError("functional dataset drift")
    native_path = None
    if recorded["native_identity"] is not None:
        native_path = (
            args.native_library.resolve()
            if args.native_library is not None
            else find_native_library(ROOT)
        )
        if native_path is None:
            raise ValueError("recorded native arm cannot be replayed")
        if hashlib.sha256(native_path.read_bytes()).hexdigest() != recorded["native_identity"]["sha256"]:
            raise ValueError("native library drift")
    replay = run_functional_validation(
        json.loads(dataset_bytes),
        dataset_sha256=recorded["dataset_sha256"],
        native_library_path=native_path,
    )
    if canonical_bytes(replay) != canonical_bytes(recorded):
        raise ValueError("functional replay is not byte-identical")
    verification = {
        "schema": "cm-architecture-refresh-functional-verification/v1",
        "status": "verified",
        "artifact_result_sha256": hashlib.sha256(
            (artifact / "RESULT.json").read_bytes()
        ).hexdigest(),
        "replay_byte_identical": True,
        "all_exact": True,
        "timing_evidence_produced": False,
        "performance_claim_permitted": False,
    }
    _write_json(artifact / "VERIFICATION.json", verification)
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
