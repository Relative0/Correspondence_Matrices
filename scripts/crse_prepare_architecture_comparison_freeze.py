"""Write the source-blind architecture-comparison corpus and schedule freeze."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.architecture_comparison_freeze import build_freeze


def _write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("freeze output escaped project")
    output.mkdir(parents=True, exist_ok=False)
    checkpoint = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    freeze = build_freeze(project_root=ROOT, source_checkpoint=checkpoint)
    _write_new(output / "FREEZE.json", freeze)
    print(json.dumps({
        "status": freeze["status"],
        "freeze_sha256": freeze["freeze_sha256"],
        "fresh_single_root_cases": len(freeze["fresh_corpus"]["single_root_cases"]),
        "fresh_multi_root_cases": len(freeze["fresh_corpus"]["multi_root_cases"]),
        "fresh_history_pairs": len(freeze["fresh_corpus"]["history_pairs"]),
        "planned_cells_A_B_C": sum(
            freeze["schedules"][lane]["planned_cells"] for lane in ("A", "B", "C")
        ),
        "runpod_authorization_request": freeze["permissions"]["runpod_authorization_request"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
