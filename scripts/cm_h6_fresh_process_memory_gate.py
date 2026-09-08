"""CLI for the frozen local H6 fresh-process memory calibration gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import h6_fresh_process_memory_gate as gate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--project-root", type=Path, default=ROOT)
    freeze.add_argument("--output", type=Path, required=True)
    worker = sub.add_parser("worker")
    worker.add_argument("--project-root", type=Path, required=True)
    worker.add_argument("--freeze", type=Path, required=True)
    worker.add_argument("--row-id", required=True)
    run = sub.add_parser("run")
    run.add_argument("--project-root", type=Path, default=ROOT)
    run.add_argument("--freeze", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--phase-timeout-seconds", type=float, default=60.0)
    summarize = sub.add_parser("summarize")
    summarize.add_argument("--freeze", type=Path, required=True)
    summarize.add_argument("--raw", type=Path, required=True)
    summarize.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "freeze":
        value = gate.freeze_to_path(args.project_root, args.output)
    elif args.command == "worker":
        return gate.worker_main(args.project_root, args.freeze, args.row_id)
    elif args.command == "run":
        value = gate.run_campaign(
            project_root=args.project_root,
            freeze_path=args.freeze,
            output_dir=args.output_dir,
            python_executable=Path(sys.executable),
            worker_script=Path(__file__).resolve(),
            phase_timeout_seconds=args.phase_timeout_seconds,
        )
        value["summary"] = gate.summary_to_path(
            args.output_dir / "RAW.jsonl", args.freeze, args.output_dir / "SUMMARY.json"
        )
    else:
        value = gate.summary_to_path(args.raw, args.freeze, args.output)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

