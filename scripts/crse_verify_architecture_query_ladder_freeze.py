"""Independently replay the query-ladder follow-up freeze."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.architecture_query_ladder_followup import verify_followup_freeze


DEFAULT_FREEZE = (
    ROOT / "docs/recognition/architecture_query_ladder_followup_freeze_20260903/FREEZE.json"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    freeze_path = args.freeze.resolve()
    output = args.output.resolve() if args.output else freeze_path.parent / "VERIFICATION.json"
    if not output.is_relative_to(ROOT) or output.exists():
        raise SystemExit("verification output must be a new in-project file")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    verification = verify_followup_freeze(freeze, ROOT)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(verification, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
