"""Build the exact deterministic W8 semantic/root/oracle scout upload bundle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[6]
CONVERSION = HERE / "w8-logikbench-conversion-v4-001/evidence/run-output/w8-conversion"
MANIFEST = HERE / "RUNPOD-W8-LOGIKBENCH-SEMANTIC-UPLOAD-MANIFEST-V1-20260830.json"
BUNDLE = HERE / "RUNPOD-W8-LOGIKBENCH-SEMANTIC-UPLOAD-BUNDLE-V1-20260830.zip"
LOCK_ROOT = ROOT / (
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909"
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if MANIFEST.exists() or BUNDLE.exists():
        raise RuntimeError("W8 semantic upload outputs already exist")
    conversion = json.loads((CONVERSION / "conversions.json").read_text(encoding="utf-8"))
    final_audit = json.loads((HERE / "W8-LOGIKBENCH-CONVERSION-FINAL-AUDIT.json").read_text(encoding="utf-8"))
    final_postflight = json.loads((HERE / "W8-LOGIKBENCH-CONVERSION-FINAL-POSTFLIGHT.json").read_text(encoding="utf-8"))
    if (
        conversion.get("attempted") != 70
        or conversion.get("converted") != 64
        or conversion.get("rejected") != 6
        or conversion.get("performance_measurement") is not False
        or conversion.get("performance_claim_permitted") is not False
        or final_audit.get("verified") is not True
        or final_postflight.get("all_created_pods_absent") is not True
        or final_postflight.get("all_inventories_empty") is not True
    ):
        raise RuntimeError("audited W8 conversion evidence is not ready")

    sources: dict[str, Path] = {
        "W8-LOGIKBENCH-ACQUISITION.json": HERE / "W8-LOGIKBENCH-ACQUISITION.json",
        "W8-LOGIKBENCH-STATIC-ADMISSION.json": HERE / "W8-LOGIKBENCH-STATIC-ADMISSION.json",
        "W8-LOGIKBENCH-CONVERSION-FINAL-AUDIT.json": HERE / "W8-LOGIKBENCH-CONVERSION-FINAL-AUDIT.json",
        "W8-LOGIKBENCH-CONVERSION-FINAL-POSTFLIGHT.json": HERE / "W8-LOGIKBENCH-CONVERSION-FINAL-POSTFLIGHT.json",
        "runpod_w8_logikbench_semantic_worker_v1.py": HERE / "runpod_w8_logikbench_semantic_worker_v1.py",
        "bitset_backend.py": ROOT / "bitset_backend.py",
        "cm_exprlib.py": ROOT / "cm_exprlib.py",
        "cmbench/__init__.py": ROOT / "cmbench/__init__.py",
        "cmbench/recognition/__init__.py": ROOT / "cmbench/recognition/__init__.py",
        "cmbench/recognition/blif.py": ROOT / "cmbench/recognition/blif.py",
        "cmbench/recognition/features.py": ROOT / "cmbench/recognition/features.py",
        "tests/test_blif_recognition.py": ROOT / "tests/test_blif_recognition.py",
        "docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/runpod-requirements.lock": LOCK_ROOT / "runpod-requirements.lock",
        "docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/RUNPOD-WHEEL-LOCK.json": LOCK_ROOT / "RUNPOD-WHEEL-LOCK.json",
    }
    for name in ("conversions.json", "fixture-summary.json", "environment.json", "checksums.json"):
        sources["w8-conversion/" + name] = CONVERSION / name
    converted_rows = [row for row in conversion["rows"] if row.get("status") == "converted"]
    if len(converted_rows) != 64:
        raise RuntimeError("converted row count changed")
    for row in converted_rows:
        target = "w8-conversion/converted/" + row["cluster_id"] + ".blif"
        path = CONVERSION / "converted" / (row["cluster_id"] + ".blif")
        if path.stat().st_size != row["bytes"] or digest(path.read_bytes()) != row["sha256"]:
            raise RuntimeError("converted BLIF identity mismatch: " + row["cluster_id"])
        sources[target] = path

    secret_names = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}
    payloads: dict[str, bytes] = {}
    rows = []
    private_targets = []
    for target, source in sorted(sources.items()):
        target_path = Path(target)
        if any(part.lower() in secret_names for part in target_path.parts):
            raise RuntimeError("secret-like path in W8 semantic bundle")
        if ".git" in target_path.parts or source.suffix.lower() in {".db", ".sqlite", ".key", ".pem"}:
            raise RuntimeError("forbidden path in W8 semantic bundle: " + target)
        if not source.is_file() or source.is_symlink():
            raise RuntimeError("missing or linked W8 semantic source: " + target)
        payload = source.read_bytes()
        payloads[target] = payload
        public_derived = target.startswith("w8-conversion/converted/")
        provenance = "derived-from-public-logikbench" if public_derived else "local-project-or-audit-source"
        if not public_derived:
            private_targets.append(target)
        rows.append({
            "source": source.relative_to(ROOT).as_posix(),
            "target": target,
            "bytes": len(payload),
            "sha256": digest(payload),
            "provenance": provenance,
        })

    manifest = {
        "schema": "cm-runpod-w8-logikbench-semantic-upload-manifest/v1",
        "purpose": "bounded semantic/root/oracle scout; no CM performance measurement",
        "upstream_repository": "https://github.com/zeroasiccorp/logikbench.git",
        "upstream_commit": "891ced851ea4c2f9a46f6ab991eeee199e2fd516",
        "converted_clusters": 64,
        "required_primary_cases": 30,
        "support_bounds": [4, 16],
        "source_node_bound": 4096,
        "file_count": len(rows),
        "bytes": sum(row["bytes"] for row in rows),
        "contains_private_project_source": True,
        "private_project_files": private_targets,
        "contains_credentials": False,
        "contains_env_files": False,
        "contains_git_metadata": False,
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "files": rows,
    }
    with zipfile.ZipFile(BUNDLE, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for target in sorted(payloads):
            info = zipfile.ZipInfo(target, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payloads[target], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
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
