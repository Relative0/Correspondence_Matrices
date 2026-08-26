#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.tracing.replay import TraceFileError, summarize_trace_files, write_json_exclusive


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and audit metrics-only CM workload trace JSONL files.")
    parser.add_argument("--input", action="append", required=True, help="Trace JSONL path; repeat for rotations/files.")
    parser.add_argument("--output", required=True, help="New audit JSON path; existing files are refused.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")
    try:
        summary = summarize_trace_files(args.input)
        summary.update({"validation_status": "pass", "scrub_status": "metrics_allowlist_pass"})
        status = 0
    except (OSError, TraceFileError, ValueError) as exc:
        summary = {
            "validation_status": "fail",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "input_files": [str(path) for path in args.input],
        }
        status = 1
    write_json_exclusive(output, summary)
    print(json.dumps(summary, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
