from __future__ import annotations

import argparse
import json
from pathlib import Path

from cmbench.recognition import query_ladder_development_experiment as experiment
from cmbench.recognition import query_ladder_learning_freeze as query_freeze


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate development-only q64 predictions against the frozen "
            "chance, majority, and analytical-control gates."
        )
    )
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument(
        "--routing-evidence",
        type=Path,
        help=(
            "Optional verified per-host exact medians and candidate inference "
            "costs; when present, require fully charged routed economics."
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    freeze = _read_json(args.freeze)
    handoff = _read_json(args.handoff)
    dataset = _read_json(args.dataset)
    predictions = _read_json(args.predictions)
    freeze_file_sha256 = query_freeze.file_sha256(args.freeze)
    if args.routing_evidence is None:
        result = experiment.assess_candidate_predictions_or_abstain(
            predictions,
            dataset,
            handoff,
            freeze,
            freeze_file_sha256=freeze_file_sha256,
        )
    else:
        result = experiment.assess_candidate_routing_economics_or_abstain(
            _read_json(args.routing_evidence),
            predictions,
            dataset,
            handoff,
            freeze,
            freeze_file_sha256=freeze_file_sha256,
        )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if args.routing_evidence is None:
        passed = result.get("development_signal_established") is True
    else:
        passed = result.get("development_routing_economics_passed") is True
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
