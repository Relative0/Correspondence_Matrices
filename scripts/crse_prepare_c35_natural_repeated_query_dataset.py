"""Freeze the outcome-independent C35 natural repeated-query dataset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_natural_repeated_queries import build_dataset_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/recognition/c35_natural_repeated_query_dataset.json")
    args = parser.parse_args()
    c34 = ROOT / "docs/recognition/c34_natural_headroom_dataset.json"
    verification = ROOT / "docs/recognition/c34_natural_headroom_dataset_verification.json"
    source = ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset.json"
    manifest = build_dataset_manifest(
        c34, verification, source,
        c34_manifest_relative=c34.relative_to(ROOT).as_posix(),
        c34_verification_relative=verification.relative_to(ROOT).as_posix(),
        source_relative=source.relative_to(ROOT).as_posix(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": "frozen", "cases": 8, "queries": 512,
                      "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
