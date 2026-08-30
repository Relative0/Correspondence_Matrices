"""Record the V3 relation-regression preflight without exposing credentials."""

from __future__ import annotations

import json

import http_p7_w3_relation_regression_preflight_v3 as preflight


def main() -> int:
    result = preflight.check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
