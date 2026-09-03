"""Freeze the C34 task-role manifest over the full-width C23 natural corpus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_natural_headroom import build_dataset_manifest


DEFAULT_SOURCE = ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset.json"
DEFAULT_VERIFICATION = ROOT / "docs/recognition/c23_yosys_fresh_gf2_dataset_verification.json"
DEFAULT_OUTPUT = ROOT / "docs/recognition/c34_natural_headroom_dataset.json"


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--source-verification", type=Path, default=DEFAULT_VERIFICATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    manifest = build_dataset_manifest(
        args.source,
        args.source_verification,
        source_relative=relative(args.source),
        verification_relative=relative(args.source_verification),
    )
    write_new(args.output, manifest)
    print(json.dumps(manifest["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
