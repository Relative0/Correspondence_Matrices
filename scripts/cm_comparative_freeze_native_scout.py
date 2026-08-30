"""Freeze the exact source set for the comparative Linux/native scout."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
MAX_SOURCE_BYTES = 8 << 20
FILES = (
    ("bitset_backend.py", "bitset_backend.py"),
    ("cm_expr_serde.py", "cm_expr_serde.py"),
    ("cm_exprlib.py", "cm_exprlib.py"),
    ("cm_ir.py", "cm_ir.py"),
    ("cm_normalize.py", "cm_normalize.py"),
    ("cmbench/__init__.py", "cmbench/__init__.py"),
    ("cmbench/output_budget.py", "cmbench/output_budget.py"),
    ("cmbench/comparative/__init__.py", "cmbench/comparative/__init__.py"),
    ("cmbench/comparative/arms.py", "cmbench/comparative/arms.py"),
    ("cmbench/comparative/contracts.py", "cmbench/comparative/contracts.py"),
    ("cmbench/comparative/evidence.py", "cmbench/comparative/evidence.py"),
    ("cmbench/comparative/ir.py", "cmbench/comparative/ir.py"),
    ("cmbench/comparative/linux_supervisor.py", "cmbench/comparative/linux_supervisor.py"),
    ("cmbench/comparative/readiness.py", "cmbench/comparative/readiness.py"),
    ("cmbench/comparative/schedule.py", "cmbench/comparative/schedule.py"),
    ("scripts/cm_comparative_smoke.py", "scripts/cm_comparative_smoke.py"),
    ("scripts/cm_comparative_native_scout.py", "scripts/cm_comparative_native_scout.py"),
    ("scripts/cm_measurement_verify.py", "scripts/cm_measurement_verify.py"),
    ("scripts/cm_native_contracts.py", "scripts/cm_native_contracts.py"),
    ("tests/test_cm_comparative_foundation.py", "tests/test_cm_comparative_foundation.py"),
    ("tests/test_cm_comparative_readiness.py", "tests/test_cm_comparative_readiness.py"),
    ("tests/test_cm_comparative_linux_supervisor.py", "tests/test_cm_comparative_linux_supervisor.py"),
    ("tests/test_cm_comparative_native_scout.py", "tests/test_cm_comparative_native_scout.py"),
    ("tests/test_cm_no_reinflate.py", "tests/test_cm_no_reinflate.py"),
    ("tests/test_program_metrics.py", "tests/test_program_metrics.py"),
    ("tests/test_cm_native_contracts.py", "tests/test_cm_native_contracts.py"),
    (
        "deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/"
        "independence_audit_2026_08_27/artifact_audit.py",
        "deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/"
        "independence_audit_2026_08_27/artifact_audit.py",
    ),
    (
        "external/d4v2/scripts/d4ScriptsCompetition/bin/d4",
        "external/d4v2/scripts/d4ScriptsCompetition/bin/d4",
    ),
    (
        "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
        "maximal-safe-20260827-192909/runpod-requirements.lock",
        "runpod-requirements.lock",
    ),
    (
        "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
        "maximal-safe-20260827-192909/continuation-20260829-125214/"
        "RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json",
        "study/RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json",
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest() -> dict[str, object]:
    rows = []
    targets: set[str] = set()
    for source_name, target_name in FILES:
        source = ROOT / source_name
        target = PurePosixPath(target_name)
        if (
            not source.is_file()
            or source.is_symlink()
            or any(parent.is_symlink() or parent.is_junction() for parent in source.parents if parent != ROOT.parent)
            or target.is_absolute()
            or ".." in target.parts
            or target.as_posix() in targets
        ):
            raise RuntimeError("missing, linked, unsafe, or duplicate scout source")
        targets.add(target.as_posix())
        rows.append({
            "source": source_name,
            "target": target.as_posix(),
            "bytes": source.stat().st_size,
            "sha256": sha256_file(source),
        })
    total = sum(row["bytes"] for row in rows)
    if total > MAX_SOURCE_BYTES:
        raise RuntimeError("native scout upload source bound exceeded")
    return {
        "schema": "cm-runpod-upload-manifest/v2",
        "package_id": "CM-COMPARATIVE-NATIVE-SCOUT-20260829",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authorization_status": "pending",
        "target": "one proposed zero-volume Runpod CPU Linux/native readiness scout; no performance ranking",
        "files": rows,
        "bytes": total,
        "excluded": [
            ".env*", ".git/", ".claude/", "credential and token stores", "unrelated dirty work",
            "benchmark corpora", "prior Runpod evidence", "dependency downloads and build products",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir() or not output.parent.resolve().is_relative_to(ROOT):
        raise ValueError("new project-local manifest path required")
    payload = json.dumps(build_manifest(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
