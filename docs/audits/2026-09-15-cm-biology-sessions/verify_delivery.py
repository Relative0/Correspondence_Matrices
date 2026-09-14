"""Read-only verification of delivered artifacts and both source identities."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]


def verify_files(base: Path, files: dict[str, str]) -> None:
    for name, expected in files.items():
        path = (base / name).resolve()
        if not path.is_relative_to(base.resolve()):
            raise ValueError(f"Manifest path escapes base: {name}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Hash mismatch: {path}")


def main() -> None:
    delivery = json.loads((AUDIT / "AUDIT_MANIFEST.json").read_text())
    verify_files(AUDIT, delivery["files"])
    current = json.loads((AUDIT / "SOURCE_MANIFEST.json").read_text())["files"]
    verify_files(ROOT, current)
    pilot = AUDIT / "pilot-002"
    executed = json.loads((pilot / "SOURCE_MANIFEST.json").read_text())["files"]
    verify_files(pilot / "source", executed)
    print(json.dumps({
        "status": "passed",
        "delivery_artifacts": len(delivery["files"]),
        "current_sources": len(current),
        "executed_source_snapshots": len(executed),
    }))


if __name__ == "__main__":
    main()
