#!/usr/bin/env python3
"""Build or verify an immutable Phase 6 corpus/schedule review package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.corpus_freeze import build_freeze, evaluate_gate, validate_freeze, verify_sources
from cmbench.comparative.evidence import publish_json


def strict_load(path: Path):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    def constant(_value):
        raise ValueError("nonfinite JSON constant")

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(args) -> int:
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing existing output directory: {output}")
    draft = strict_load(args.draft)
    freeze = build_freeze(draft, args.project_root)
    source_check = verify_sources(freeze, args.project_root)
    gate = evaluate_gate(freeze, source_check)
    publish_json(output / "freeze.json", freeze)
    publish_json(output / "source-check.json", source_check)
    publish_json(output / "gate.json", gate)
    artifacts = [output / name for name in ("freeze.json", "source-check.json", "gate.json")]
    checksums = {
        "schema": "cm-comparative-p6-checksums/v1",
        "files": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)} for path in artifacts
        ],
    }
    publish_json(output / "checksums.json", checksums)
    print(json.dumps({
        "output": str(output),
        "freeze_sha256": freeze["freeze_sha256"],
        "sources_verified": source_check["verified"],
        "ready_for_paid_measurement": gate["ready_for_paid_measurement"],
        "gate_reasons": gate["reasons"],
    }, indent=2))
    return 0


def verify(args) -> int:
    output = args.output.resolve()
    freeze = strict_load(output / "freeze.json")
    saved_source = strict_load(output / "source-check.json")
    saved_gate = strict_load(output / "gate.json")
    checksums = strict_load(output / "checksums.json")
    validate_freeze(freeze)
    source_check = verify_sources(freeze, args.project_root)
    gate = evaluate_gate(freeze, source_check)
    expected_names = ["freeze.json", "source-check.json", "gate.json"]
    rows = checksums.get("files") if isinstance(checksums, dict) else None
    checksum_ok = (
        checksums.get("schema") == "cm-comparative-p6-checksums/v1"
        and isinstance(rows, list)
        and [row.get("path") for row in rows] == expected_names
        and all(
            set(row) == {"path", "bytes", "sha256"}
            and (output / row["path"]).stat().st_size == row["bytes"]
            and sha256(output / row["path"]) == row["sha256"]
            for row in rows
        )
    )
    result = {
        "schema": "cm-comparative-p6-verification/v1",
        "freeze_sha256": freeze["freeze_sha256"],
        "checksums_verified": checksum_ok,
        "saved_source_check_matches": saved_source == source_check,
        "saved_gate_matches": saved_gate == gate,
        "sources_verified": source_check["verified"],
        "ready_for_paid_measurement": gate["ready_for_paid_measurement"],
        "gate_reasons": gate["reasons"],
    }
    result["package_verified"] = all((
        result["checksums_verified"],
        result["saved_source_check_matches"],
        result["saved_gate_matches"],
        result["sources_verified"],
    ))
    print(json.dumps(result, indent=2))
    if not result["package_verified"]:
        return 1
    if args.require_ready and not result["ready_for_paid_measurement"]:
        return 2
    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    sub = value.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--draft", type=Path, required=True)
    build_parser.add_argument("--project-root", type=Path, required=True)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.set_defaults(func=build)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--project-root", type=Path, required=True)
    verify_parser.add_argument("--output", type=Path, required=True)
    verify_parser.add_argument("--require-ready", action="store_true")
    verify_parser.set_defaults(func=verify)
    return value


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
