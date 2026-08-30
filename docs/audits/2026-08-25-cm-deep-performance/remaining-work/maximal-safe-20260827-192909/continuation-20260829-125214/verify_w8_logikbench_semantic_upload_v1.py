"""Verify the exact frozen W8 semantic/root/oracle upload package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[6]
MANIFEST = HERE / "RUNPOD-W8-LOGIKBENCH-SEMANTIC-UPLOAD-MANIFEST-V1-20260830.json"
BUNDLE = HERE / "RUNPOD-W8-LOGIKBENCH-SEMANTIC-UPLOAD-BUNDLE-V1-20260830.zip"
EXPECTED_MANIFEST_SHA256 = "42411d3b0e22b048f143cdece99848b104d2cc9278ab7cbef050c1db9ecba5d1"
EXPECTED_BUNDLE_SHA256 = "142f6d5e6ad4fe68ef3f64e6a74a0236fa786ae9e990c27ea1ed8c533faa24aa"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify() -> dict:
    if digest(MANIFEST.read_bytes()) != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("W8 semantic manifest hash mismatch")
    if digest(BUNDLE.read_bytes()) != EXPECTED_BUNDLE_SHA256:
        raise RuntimeError("W8 semantic bundle hash mismatch")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (
        manifest.get("schema") != "cm-runpod-w8-logikbench-semantic-upload-manifest/v1"
        or manifest.get("file_count") != 82
        or manifest.get("bytes") != 15054954
        or manifest.get("converted_clusters") != 64
        or manifest.get("required_primary_cases") != 30
        or manifest.get("support_bounds") != [4, 16]
        or manifest.get("source_node_bound") != 4096
        or manifest.get("contains_credentials") is not False
        or manifest.get("contains_env_files") is not False
        or manifest.get("contains_git_metadata") is not False
        or manifest.get("performance_measurement") is not False
        or manifest.get("performance_claim_permitted") is not False
    ):
        raise RuntimeError("W8 semantic manifest contract mismatch")
    rows = manifest["files"]
    expected = {row["target"]: row for row in rows}
    if len(expected) != 82:
        raise RuntimeError("duplicate W8 semantic manifest target")
    converted = [target for target in expected if target.startswith("w8-conversion/converted/")]
    if len(converted) != 64:
        raise RuntimeError("converted BLIF upload coverage mismatch")
    secret_names = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}
    for target, row in expected.items():
        pure = PurePosixPath(target)
        if pure.is_absolute() or ".." in pure.parts or ".git" in pure.parts:
            raise RuntimeError("unsafe upload target")
        if any(part.lower() in secret_names for part in pure.parts):
            raise RuntimeError("secret-like upload target")
        source = ROOT / PurePosixPath(row["source"])
        data = source.read_bytes()
        if len(data) != row["bytes"] or digest(data) != row["sha256"]:
            raise RuntimeError("source changed: " + target)
    with zipfile.ZipFile(BUNDLE) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise RuntimeError("W8 semantic archive member mismatch")
        for name in names:
            data = archive.read(name)
            row = expected[name]
            if len(data) != row["bytes"] or digest(data) != row["sha256"]:
                raise RuntimeError("W8 semantic archive payload mismatch: " + name)
    return {
        "verified": True,
        "files": 82,
        "converted_blifs": 64,
        "source_bytes": manifest["bytes"],
        "bundle_bytes": BUNDLE.stat().st_size,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "bundle_sha256": EXPECTED_BUNDLE_SHA256,
        "worker_sha256": digest((HERE / "runpod_w8_logikbench_semantic_worker_v1.py").read_bytes()),
        "remote_program_sha256": digest((HERE / "runpod_w8_logikbench_semantic_remote_v1.py").read_bytes()),
        "performance_measurement": False,
        "performance_claim_permitted": False,
    }
def main() -> int:
    print(json.dumps(verify(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
