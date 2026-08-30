"""Set one frozen W3 shard identity and invoke its preflight or controller."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import runpy
import sys


SHARDS = ("ir-regression", "ir-development", "relation-regression", "relation-development")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "run"))
    parser.add_argument("shard", choices=SHARDS)
    args = parser.parse_args()
    os.environ["CM_W3_SHARD_ID"] = args.shard
    here = Path(__file__).resolve().parent
    target = (
        here / "record_p7_w3_shard_preflight_v1.py"
        if args.mode == "preflight"
        else here / "runpod_p7_w3_shard_controller_v2.py"
    )
    sys.argv = [str(target)]
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
