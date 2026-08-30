#!/usr/bin/env python3
"""Build or verify an immutable, non-performance P7 execution gate package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.corpus_freeze import validate_freeze
from cmbench.comparative.evidence import publish_json
from cmbench.comparative.p7 import execution_readiness, offline_dry_run


SOURCES = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cm_normalize.py",
    "cmbench/backends/__init__.py",
    "cmbench/backends/bitset_engine.py",
    "cmbench/comparative/arms.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/corpus_freeze.py",
    "cmbench/comparative/evidence.py",
    "cmbench/comparative/ir.py",
    "cmbench/comparative/linux_supervisor.py",
    "cmbench/comparative/p7.py",
    "cmbench/comparative/p7_runner.py",
    "cmbench/comparative/schedule.py",
    "cmbench/recognition/__init__.py",
    "cmbench/recognition/blif.py",
    "cmbench/recognition/features.py",
    "scripts/cm_manifest_dependency_audit.py",
    "scripts/cm_comparative_p7_offline_gate.py",
    "scripts/cm_comparative_p7_runner.py",
    "scripts/cm_comparative_prepare_p6_review.py",
    "tests/test_blif_recognition.py",
    "tests/test_cm_comparative_corpus_freeze.py",
    "tests/test_cm_comparative_p7.py",
    "tests/test_cm_comparative_p7_package.py",
    "tests/test_cm_comparative_p7_runner.py",
    "tests/test_cm_comparative_linux_supervisor.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def strict_load(path: Path):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    def constant(_value):
        raise ValueError("nonfinite JSON")

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=constant)


def source_manifest(project: Path) -> dict:
    rows = []
    for name in SOURCES:
        path = project / name
        if not path.is_file():
            raise FileNotFoundError(path)
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {
        "schema": "cm-comparative-p7-offline-source-manifest/v1",
        "secrets_included": False,
        "files": rows,
    }


def _safe_output(output: Path, project: Path) -> Path:
    output = output.absolute()
    if output.exists() or not output.parent.exists():
        raise ValueError("output must be a new path under an existing project directory")
    if not output.parent.resolve().is_relative_to(project):
        raise ValueError("output escapes project root")
    return output


def _checksums(output: Path, names: list[str]) -> dict:
    return {
        "schema": "cm-comparative-p7-offline-checksums/v1",
        "files": [
            {"path": name, "bytes": (output / name).stat().st_size,
             "sha256": sha256(output / name)}
            for name in names
        ],
    }


def build(args) -> int:
    project = args.project_root.resolve()
    output = _safe_output(args.output, project)
    freeze = strict_load(args.freeze.resolve())
    validate_freeze(freeze)
    readiness = execution_readiness(freeze, project)
    if not readiness["ready_for_offline_dry_run"]:
        raise ValueError("execution readiness failed: " + ",".join(readiness["reasons"]))
    dry_run = offline_dry_run(freeze, project)
    manifest = source_manifest(project)
    publish_json(output / "execution-readiness.json", readiness)
    publish_json(output / "dry-run.json", dry_run)
    publish_json(output / "source-manifest.json", manifest)
    names = ["execution-readiness.json", "dry-run.json", "source-manifest.json"]
    publish_json(output / "checksums.json", _checksums(output, names))
    print(json.dumps({
        "output": str(output),
        "freeze_sha256": freeze["freeze_sha256"],
        "ready": True,
        "dry_run_status": dry_run["status"],
        "performance_measurement": False,
    }, indent=2))
    return 0


def verify(args) -> int:
    project = args.project_root.resolve()
    output = args.output.resolve()
    freeze = strict_load(args.freeze.resolve())
    validate_freeze(freeze)
    saved_readiness = strict_load(output / "execution-readiness.json")
    saved_dry_run = strict_load(output / "dry-run.json")
    saved_manifest = strict_load(output / "source-manifest.json")
    checksums = strict_load(output / "checksums.json")
    expected_names = ["execution-readiness.json", "dry-run.json", "source-manifest.json"]
    rows = checksums.get("files") if isinstance(checksums, dict) else None
    checksum_ok = (
        checksums.get("schema") == "cm-comparative-p7-offline-checksums/v1"
        and isinstance(rows, list)
        and [row.get("path") for row in rows] == expected_names
        and all(
            set(row) == {"path", "bytes", "sha256"}
            and (output / row["path"]).is_file()
            and (output / row["path"]).stat().st_size == row["bytes"]
            and sha256(output / row["path"]) == row["sha256"]
            for row in rows
        )
    )
    readiness = execution_readiness(freeze, project)
    dry_run = offline_dry_run(freeze, project)
    manifest = source_manifest(project)
    result = {
        "schema": "cm-comparative-p7-offline-verification/v1",
        "freeze_sha256": freeze["freeze_sha256"],
        "checksums_verified": checksum_ok,
        "readiness_matches": saved_readiness == readiness,
        "dry_run_matches": saved_dry_run == dry_run,
        "source_manifest_matches": saved_manifest == manifest,
        "ready": readiness["ready_for_offline_dry_run"],
        "dry_run_status": dry_run["status"],
        "performance_measurement": False,
    }
    result["package_verified"] = all((
        result["checksums_verified"], result["readiness_matches"],
        result["dry_run_matches"], result["source_manifest_matches"],
        result["ready"], result["dry_run_status"] == "passed",
    ))
    print(json.dumps(result, indent=2))
    return 0 if result["package_verified"] else 1


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    sub = value.add_subparsers(dest="command", required=True)
    for name, function in (("build", build), ("verify", verify)):
        command = sub.add_parser(name)
        command.add_argument("--project-root", type=Path, required=True)
        command.add_argument("--freeze", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.set_defaults(func=function)
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
