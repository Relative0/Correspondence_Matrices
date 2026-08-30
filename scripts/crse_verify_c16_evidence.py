"""Verify the immutable C16 local run manifest and source fingerprints."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/recognition/runs/c16-gf2-screened-tail-windows-20260830-001"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    sources = json.loads((RUN / "source_fingerprints.json").read_text(encoding="utf-8"))
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    changed = [path for path, expected in sources["files"].items()
               if not (ROOT / path).is_file() or sha(ROOT / path) != expected]
    invalid = [row["path"] for row in manifest["files"]
               if not (RUN / row["path"]).is_file()
               or (RUN / row["path"]).stat().st_size != row["bytes"]
               or sha(RUN / row["path"]) != row["sha256"]]
    if changed or invalid:
        raise SystemExit(json.dumps({"changed_sources": changed, "invalid_evidence": invalid},
                                    sort_keys=True))
    print(json.dumps({"status": "verified", "source_files": len(sources["files"]),
                      "evidence_files": len(manifest["files"])}, sort_keys=True))


if __name__ == "__main__":
    main()
