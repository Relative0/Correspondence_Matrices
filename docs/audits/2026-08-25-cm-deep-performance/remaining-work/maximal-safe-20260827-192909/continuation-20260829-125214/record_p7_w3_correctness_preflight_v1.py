"""Record the sanitized, read-only preflight for the P7 W3 correctness scout."""

from __future__ import annotations

import json
import os
from pathlib import Path

import http_p7_w3_correctness_preflight_v1 as preflight


HERE = Path(__file__).resolve().parent
RECEIPT = HERE / "P7-W3-CORRECTNESS-PREFLIGHT-RECEIPT.json"


def main() -> int:
    result = preflight.check()
    temporary = RECEIPT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, RECEIPT)
    print(json.dumps({
        "ready": result.get("ready"),
        "checked_utc": result.get("checked_utc"),
        "selected_offer": result.get("selected_offer"),
        "prior_cost_bound_usd": result.get("prior_cost_bound_usd"),
        "projected_20_min_cost_usd": result.get("projected_20_min_cost_usd"),
        "projected_aggregate_cost_usd": result.get("projected_aggregate_cost_usd"),
        "current_inventories": result.get("current_inventories"),
        "w3_total_cells": result.get("w3_total_cells"),
    }, sort_keys=True))
    return int(result.get("ready") is not True)


if __name__ == "__main__":
    raise SystemExit(main())
