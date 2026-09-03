"""Verify the dormant architecture-comparison prefreeze against bound evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.comparison_prefreeze import build_prefreeze, validate_prefreeze
from cmbench.comparative.contracts import canonical_bytes
from scripts.crse_prepare_architecture_comparison_prefreeze import C38, FUNCTIONAL, NATIVE, _load, _write


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    recorded = json.loads((artifact / "PREFREEZE.json").read_text(encoding="utf-8"))
    validate_prefreeze(recorded)
    native, native_sha = _load(NATIVE)
    c38, c38_sha = _load(C38)
    plan, plan_sha = _load(FUNCTIONAL / "PLAN.json")
    result, result_sha = _load(FUNCTIONAL / "RESULT.json")
    replay = build_prefreeze(
        source_checkpoint=recorded["source_checkpoint"],
        native_closure=native,
        native_closure_sha256=native_sha,
        c38_adjudication=c38,
        c38_adjudication_sha256=c38_sha,
        functional_plan=plan,
        functional_plan_sha256=plan_sha,
        functional_result=result,
        functional_result_sha256=result_sha,
    )
    if canonical_bytes(replay) != canonical_bytes(recorded):
        raise ValueError("prefreeze replay mismatch")
    verification = {
        "schema": "cm-architecture-comparison-prefreeze-verification/v1",
        "status": "verified_ready_for_corpus_freeze",
        "prefreeze_sha256": hashlib.sha256(
            (artifact / "PREFREEZE.json").read_bytes()
        ).hexdigest(),
        "replay_byte_identical": True,
        "fresh_or_prospective_data_consumed": False,
        "timing_evidence_produced": False,
        "cloud_resource_created": False,
    }
    _write(artifact / "VERIFICATION.json", verification)
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
