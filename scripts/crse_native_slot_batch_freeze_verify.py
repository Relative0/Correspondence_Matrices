"""Independently replay the prospective native-batch freeze and oracles."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cmbench.comparative import gf2_native_slot_batch_workload as workload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = (
    ROOT
    / "docs/recognition/runs/native-slot-batch-prospective-freeze-20260910-001"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    if not artifact.is_relative_to(ROOT.resolve()):
        raise ValueError("artifact must remain inside the project")
    freeze_path = artifact / "FREEZE.json"
    oracles_path = artifact / "ORACLES.json"
    manifest_path = artifact / "MANIFEST.json"
    freeze = _load(freeze_path)
    oracles = _load(oracles_path)
    manifest = _load(manifest_path)
    if (
        manifest.get("schema") != workload.MANIFEST_SCHEMA
        or manifest.get("artifacts", {}).get("FREEZE.json")
        != workload.file_sha256(freeze_path)
        or manifest.get("artifacts", {}).get("ORACLES.json")
        != workload.file_sha256(oracles_path)
        or any(
            manifest.get("artifacts", {}).get(name)
            != workload.file_sha256(artifact / name)
            for name in ("REPORT.md", "BENCHMARK_AUTHORIZATION_REQUEST.json")
        )
    ):
        raise ValueError("artifact manifest mismatch")
    verification = workload.verify_freeze_artifacts(freeze, oracles, ROOT)
    verification.update({
        "freeze_file_sha256": workload.file_sha256(freeze_path),
        "oracles_file_sha256": workload.file_sha256(oracles_path),
        "manifest_file_sha256": workload.file_sha256(manifest_path),
        "authorization_granted": False,
    })
    _write_new(artifact / "INDEPENDENT_VERIFICATION.json", verification)
    print(artifact / "INDEPENDENT_VERIFICATION.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
