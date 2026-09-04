"""Independently verify a source-blind q64 learning-evidence freeze."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition import query_ladder_learning_freeze as protocol
from scripts.cm_query_ladder_learning_freeze import write_new


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    if not artifact.is_relative_to(ROOT) or not artifact.is_dir():
        raise ValueError("artifact must be an in-project directory")

    manifest_path = artifact / "MANIFEST.json"
    freeze_path = artifact / "FREEZE.json"
    report_path = artifact / "REPORT.md"
    manifest = read_json(manifest_path)
    freeze = read_json(freeze_path)
    expected_manifest_fields = {
        "schema",
        "status",
        "source_checkpoint",
        "source_closure_sha256",
        "artifacts",
        "exact_backend_executions",
        "timing_rows_produced",
        "labels_produced",
        "models_trained",
        "prospective_cases_consumed",
    }
    if (
        set(manifest) != expected_manifest_fields
        or manifest.get("schema") != protocol.MANIFEST_SCHEMA
        or manifest.get("status") != "source_blind_freeze_no_labels"
        or set(manifest.get("artifacts", {})) != {"FREEZE.json", "REPORT.md"}
    ):
        raise ValueError("artifact manifest shape")
    for name, expected in manifest["artifacts"].items():
        path = artifact / name
        if not path.is_file() or protocol.file_sha256(path) != expected:
            raise ValueError(f"artifact hash mismatch: {name}")
    if (
        manifest["source_checkpoint"] != freeze.get("source_checkpoint")
        or manifest["source_closure_sha256"] != freeze.get("source_closure_sha256")
        or any(
            manifest[name] != 0
            for name in (
                "exact_backend_executions",
                "timing_rows_produced",
                "labels_produced",
                "models_trained",
                "prospective_cases_consumed",
            )
        )
    ):
        raise ValueError("artifact boundary mismatch")
    verification = protocol.verify_freeze(freeze, ROOT)
    if report_path.read_text(encoding="utf-8") != protocol.render_report(freeze):
        raise ValueError("report replay mismatch")
    verification.update({
        "manifest_sha256": protocol.file_sha256(manifest_path),
        "freeze_file_sha256": protocol.file_sha256(freeze_path),
        "report_sha256": protocol.file_sha256(report_path),
    })
    write_new(artifact / "INDEPENDENT_VERIFICATION.json", verification)
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
