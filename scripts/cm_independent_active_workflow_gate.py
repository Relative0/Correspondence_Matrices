"""CLI for the independent active CM workflow discovery and local profile gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import independent_active_workflow_gate as gate


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--project-root", type=Path, default=ROOT)
    checkpoint.add_argument("--original-checkout", type=Path, required=True)
    checkpoint.add_argument("--output", type=Path, required=True)
    discovery = sub.add_parser("discovery")
    discovery.add_argument("--project-root", type=Path, default=ROOT)
    discovery.add_argument("--checkpoint", type=Path, required=True)
    discovery.add_argument("--output", type=Path, required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--project-root", type=Path, default=ROOT)
    freeze.add_argument("--checkpoint", type=Path, required=True)
    freeze.add_argument("--discovery", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    profile = sub.add_parser("profile")
    profile.add_argument("--project-root", type=Path, default=ROOT)
    profile.add_argument("--freeze", type=Path, required=True)
    profile.add_argument("--output", type=Path, required=True)
    worker = sub.add_parser("worker")
    worker.add_argument("--project-root", type=Path, required=True)
    worker.add_argument("--freeze", type=Path, required=True)
    worker.add_argument("--row-id", required=True)
    memory = sub.add_parser("memory")
    memory.add_argument("--project-root", type=Path, default=ROOT)
    memory.add_argument("--freeze", type=Path, required=True)
    memory.add_argument("--output", type=Path, required=True)
    memory.add_argument("--timeout", type=float, default=60.0)
    summarize = sub.add_parser("summarize")
    summarize.add_argument("--freeze", type=Path, required=True)
    summarize.add_argument("--profile", type=Path, required=True)
    summarize.add_argument("--memory", type=Path, required=True)
    summarize.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "checkpoint": value = gate.checkpoint_to_path(args.project_root, args.original_checkout, args.output)
    elif args.command == "discovery": value = gate.discovery_to_path(args.project_root, args.checkpoint, args.output)
    elif args.command == "freeze": value = gate.freeze_to_path(args.project_root, args.checkpoint, args.discovery, args.output)
    elif args.command == "profile": value = gate.run_profile(args.project_root, args.freeze, args.output)
    elif args.command == "worker": return gate.worker_main(args.project_root, args.freeze, args.row_id)
    elif args.command == "memory": value = gate.run_memory(args.project_root, args.freeze, args.output, Path(sys.executable), Path(__file__).resolve(), args.timeout)
    else: value = gate.summary_to_path(args.profile, args.memory, args.freeze, args.output)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
