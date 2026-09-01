"""Stage the unchanged frozen C27 package for a local Linux Docker replication."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_linux_confirmation"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
OUTPUT = HERE / "c27-docker-linux-portability-001"
FROZEN = OUTPUT / "frozen"
RESULTS = OUTPUT / "results"
RUNTIME = OUTPUT / "runtime"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 Docker portability staging")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (
        manifest.get("file_count") != 63
        or manifest.get("bytes") != 1078671
        or manifest.get("runtime", {}).get("python") != "3.13.15"
        or manifest.get("runtime", {}).get("numpy") != "2.3.2"
    ):
        raise ValueError("C27 Docker manifest contract mismatch")
    FROZEN.mkdir(parents=True)
    RESULTS.mkdir()
    RUNTIME.mkdir()
    copied = []
    for row in manifest["files"]:
        source = ROOT / row["source"]
        target = FROZEN / row["target"]
        if source.stat().st_size != row["bytes"] or sha256(source) != row["sha256"]:
            raise ValueError(f"C27 frozen source changed: {row['source']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if target.stat().st_size != row["bytes"] or sha256(target) != row["sha256"]:
            raise ValueError(f"C27 staged source mismatch: {row['target']}")
        copied.append(row["target"])
    observed = sorted(
        str(path.relative_to(FROZEN)).replace("\\", "/")
        for path in FROZEN.rglob("*") if path.is_file())
    if observed != sorted(copied):
        raise ValueError("C27 Docker staging contains an unlisted file")
    base = manifest["runtime"]["image"]
    numpy_requirement = manifest["runtime"]["numpy_requirement"]
    dockerfile = (
        f"FROM {base}\n"
        "RUN printf '%s\\n' '" + numpy_requirement + "' > /tmp/requirements.txt \\\n"
        " && python -m pip install --disable-pip-version-check --no-cache-dir "
        "--require-hashes -r /tmp/requirements.txt \\\n"
        " && rm /tmp/requirements.txt\n"
    )
    (RUNTIME / "Dockerfile").write_text(dockerfile, encoding="utf-8", newline="\n")
    record = {
        "schema": "crse-c27-docker-linux-portability-staging/v1",
        "status": "staged",
        "scientific_scope": "same-host Linux OS/container portability; not second-machine",
        "manifest_sha256": sha256(MANIFEST),
        "source_files": len(copied),
        "source_bytes": sum((FROZEN / target).stat().st_size for target in copied),
        "staged_targets": observed,
        "base_image": base,
        "numpy_requirement": numpy_requirement,
        "network_during_workload": False,
        "container_root_read_only": True,
        "vcpu_limit": 2,
        "memory_limit_gb": 4,
        "result_cap_bytes": manifest["result_cap_bytes"],
        "commands": manifest["commands"],
        "credentials_included": False,
        "production_write": False,
    }
    (OUTPUT / "STAGING.json").write_bytes(json.dumps(
        record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "status": "staged", "source_files": len(copied),
        "source_bytes": record["source_bytes"],
        "manifest_sha256": record["manifest_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
