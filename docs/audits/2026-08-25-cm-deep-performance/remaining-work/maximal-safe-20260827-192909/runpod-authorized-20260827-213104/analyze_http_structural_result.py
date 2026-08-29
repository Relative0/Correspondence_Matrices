"""Trivial local aggregation of the retrieved Runpod structural evidence."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import statistics

import runpod_structural_controller_v4 as controller

ROOT = controller.OUT / "evidence/run-output/structural"


def aggregate(rows):
    legacy_peak_over = [row["tracemalloc_peak_bytes"] / row["legacy_estimate"] for row in rows]
    candidate_peak_over = [row["tracemalloc_peak_bytes"] / row["candidate"]["temporary_bytes"] for row in rows]
    candidate_estimate_over = [1 / value for value in candidate_peak_over]
    ordered = sorted(candidate_estimate_over)
    return {"calls": len(rows),
            "legacy_underestimates": sum(value > 1 for value in legacy_peak_over),
            "candidate_underestimates": sum(value > 1 for value in candidate_peak_over),
            "legacy_max_peak_over_estimate": max(legacy_peak_over),
            "candidate_max_peak_over_estimate": max(candidate_peak_over),
            "candidate_median_estimate_over_peak": statistics.median(candidate_estimate_over),
            "candidate_p95_estimate_over_peak": ordered[math.ceil(0.95 * len(ordered)) - 1],
            "candidate_max_estimate_over_peak": max(candidate_estimate_over)}


raw_path = ROOT / "raw.jsonl"
summary_path = ROOT / "summary.json"
rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
eligible = [row for row in rows if row.get("comparison_eligible") and row.get("status") == "ok"]
breakdowns = {}
for field in ("family", "k", "representation", "schedule", "role"):
    values = sorted({row[field] for row in eligible}, key=str)
    breakdowns[field] = {str(value): aggregate([row for row in eligible if row[field] == value]) for value in values}

locations = []
for row in eligible:
    candidate_ratio = row["candidate"]["temporary_bytes"] / row["tracemalloc_peak_bytes"]
    legacy_ratio = row["tracemalloc_peak_bytes"] / row["legacy_estimate"]
    locations.append({"case_id": row["case_id"], "family": row["family"], "k": row["k"],
                      "representation": row["representation"], "schedule": row["schedule"],
                      "repetition": row["repetition"], "candidate_estimate_over_peak": candidate_ratio,
                      "legacy_peak_over_estimate": legacy_ratio})

decision_statuses = Counter()
decision_reasons = Counter()
false_admissions = 0
false_refusals = 0
for row in eligible:
    for model, decisions in row["profiles"].items():
        for decision in decisions:
            decision_statuses[(model, decision["status"])] += 1
            if decision["reason"]:
                decision_reasons[(model, decision["profile"], decision["reason"])] += 1
            false_admissions += decision["false_admission"] is True
            false_refusals += decision["false_refusal"] is True

result = {"checked_utc": datetime.now(timezone.utc).isoformat(),
          "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
          "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
          "planned_rows": len(rows), "comparable_calls": len(eligible), "overall": aggregate(eligible),
          "breakdowns": breakdowns,
          "max_candidate_conservatism_location": max(locations, key=lambda row: row["candidate_estimate_over_peak"]),
          "max_legacy_underestimate_location": max(locations, key=lambda row: row["legacy_peak_over_estimate"]),
          "policy_decisions": sum(decision_statuses.values()),
          "policy_statuses": {model + ":" + status: count for (model, status), count in sorted(decision_statuses.items())},
          "policy_refusal_reasons": {model + ":" + profile + ":" + reason: count
                                     for (model, profile, reason), count in sorted(decision_reasons.items())},
          "false_admissions": false_admissions, "false_refusals": false_refusals,
          "scope_limit": "synthetic structural families only; no real corpus compatibility and no production acceptance"}
output = controller.HERE / ("HTTP-STRUCTURAL-ANALYSIS-" +
    datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".json")
controller.write(output, result)
print(json.dumps(result, indent=2))
print("evidence_file=" + str(output))
