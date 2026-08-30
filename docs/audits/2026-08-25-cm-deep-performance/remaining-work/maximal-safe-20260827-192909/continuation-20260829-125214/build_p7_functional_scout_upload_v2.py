"""Build the corrected, deterministic P7 functional-scout source bundle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
OLD_MANIFEST = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V1-20260830.json"
OLD_BUNDLE = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V1-20260830.zip"
NEW_MANIFEST = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json"
NEW_BUNDLE = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V2-20260830.zip"
FEATURES = ROOT / "cmbench" / "recognition" / "features.py"
FEATURES_TARGET = "cmbench/recognition/features.py"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    if NEW_MANIFEST.exists() or NEW_BUNDLE.exists():
        raise RuntimeError("corrected outputs already exist")
    manifest = json.loads(OLD_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("file_count") != 152 or manifest.get("bytes") != 11_224_621:
        raise RuntimeError("unexpected V1 manifest identity")
    rows = list(manifest["files"])
    if any(row["target"] == FEATURES_TARGET for row in rows):
        raise RuntimeError("features.py unexpectedly present in V1 manifest")
    features = FEATURES.read_bytes()
    if len(features) != 4_789 or digest(features) != "02b183d09e1cf673b63dbb0f2d942a9695acb1979045eeba804d18a6cb3a0bb6":
        raise RuntimeError("features.py identity changed")
    with zipfile.ZipFile(OLD_BUNDLE, "r") as old:
        old_names = old.namelist()
        expected = {row["target"]: row for row in rows}
        if len(old_names) != len(set(old_names)) or set(old_names) != set(expected):
            raise RuntimeError("V1 ZIP membership mismatch")
        payloads = {}
        for name in old_names:
            payload = old.read(name)
            row = expected[name]
            if len(payload) != row["bytes"] or digest(payload) != row["sha256"]:
                raise RuntimeError(f"V1 ZIP member mismatch: {name}")
            payloads[name] = payload
    payloads[FEATURES_TARGET] = features
    rows.append(
        {
            "source": FEATURES_TARGET,
            "target": FEATURES_TARGET,
            "bytes": len(features),
            "sha256": digest(features),
        }
    )
    manifest["file_count"] = len(rows)
    manifest["bytes"] = sum(row["bytes"] for row in rows)
    manifest["correction"] = (
        "Adds cmbench/recognition/features.py, the omitted direct import required "
        "by cmbench/recognition/blif.py. All 152 V1 payloads remain byte-identical."
    )
    manifest["files"] = rows
    with zipfile.ZipFile(NEW_BUNDLE, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as new:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            new.writestr(info, payloads[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    NEW_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "files": manifest["file_count"],
                "source_bytes": manifest["bytes"],
                "bundle_bytes": NEW_BUNDLE.stat().st_size,
                "bundle_sha256": digest(NEW_BUNDLE.read_bytes()),
                "manifest_sha256": digest(NEW_MANIFEST.read_bytes()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
