"""Offline verification for the exact W8 LogikBench conversion V2 upload."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[6]
MANIFEST = HERE / "RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-MANIFEST-V2-20260830.json"
BUNDLE = HERE / "RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-BUNDLE-V2-20260830.zip"
EXPECTED_MANIFEST_SHA256 = "5365b4362fc42790bf7107c6b8da29ec61b79faf8d69ac40bcfeb77a87640354"
EXPECTED_BUNDLE_SHA256 = "1b3796d6ded0f6d1b0d6266c5e783f1b0687aae9c7ecfdac901ad625c6e6ff95"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify() -> dict:
    manifest_bytes = MANIFEST.read_bytes()
    bundle_bytes = BUNDLE.read_bytes()
    manifest = json.loads(manifest_bytes)
    if (
        digest(manifest_bytes) != EXPECTED_MANIFEST_SHA256
        or digest(bundle_bytes) != EXPECTED_BUNDLE_SHA256
        or manifest.get("schema") != "cm-runpod-w8-logikbench-conversion-upload-manifest/v2"
        or manifest.get("upstream_commit") != "891ced851ea4c2f9a46f6ab991eeee199e2fd516"
        or manifest.get("static_candidate_clusters") != 70
        or manifest.get("file_count") != 159
        or manifest.get("bytes") != 617274
        or manifest.get("performance_measurement") is not False
        or manifest.get("contains_credentials") is not False
        or manifest.get("contains_env_files") is not False
        or manifest.get("contains_git_metadata") is not False
        or manifest.get("private_project_files") != [
            "runpod_w8_logikbench_conversion_worker_v2.py",
            "W8-LOGIKBENCH-ACQUISITION.json",
            "W8-LOGIKBENCH-STATIC-ADMISSION.json",
        ]
    ):
        raise RuntimeError("W8 V2 manifest freeze mismatch")
    rows = manifest["files"]
    by_target = {row["target"]: row for row in rows}
    if len(rows) != len(by_target) or sum(row["bytes"] for row in rows) != manifest["bytes"]:
        raise RuntimeError("W8 V2 manifest row mismatch")
    forbidden_names = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}
    for target, row in by_target.items():
        pure = PurePosixPath(target)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or ".git" in pure.parts
            or any(part.lower() in forbidden_names for part in pure.parts)
            or pure.suffix.lower() in {".db", ".sqlite", ".key", ".pem"}
        ):
            raise RuntimeError("unsafe W8 V2 target: " + target)
        source = ROOT / PurePosixPath(row["source"])
        data = source.read_bytes()
        if len(data) != row["bytes"] or digest(data) != row["sha256"]:
            raise RuntimeError("W8 V2 local source changed: " + row["source"])
    with zipfile.ZipFile(BUNDLE) as archive:
        names = archive.namelist()
        if set(names) != set(by_target) or len(names) != len(set(names)):
            raise RuntimeError("W8 V2 bundle members differ from manifest")
        for name in names:
            data = archive.read(name)
            row = by_target[name]
            if len(data) != row["bytes"] or digest(data) != row["sha256"]:
                raise RuntimeError("W8 V2 bundle member mismatch: " + name)
    return {
        "verified": True,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "bundle_sha256": EXPECTED_BUNDLE_SHA256,
        "bundle_bytes": len(bundle_bytes),
        "source_files": len(rows),
        "source_bytes": manifest["bytes"],
        "static_candidate_clusters": 70,
        "contains_credentials": False,
        "performance_measurement": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
