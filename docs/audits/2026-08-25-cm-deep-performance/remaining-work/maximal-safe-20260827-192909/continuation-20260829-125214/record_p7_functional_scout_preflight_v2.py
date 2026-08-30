"""Record the sanitized, read-only Runpod preflight for the P7 V2 scout."""

from __future__ import annotations

import json
import os
from pathlib import Path

import http_p7_functional_scout_preflight_v2 as preflight


HERE = Path(__file__).resolve().parent
RECEIPT = HERE / "P7-FUNCTIONAL-SCOUT-V2-PREFLIGHT-RECEIPT.json"


def main() -> int:
    result = preflight.check()
    temporary = RECEIPT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, RECEIPT)
    summary = {
        "ready": result.get("ready"),
        "checked_utc": result.get("checked_utc"),
        "selected_offer": result.get("selected_offer"),
        "projected_20_min_cost_usd": result.get("projected_20_min_cost_usd"),
        "projected_aggregate_cost_usd": result.get("projected_aggregate_cost_usd"),
        "current_inventories": result.get("current_inventories"),
    }
    print(json.dumps(summary, sort_keys=True))
    return int(result.get("ready") is not True)


if __name__ == "__main__":
    raise SystemExit(main())
