"""Read-only checker for memory-learning measurements and predictions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition import memory_learning_evidence as memory


def _read_json(path: Path) -> dict:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT) or not resolved.is_file():
        raise ValueError("input must be an existing in-project JSON file")
    if not 0 < resolved.stat().st_size <= 8 * 1024 * 1024:
        raise ValueError("input is outside the JSON size bound")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, required=True)
    candidates = parser.add_mutually_exclusive_group()
    candidates.add_argument("--predictions", type=Path)
    candidates.add_argument(
        "--neural-predictions",
        type=Path,
        nargs="+",
        help="all prediction documents named by the precommitted seed schedule",
    )
    parser.add_argument(
        "--neural-protocol",
        type=Path,
        help="candidate specification and seed schedule frozen before evaluation",
    )
    args = parser.parse_args()
    try:
        measurements = _read_json(args.measurements)
        if args.neural_predictions is not None:
            if args.neural_protocol is None:
                raise ValueError("neural predictions require a neural protocol")
            result = memory.assess_neural_seed_predictions_or_abstain(
                _read_json(args.neural_protocol),
                [_read_json(path) for path in args.neural_predictions],
                measurements,
            )
            passed = result.get("development_signal_established") is True
        elif args.neural_protocol is not None:
            raise ValueError("neural protocol requires neural predictions")
        elif args.predictions is None:
            result = memory.assess_decision_surface_or_abstain(measurements)
            passed = result.get("development_training_eligible") is True
        else:
            result = memory.assess_candidate_predictions_or_abstain(
                _read_json(args.predictions),
                measurements,
            )
            passed = result.get("development_signal_established") is True
    except (OSError, ValueError, json.JSONDecodeError):
        result = memory.assess_decision_surface_or_abstain({})
        passed = False
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
