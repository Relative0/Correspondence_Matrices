"""Set one V5 W3 partition identity and invoke its preflight/controller."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import runpy
import sys


SHARDS = ("ir-development-b", "relation-development-a", "relation-development-b")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "run"))
    parser.add_argument("shard", choices=SHARDS)
    args = parser.parse_args()
    os.environ["CM_W3_SPLIT_ID"] = args.shard
    here = Path(__file__).resolve().parent
    target = here / (
        "record_p7_w3_split_preflight_v5.py"
        if args.mode == "preflight"
        else "runpod_p7_w3_split_controller_v5.py"
    )
    sys.argv = [str(target)]
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
