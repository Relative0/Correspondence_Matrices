"""Create the prospective native scalar-versus-batch timing freeze."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from cmbench.comparative import gf2_native_slot_batch_workload as workload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT
    / "docs/recognition/runs/native-slot-batch-prospective-freeze-20260910-001"
)


def _write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        if isinstance(value, str):
            stream.write(value)
            if not value.endswith("\n"):
                stream.write("\n")
        else:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT.resolve()):
        raise ValueError("freeze output must remain inside the project")
    output.mkdir(parents=True, exist_ok=False)
    checkpoint = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    freeze = workload.build_freeze(
        project_root=ROOT,
        source_checkpoint=checkpoint,
    )
    freeze_path = output / "FREEZE.json"
    _write_new(freeze_path, freeze)
    oracles = workload.build_oracles(freeze)
    workload.validate_oracles(oracles, freeze, replay=False)
    oracles_path = output / "ORACLES.json"
    _write_new(oracles_path, oracles)
    _write_new(output / "REPORT.md", workload.render_report(freeze))
    request = workload.authorization_request(freeze_path, oracles_path)
    _write_new(output / "BENCHMARK_AUTHORIZATION_REQUEST.json", request)
    artifacts = {
        name: workload.file_sha256(output / name)
        for name in (
            "FREEZE.json",
            "ORACLES.json",
            "REPORT.md",
            "BENCHMARK_AUTHORIZATION_REQUEST.json",
        )
    }
    manifest = {
        "schema": workload.MANIFEST_SCHEMA,
        "status": "frozen_awaiting_explicit_benchmark_authorization",
        "artifacts": artifacts,
        "performance_rows_opened": 0,
        "timing_rows_produced": 0,
        "authorization_granted": False,
    }
    _write_new(output / "MANIFEST.json", manifest)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
