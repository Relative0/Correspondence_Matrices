"""Build the exact deterministic W8 V2 conversion-scout upload bundle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[6]
SOURCE = ROOT / "external/logikbench-confirmation-20260830"
ACQUISITION = HERE / "W8-LOGIKBENCH-ACQUISITION.json"
ADMISSION = HERE / "W8-LOGIKBENCH-STATIC-ADMISSION.json"
WORKER = HERE / "runpod_w8_logikbench_conversion_worker_v2.py"
MANIFEST = HERE / "RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-MANIFEST-V2-20260830.json"
BUNDLE = HERE / "RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-BUNDLE-V2-20260830.zip"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if MANIFEST.exists() or BUNDLE.exists():
        raise RuntimeError("W8 upload outputs already exist")
    acquisition = json.loads(ACQUISITION.read_text(encoding="utf-8"))
    admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
    if (
        acquisition.get("commit") != "891ced851ea4c2f9a46f6ab991eeee199e2fd516"
        or acquisition.get("clean") is not True
        or admission.get("static_admitted_count") != 70
        or admission.get("ready_for_yosys_conversion_scout") is not True
        or admission.get("comparative_timing_inspected") is not False
    ):
        raise RuntimeError("W8 source freeze is not ready")
    acquisition_by_id = {row["cluster_id"]: row for row in acquisition["clusters"]}
    sources: dict[str, Path] = {
        "W8-LOGIKBENCH-ACQUISITION.json": ACQUISITION,
        "W8-LOGIKBENCH-STATIC-ADMISSION.json": ADMISSION,
        WORKER.name: WORKER,
        "source/LICENSE": SOURCE / "LICENSE",
        "source/README.md": SOURCE / "README.md",
    }
    for cluster_id in admission["static_admitted_cluster_ids_in_frozen_order"]:
        cluster = acquisition_by_id[cluster_id]
        directory = SOURCE / "logikbench/benchmarks" / cluster["group"] / cluster["name"]
        for path in directory.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            relative_cluster = path.relative_to(directory)
            if relative_cluster.parts[0] in {"testbench", "__pycache__"}:
                continue
            relative_source = path.relative_to(SOURCE).as_posix()
            target = "source/" + relative_source
            if target in sources and sources[target] != path:
                raise RuntimeError("duplicate target: " + target)
            sources[target] = path

    secret_names = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}
    payloads = {}
    rows = []
    for target, source in sorted(sources.items()):
        if any(part.lower() in secret_names for part in Path(target).parts):
            raise RuntimeError("secret-like path in W8 bundle")
        if ".git" in Path(target).parts or source.suffix.lower() in {".db", ".sqlite", ".key", ".pem"}:
            raise RuntimeError("forbidden path in W8 bundle: " + target)
        payload = source.read_bytes()
        payloads[target] = payload
        rows.append({
            "source": source.relative_to(ROOT).as_posix(),
            "target": target,
            "bytes": len(payload),
            "sha256": digest(payload),
            "provenance": "public-logikbench" if source.is_relative_to(SOURCE) else "local-controller-source",
        })

    manifest = {
        "schema": "cm-runpod-w8-logikbench-conversion-upload-manifest/v2",
        "purpose": "conversion-only W8 corpus scout; no CM performance measurement",
        "upstream_repository": "https://github.com/zeroasiccorp/logikbench.git",
        "upstream_commit": acquisition["commit"],
        "static_candidate_clusters": 70,
        "file_count": len(rows),
        "bytes": sum(row["bytes"] for row in rows),
        "contains_private_project_source": True,
        "private_project_files": [WORKER.name, "W8-LOGIKBENCH-ACQUISITION.json",
                                  "W8-LOGIKBENCH-STATIC-ADMISSION.json"],
        "contains_credentials": False,
        "contains_env_files": False,
        "contains_git_metadata": False,
        "performance_measurement": False,
        "files": rows,
    }
    with zipfile.ZipFile(BUNDLE, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for target in sorted(payloads):
            info = zipfile.ZipInfo(target, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payloads[target], compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
    print(json.dumps({
        "files": manifest["file_count"],
        "source_bytes": manifest["bytes"],
        "bundle_bytes": BUNDLE.stat().st_size,
        "bundle_sha256": digest(BUNDLE.read_bytes()),
        "manifest_sha256": digest(MANIFEST.read_bytes()),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
