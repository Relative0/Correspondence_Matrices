#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.reporting.provenance import sha256_file
from cmbench.tracing.replay import write_json_exclusive
from cmbench.tracing.workload_manifest import WorkloadManifestError, validate_workload_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a real CM workload intake manifest.")
    parser.add_argument("--input", required=True, help="Owner-declared manifest JSON path.")
    parser.add_argument("--output", required=True, help="New validation JSON path; existing files are refused.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite: {output_path}")
    input_meta = {"path": str(input_path), "bytes": input_path.stat().st_size, "sha256": sha256_file(input_path)}
    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
        result = validate_workload_manifest(raw)
        result["input_file"] = input_meta
        exit_code = 0
    except (OSError, json.JSONDecodeError, WorkloadManifestError, ValueError) as exc:
        result = {
            "validation_status": "fail",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "input_file": input_meta,
        }
        exit_code = 1
    write_json_exclusive(output_path, result)
    print(json.dumps(result, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
