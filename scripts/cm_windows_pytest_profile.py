"""Inspect or verify the maintained Windows pytest profile."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.pytest_profiles import profile_summary, validate_profile  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "show"))
    args = parser.parse_args()
    summary = profile_summary(validate_profile())
    if args.action == "verify":
        print(
            json.dumps(
                {
                    "status": "passed",
                    "profile": summary["profile"],
                    "historical_replay_tests": summary["historical_replay_tests"],
                    "optional_modules": summary["optional_modules"],
                }
            )
        )
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

