"""Independently verify and summarize an authorized native-batch timing run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cmbench.comparative import gf2_native_slot_batch_workload as workload


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--oracles", type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    freeze_path = args.freeze.resolve()
    oracles_path = args.oracles.resolve()
    if not run.is_relative_to(ROOT.resolve()):
        raise ValueError("run must remain inside the project")
    freeze = _load(freeze_path)
    oracles = _load(oracles_path)
    result = _load(run / "RESULT.json")
    rows = [
        json.loads(line)
        for line in (run / "RAW.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    workload.validate_freeze(freeze, ROOT)
    workload.validate_oracles(oracles, freeze, replay=False)
    if (
        result.get("freeze_file_sha256") != workload.file_sha256(freeze_path)
        or result.get("oracles_file_sha256") != workload.file_sha256(oracles_path)
        or result.get("raw_file_sha256") != workload.file_sha256(run / "RAW.jsonl")
    ):
        raise ValueError("run identity mismatch")
    summary = workload.summarize_rows(rows, freeze, oracles)
    summary.update({
        "freeze_file_sha256": workload.file_sha256(freeze_path),
        "oracles_file_sha256": workload.file_sha256(oracles_path),
        "raw_file_sha256": workload.file_sha256(run / "RAW.jsonl"),
        "result_file_sha256": workload.file_sha256(run / "RESULT.json"),
        "physical_machine_sha256": result["physical_machine_sha256"],
    })
    _write_new(run / "INDEPENDENT_VERIFICATION.json", summary)
    print(run / "INDEPENDENT_VERIFICATION.json")
    return 0 if summary["verification"]["verified_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
