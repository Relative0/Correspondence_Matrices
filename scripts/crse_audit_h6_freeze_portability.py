"""Read-only line-ending portability audit for the historical H6 freeze."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.h6_freeze_portability import DEFAULT_FREEZE, audit_h6_freeze


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", default=DEFAULT_FREEZE)
    parser.add_argument(
        "--show-bindings",
        action="store_true",
        help="include every per-file match record instead of the compact audit summary",
    )
    arguments = parser.parse_args()
    result = audit_h6_freeze(ROOT, arguments.freeze)
    if not arguments.show_bindings:
        result = {key: value for key, value in result.items() if key != "bindings"}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("verified_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
