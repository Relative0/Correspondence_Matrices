"""Read-only q64 decision-surface replay and v2 handoff constructor."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition import learning_benchmark_handoff as benchmark_handoff
from cmbench.recognition import query_ladder_decision_surface as surface
from cmbench.recognition import query_ladder_learning_freeze as query_freeze


def _read_json(path: Path) -> dict:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT) or not resolved.is_file():
        raise ValueError("input must be an existing in-project JSON file")
    if not 0 < resolved.stat().st_size <= 32 * 1024 * 1024:
        raise ValueError("input is outside the JSON size bound")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument(
        "--emit-handoff",
        action="store_true",
        help="print the reconstructed v2 handoff and its readiness assessment",
    )
    args = parser.parse_args()
    try:
        evidence = _read_json(args.evidence)
        freeze = _read_json(args.freeze)
        freeze_sha256 = query_freeze.file_sha256(args.freeze.resolve())
        if args.emit_handoff:
            handoff, readiness = surface.build_v2_handoff_or_abstain(
                evidence,
                freeze,
                freeze_file_sha256=freeze_sha256,
            )
            result = {"handoff": handoff, "readiness": readiness}
            passed = readiness.get("development_training_eligible") is True
        else:
            result = surface.assess_decision_surface_or_abstain(
                evidence,
                freeze,
                freeze_file_sha256=freeze_sha256,
            )
            passed = result.get("development_handoff_construction_permitted") is True
    except (OSError, ValueError, json.JSONDecodeError):
        result = benchmark_handoff.assess_or_abstain({})
        passed = False
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
