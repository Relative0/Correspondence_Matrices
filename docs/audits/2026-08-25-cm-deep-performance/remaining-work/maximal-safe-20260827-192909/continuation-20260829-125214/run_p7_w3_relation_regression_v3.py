"""Invoke the frozen V3 W3 relation-regression preflight or controller."""

from __future__ import annotations

import argparse
from pathlib import Path
import runpy
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "run"))
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    target = here / (
        "record_p7_w3_relation_regression_preflight_v3.py"
        if args.mode == "preflight"
        else "runpod_p7_w3_relation_regression_controller_v3.py"
    )
    sys.argv = [str(target)]
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
