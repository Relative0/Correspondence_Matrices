"""Run the post-C38 four-lane local functional admission harness."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.architecture_refresh_harness import (
    build_plan,
    find_native_library,
    run_functional_validation,
)


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json",
    )
    parser.add_argument("--native-library", type=Path)
    parser.add_argument("--without-native", action="store_true")
    args = parser.parse_args()
    if args.without_native and args.native_library is not None:
        raise ValueError("--without-native conflicts with --native-library")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    dataset_path = args.dataset.resolve()
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes)
    native_path = None if args.without_native else (
        args.native_library.resolve()
        if args.native_library is not None
        else find_native_library(ROOT)
    )
    plan = build_plan(native_available=native_path is not None)
    result = run_functional_validation(
        dataset,
        dataset_sha256=hashlib.sha256(dataset_bytes).hexdigest(),
        native_library_path=native_path,
    )
    _write_json(output / "PLAN.json", plan)
    _write_json(output / "RESULT.json", result)
    print(json.dumps({
        "status": result["status"],
        "all_exact": result["all_exact"],
        "native_included": native_path is not None,
        "lane_a_arms": len(result["lanes"]["A"]["arms"]),
        "lane_b_cells": sum(
            len(checkpoint["arms"])
            for checkpoint in result["lanes"]["B"]["checkpoints"].values()
        ),
        "lane_c_arms": len(result["lanes"]["C"]["arms"]),
        "lane_d_sublanes": len(result["lanes"]["D"]["sublanes"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
