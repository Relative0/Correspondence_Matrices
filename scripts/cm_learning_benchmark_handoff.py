"""Check current evidence or a normalized benchmark handoff for learning readiness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition import learning_benchmark_handoff as handoff
from cmbench.recognition import version_history_learning_protocol as history


CURRENT_ARTIFACT = (
    ROOT
    / "docs/recognition/runs/version-history-learning-development-20260904-004"
)


def _read_json(path: Path) -> dict:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT) or not resolved.is_file():
        raise ValueError("input must be an existing in-project JSON file")
    if not 0 < resolved.stat().st_size <= 4 * 1024 * 1024:
        raise ValueError("input is outside the JSON size bound")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    return value


def _current_readiness() -> dict:
    manifest = _read_json(CURRENT_ARTIFACT / "manifest.json")
    assessment = _read_json(CURRENT_ARTIFACT / "assessment.json")
    verification = _read_json(CURRENT_ARTIFACT / "independent_verification.json")
    if (
        history.file_sha256(CURRENT_ARTIFACT / "assessment.json")
        != manifest.get("artifacts", {}).get("assessment.json")
        or history.file_sha256(CURRENT_ARTIFACT / "manifest.json")
        != verification.get("manifest_sha256")
        or verification.get("assessment_sha256")
        != manifest.get("artifacts", {}).get("assessment.json")
        or verification.get("status") != "verified_protocol_no_training"
    ):
        return handoff.assess_or_abstain({})
    return handoff.current_evidence_readiness(assessment)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--handoff",
        type=Path,
        help="in-project crse-learning-benchmark-handoff/v1 JSON; omit for current evidence",
    )
    args = parser.parse_args()
    if args.handoff is None:
        result = _current_readiness()
    else:
        try:
            result = handoff.assess_or_abstain(_read_json(args.handoff))
        except (OSError, ValueError, json.JSONDecodeError):
            result = handoff.assess_or_abstain({})
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result.get("development_training_eligible") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
