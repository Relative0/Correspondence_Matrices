"""Build the dependency-closed, deterministic P7 functional-scout bundle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
OLD_MANIFEST = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V1-20260830.json"
OLD_BUNDLE = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V1-20260830.zip"
NEW_MANIFEST = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V5-20260830.json"
NEW_BUNDLE = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V5-20260830.zip"
FREEZE = ROOT / "docs" / "research" / "verification" / "comparative-p6-candidate-v4-2026-08-30" / "freeze.json"
FEATURES = ROOT / "cmbench" / "recognition" / "features.py"
FEATURES_TARGET = "cmbench/recognition/features.py"
CORPUS = ROOT / "deliverables_n22_24" / "CM_gap_e3_corrected_corpus_2026_08_02.jsonl"
CORPUS_TARGET = "deliverables_n22_24/CM_gap_e3_corrected_corpus_2026_08_02.jsonl"
BACKENDS_INIT = ROOT / "cmbench" / "backends" / "__init__.py"
BACKENDS_INIT_TARGET = "cmbench/backends/__init__.py"
BITSET_ENGINE = ROOT / "cmbench" / "backends" / "bitset_engine.py"
BITSET_ENGINE_TARGET = "cmbench/backends/bitset_engine.py"


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
    if any(row["target"] == CORPUS_TARGET for row in rows):
        raise RuntimeError("development corpus unexpectedly present in V1 manifest")
    if any(row["target"] in {BACKENDS_INIT_TARGET, BITSET_ENGINE_TARGET} for row in rows):
        raise RuntimeError("bitset-engine package unexpectedly present in V1 manifest")
    features = FEATURES.read_bytes()
    if len(features) != 4_789 or digest(features) != "02b183d09e1cf673b63dbb0f2d942a9695acb1979045eeba804d18a6cb3a0bb6":
        raise RuntimeError("features.py identity changed")
    corpus = CORPUS.read_bytes()
    if len(corpus) != 357_984 or digest(corpus) != "8a6da87cc8b13f6123cb11adfa77b5d69bcd0a086666abea7df633ef92f6e68a":
        raise RuntimeError("development corpus identity changed")
    backends_init = BACKENDS_INIT.read_bytes()
    bitset_engine = BITSET_ENGINE.read_bytes()
    if backends_init or digest(backends_init) != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
        raise RuntimeError("cmbench.backends package identity changed")
    if len(bitset_engine) != 3_627 or digest(bitset_engine) != "91cfa4ec491d5153b1332a6738ef34c1e17335ee48df168bdc06ad92faa2db62":
        raise RuntimeError("bitset_engine.py identity changed")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    epfl_sources = {
        case["source"]["path"]: case["source"]
        for case in freeze["cases"]
        if case["case_id"].startswith("development-epfl-")
    }
    if len(epfl_sources) != 10:
        raise RuntimeError("unexpected frozen EPFL source set")
    if any(row["target"] in epfl_sources for row in rows):
        raise RuntimeError("EPFL readiness source unexpectedly present in V1 manifest")
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
    payloads[CORPUS_TARGET] = corpus
    payloads[BACKENDS_INIT_TARGET] = backends_init
    payloads[BITSET_ENGINE_TARGET] = bitset_engine
    for target, frozen in sorted(epfl_sources.items()):
        payload = (ROOT / target).read_bytes()
        if len(payload) != frozen["bytes"] or digest(payload) != frozen["sha256"]:
            raise RuntimeError(f"frozen EPFL source identity changed: {target}")
        payloads[target] = payload
    rows.append(
        {
            "source": FEATURES_TARGET,
            "target": FEATURES_TARGET,
            "bytes": len(features),
            "sha256": digest(features),
        }
    )
    rows.append(
        {
            "source": CORPUS_TARGET,
            "target": CORPUS_TARGET,
            "bytes": len(corpus),
            "sha256": digest(corpus),
        }
    )
    rows.extend(
        [
            {
                "source": BACKENDS_INIT_TARGET,
                "target": BACKENDS_INIT_TARGET,
                "bytes": len(backends_init),
                "sha256": digest(backends_init),
            },
            {
                "source": BITSET_ENGINE_TARGET,
                "target": BITSET_ENGINE_TARGET,
                "bytes": len(bitset_engine),
                "sha256": digest(bitset_engine),
            },
        ]
    )
    for target, frozen in sorted(epfl_sources.items()):
        rows.append(
            {
                "source": target,
                "target": target,
                "bytes": frozen["bytes"],
                "sha256": frozen["sha256"],
            }
        )
    manifest["file_count"] = len(rows)
    manifest["bytes"] = sum(row["bytes"] for row in rows)
    manifest["correction"] = (
        "Adds cmbench/recognition/features.py, the omitted direct import required "
        "by cmbench/recognition/blif.py, and the frozen development-case JSONL "
        "referenced by the P7 plan, plus the cmbench.backends package and "
        "bitset-engine selector imported during complete-relation execution, "
        "and all ten frozen EPFL development sources required by the full "
        "offline-gate readiness verification. "
        "All 152 V1 payloads remain byte-identical."
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
