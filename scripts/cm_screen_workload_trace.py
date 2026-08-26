#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.tracing.opportunity import screen_trace_files
from cmbench.tracing.replay import write_json_exclusive


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Screen validated CM metrics traces against conservative downstream entry gates."
    )
    parser.add_argument("--input", action="append", required=True, help="Trace JSONL; repeat for rotations/files.")
    parser.add_argument("--output", required=True, help="New screen JSON path; existing files are refused.")
    parser.add_argument("--workload-label", required=True, help="Human-readable label recorded in the report.")
    parser.add_argument("--evidence-class", choices=["real", "synthetic", "unknown"], required=True)
    parser.add_argument(
        "--context-stream-kind",
        choices=["natural", "synthetic", "unknown"],
        default="unknown",
    )
    parser.add_argument(
        "--complete-workload",
        action="store_true",
        help="Declare that the inputs contain the complete smaller workload population.",
    )
    parser.add_argument(
        "--complete-family-population",
        action="store_true",
        help="Declare that every available real family revision is included.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")
    report = screen_trace_files(
        args.input,
        workload_label=args.workload_label,
        evidence_class=args.evidence_class,
        context_stream_kind=args.context_stream_kind,
        complete_workload=bool(args.complete_workload),
        complete_family_population=bool(args.complete_family_population),
    )
    write_json_exclusive(output, report)
    print(
        json.dumps(
            {
                "screen_status": report["screen_status"],
                "recommended_next_step": report["recommended_next_step"],
                "event_count": report["trace_quality"]["event_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
