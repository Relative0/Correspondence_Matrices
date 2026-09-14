"""Freeze the focused successor upload shard and its exact file manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
OUT = BASE / "successor-prelaunch-002"
PLAN = OUT / "PLAN.json"
LEDGER = BASE / "prelaunch-008/ADMISSION_LEDGER.json"
POSTFIX_SMOKE = BASE / "postfix-linux-smoke-001/RESULT.json"
CORRECTION = BASE / "admission-d4-correction-001/DIAGNOSTIC.json"
BUNDLE = OUT / "SUCCESSOR_BUNDLE-002.zip"
UPLOAD_MANIFEST = OUT / "UPLOAD_MANIFEST.json"
CAMPAIGN = "cm-mega-successor-20260914-009"


CODE_PATHS = [
    "cmbench/__init__.py",
    "cmbench/backends/__init__.py",
    "cmbench/backends/native_count.py",
    "cmbench/backends/native_sat.py",
    "cmbench/backends/projected_count.py",
    "cmbench/biology_bnet.py",
    "scripts/cm_benchmark_core_screen.py",
    "docker/cm-benchmark-smoke/NATIVE_LOCK.json",
    "docker/cm-benchmark-smoke/smoke_v2.py",
    "docker/cm-benchmark-smoke/fixtures/exact.cnf",
    "docker/cm-benchmark-smoke/fixtures/projected.cnf",
    "docker/cm-benchmark-smoke/fixtures/sat.cnf",
    "docker/cm-benchmark-smoke/fixtures/unsat.cnf",
    "docker/cm-benchmark-smoke/fixtures/xor-sat.cnf",
    "docker/cm-benchmark-smoke/fixtures/xor-unsat.cnf",
    "docker/cm-benchmark-smoke/fixtures/aeon.bnet",
    "docker/cm-benchmark-smoke/vendor/ganak-v2.6.4-linux-amd64.tar.gz",
    "docker/cm-benchmark-smoke/vendor/kissat-4.0.4-linux-amd64.zip",
    "docker/cm-benchmark-smoke/vendor/cryptominisat5-v5.15.0-linux-amd64.tar.gz",
    "docker/cm-benchmark-smoke/vendor/d4v2-15eff31962466804a48374826b9e5a746fc2766e.tar.gz",
    "docker/cm-benchmark-smoke/vendor/libpatoh-linux-x86_64-pr8.a",
    "docker/cm-benchmark-smoke/vendor/biodivine_aeon-1.4.2-cp37-abi3-manylinux_2_28_x86_64.whl",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def archive_info(name: str) -> zipfile.ZipInfo:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError("unsafe successor archive path")
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def main() -> None:
    if BUNDLE.exists() or UPLOAD_MANIFEST.exists():
        raise RuntimeError("successor upload freeze already exists")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    smoke = json.loads(POSTFIX_SMOKE.read_text(encoding="utf-8"))
    if (
        plan.get("campaign_id") != CAMPAIGN
        or len(plan.get("cases", [])) != 18
        or len(plan.get("cells", [])) != 108
        or smoke.get("status") != "passed"
        or smoke["d4_selected_exact_replay"]["status_counts"]["error"] != 0
    ):
        raise RuntimeError("successor plan or post-fix smoke is not ready")

    rows_by_hash = {}
    for row in ledger["rows"]:
        rows_by_hash.setdefault(row.get("sha256"), row)
    files: dict[str, tuple[bytes, str | None]] = {}
    for relative in CODE_PATHS:
        path = ROOT / relative
        files["source/" + relative.replace("\\", "/")] = (
            path.read_bytes(),
            relative,
        )

    selected_rows = []
    for case in plan["cases"]:
        row = rows_by_hash.get(case["input_sha256"])
        if row is None:
            raise RuntimeError("planned input absent from frozen admission ledger")
        path = ROOT / row["path"]
        if digest(path) != case["input_sha256"]:
            raise RuntimeError("planned input identity changed")
        archive_name = case["path"]
        files[archive_name] = (path.read_bytes(), row["path"])
        selected_rows.append(row)

    for license_path in sorted(
        {row["license_path"] for row in selected_rows if row.get("license_path")}
    ):
        path = ROOT / license_path
        files["licenses/" + license_path.replace("\\", "/")] = (
            path.read_bytes(),
            license_path,
        )

    generated = {
        "manifests/PLAN.json": PLAN.read_bytes(),
        "manifests/POSTFIX_LINUX_SMOKE.json": POSTFIX_SMOKE.read_bytes(),
        "manifests/ADMISSION_D4_CORRECTION.json": CORRECTION.read_bytes(),
        "BUNDLE_README.md": (
            "# CM focused successor bundle\n\n"
            "This frozen shard is not authorized for upload or paid execution. "
            "It contains only the 18 inputs and pinned native/runtime files required "
            "by the 108-cell exact-count and closed-biology successor plan.\n"
        ).encode("utf-8"),
    }
    for name, data in generated.items():
        files[name] = (data, None)

    contents = [
        {
            "archive": name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "source": source,
        }
        for name, (data, source) in sorted(files.items())
    ]
    contents_record = {
        "schema": "cm-benchmark-successor-bundle-contents/v1",
        "campaign_id": CAMPAIGN,
        "created_utc": plan["created_utc"],
        "entries": contents,
        "entries_sha256": hashlib.sha256(canonical(contents)).hexdigest(),
    }
    files["BUNDLE_CONTENTS.json"] = (
        json.dumps(contents_record, indent=2, sort_keys=True).encode("utf-8") + b"\n",
        None,
    )

    with zipfile.ZipFile(BUNDLE, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, (data, _) in sorted(files.items()):
            archive.writestr(archive_info(name), data)

    with zipfile.ZipFile(BUNDLE) as archive:
        names = archive.namelist()
        if names != sorted(names) or len(names) != len(set(names)):
            raise RuntimeError("successor bundle member ordering or uniqueness failure")
        expanded = sum(info.file_size for info in archive.infolist())
        for info in archive.infolist():
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts or info.is_dir():
                raise RuntimeError("unsafe successor bundle member")
    if BUNDLE.stat().st_size > 64 << 20 or expanded > 128 << 20:
        raise RuntimeError("successor bundle exceeds transport bounds")

    controls = [
        {
            "id": "runner",
            "path": "scripts/cm_benchmark_core_screen_v2.py",
            "bytes": (ROOT / "scripts/cm_benchmark_core_screen_v2.py").stat().st_size,
            "sha256": digest(ROOT / "scripts/cm_benchmark_core_screen_v2.py"),
        },
        {
            "id": "plan",
            "path": "PLAN.json",
            "bytes": PLAN.stat().st_size,
            "sha256": digest(PLAN),
        },
    ]
    manifest = {
        "schema": "cm-benchmark-successor-upload-manifest/v1",
        "campaign_id": CAMPAIGN,
        "created_utc": plan["created_utc"],
        "authorization_granted": False,
        "bundles": [
            {
                "path": BUNDLE.name,
                "bytes": BUNDLE.stat().st_size,
                "expanded_bytes": expanded,
                "expanded_limit": 128 << 20,
                "files": len(files),
                "sha256": digest(BUNDLE),
            }
        ],
        "controls": controls,
        "contents": contents,
        "scope": {
            "inputs": len(plan["cases"]),
            "cells": len(plan["cells"]),
            "lanes": ["biology_fixed_points", "exact_count"],
            "other_uploads_permitted": False,
        },
    }
    UPLOAD_MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "frozen",
                "bundle_bytes": BUNDLE.stat().st_size,
                "bundle_sha256": digest(BUNDLE),
                "expanded_bytes": expanded,
                "files": len(files),
                "upload_manifest_sha256": digest(UPLOAD_MANIFEST),
                "controls": controls,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
