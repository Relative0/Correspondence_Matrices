"""Read-only sanitized shape probe for Runpod billing reconciliation."""
from datetime import datetime, timezone
import json

import http_structural_preflight_v3 as preflight


params = {"startTime": "2026-08-27T00:00:00Z", "endTime": preflight.utc_now(),
          "bucketSize": "day", "grouping": "podId"}
with preflight.session() as client:
    v2 = client.get(preflight.V2 + "/billing/pods", params=params, timeout=15, allow_redirects=False)
    v2.raise_for_status()
    v2_body = v2.json()
    v1 = client.get(preflight.V1 + "/billing/pods", params=params, timeout=15, allow_redirects=False)
    v1.raise_for_status()
    v1_body = v1.json()

metadata = v2_body.get("metadata") if isinstance(v2_body, dict) else None
v2_rows = v2_body.get("records", []) if isinstance(v2_body, dict) else []
rows = v1_body if isinstance(v1_body, list) else []
report = {
    "checked_utc": preflight.utc_now(),
    "resource_writes": 0,
    "credential_values_recorded": False,
    "v2_top_level_type": type(v2_body).__name__,
    "v2_top_level_keys": sorted(v2_body) if isinstance(v2_body, dict) else None,
    "v2_metadata": metadata,
    "v2_record_count": len(v2_rows) if isinstance(v2_rows, list) else None,
    "v2_record_keys": sorted({key for row in v2_rows if isinstance(row, dict) for key in row})
                      if isinstance(v2_rows, list) else None,
    "v2_records": [{key: row.get(key) for key in ("podId", "amount", "time")}
                   for row in v2_rows if isinstance(row, dict)] if isinstance(v2_rows, list) else None,
    "v1_top_level_type": type(v1_body).__name__,
    "v1_top_level_keys": sorted(v1_body) if isinstance(v1_body, dict) else None,
    "v1_row_count": len(rows),
    "v1_row_keys": sorted({key for row in rows if isinstance(row, dict) for key in row}),
    "v1_rows": [{key: row.get(key) for key in ("podId", "amount", "time")}
                for row in rows if isinstance(row, dict)],
}
path = preflight.HERE / ("HTTP-STRUCTURAL-BILLING-SHAPE-" +
    datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json")
with path.open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps(report, indent=2, sort_keys=True))
print("evidence_file=" + str(path))
