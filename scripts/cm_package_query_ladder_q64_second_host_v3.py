"""Create the minimally corrected q64 second-host V3 source bundle."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004"
SOURCE = RUN / "SECOND_HOST_SOURCE_BUNDLE_V2.zip"
OUTPUT = RUN / "SECOND_HOST_SOURCE_BUNDLE_V3.zip"
MANIFEST = RUN / "SECOND_HOST_SOURCE_BUNDLE_V3_MANIFEST.json"
SOURCE_SHA256 = "6baf8e95062b9b80f2dee4a5c98e16983ea0dfb2c111e681cc672e774a45671d"
ADDITIONS = (
    "scripts/cm_measurement_verify.py",
    "scripts/cm_native_contracts.py",
    "scripts/cm_session_contracts.py",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    if SOURCE.stat().st_size != 1_755_915 or sha256_file(SOURCE) != SOURCE_SHA256:
        raise ValueError("V2 source bundle identity mismatch")
    if OUTPUT.exists() or MANIFEST.exists():
        raise ValueError("refusing to overwrite V3 package artifacts")
    additions = []
    with zipfile.ZipFile(SOURCE) as source:
        source_infos = source.infolist()
        source_names = [info.filename for info in source_infos]
        if len(source_names) != len(set(source_names)) or any(
            PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
            for name in source_names
        ):
            raise ValueError("unsafe or duplicate V2 member")
        if any(name in source_names for name in ADDITIONS):
            raise ValueError("V2 unexpectedly already contains a V3 addition")
        with zipfile.ZipFile(OUTPUT, "x", zipfile.ZIP_DEFLATED) as target:
            for info in source_infos:
                if info.is_dir():
                    raise ValueError("V2 directory member is outside the frozen packaging form")
                target.writestr(info.filename, source.read(info))
            for relative in ADDITIONS:
                path = ROOT / relative
                data = path.read_bytes()
                target.writestr(relative, data)
                additions.append({
                    "path": relative,
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                    "unchanged_from_child_source_checkpoint": True,
                })
    with zipfile.ZipFile(OUTPUT) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(source_names) | set(ADDITIONS):
            raise ValueError("V3 member-set validation failed")
        for row in additions:
            data = archive.read(row["path"])
            if len(data) != row["bytes"] or sha256_bytes(data) != row["sha256"]:
                raise ValueError("V3 addition identity validation failed")
    document = {
        "schema": "crse-query-ladder-q64-second-host-source-bundle-v3/v1",
        "status": "sealed_not_authorized_for_upload",
        "reason": "V2 omitted three unchanged transitive import dependencies; no timing began",
        "source_checkpoint": "c4cfccd846771a4f72a1b429797b97cdb1ed3d83",
        "superseded_v2": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "bytes": SOURCE.stat().st_size,
            "sha256": SOURCE_SHA256,
        },
        "additions": additions,
        "file_count": len(names),
        "bytes": OUTPUT.stat().st_size,
        "sha256": sha256_file(OUTPUT),
        "path": OUTPUT.relative_to(ROOT).as_posix(),
        "timing_results_opened": False,
        "decision_cells_executed": 0,
        "credentials_included": False,
    }
    with MANIFEST.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(document, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(document, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
