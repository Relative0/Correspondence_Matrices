#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.tracing.replay import load_trace_events, summarize_trace_files, write_json_exclusive


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Produce a deterministic logical replay summary for CM workload traces.")
    parser.add_argument("--input", action="append", required=True, help="Validated trace JSONL; repeat for rotations.")
    parser.add_argument("--output", required=True, help="New replay summary JSON path; existing files are refused.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")
    events = load_trace_events(args.input)
    summary = summarize_trace_files(args.input)
    summary.update(
        {
            "replay_status": "pass",
            "replay_mode": "logical_order_only",
            "ordered_event_ids": [event["event_id"] for event in events],
            "cache_policy_simulated": False,
            "expressions_executed": False,
        }
    )
    write_json_exclusive(output, summary)
    print(json.dumps({key: summary[key] for key in ("replay_status", "event_count", "session_count")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
