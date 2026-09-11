"""Replay the saved local panel schedule, outputs, accounting and summaries.

Boolean oracle and bootstrap code are shared with the harness; exhaustive scalar
truth tests are the independent implementation check. No timing is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json

from scripts import cm_packed_queries_campaign as campaign


def verify(output):
    frozen = campaign.check_sources(output)
    fixtures = json.loads((output / "FIXTURES.json").read_text())
    checked = outputs = memory_rows = 0
    for cohort, cases in fixtures.items():
        expected_schedule = [row for row in frozen["schedule"] if row["cohort"] == cohort]
        rows = [json.loads(line) for line in (output / f"{cohort}-RAW.jsonl").read_text().splitlines()]
        if [{key: row[key] for key in ("cohort", "case", "q", "repeat", "method")} for row in rows] != expected_schedule:
            raise ValueError("schedule mismatch")
        targets = {(case["id"], q): campaign.expected(case, q) for case in cases
                   for q in ((32,) if case["task"] == "cache" else (1, 16))}
        recorded = json.loads((output / f"{cohort}-ORACLES.json").read_text())
        if {(row["case"], row["q"]): row["result"] for row in recorded} != targets:
            raise ValueError("oracle mismatch")
        for row in rows:
            target = targets[row["case"], row["q"]]
            if not row["exact"] or hashlib.sha256(target.encode()).hexdigest() != row["result_sha256"]:
                raise ValueError("output mismatch")
            if row["total_ns"] != row["setup_ns"] + row["query_delivery_ns"] + row["cleanup_ns"]:
                raise ValueError("stage accounting mismatch")
            if row["cache"]["entry_bytes"] > row["cache"]["max_bytes"]:
                raise ValueError("admission budget violation")
            checked += 1
            outputs += row["q"]
        if campaign.summarize(rows) != json.loads((output / f"{cohort}-SUMMARY.json").read_text()):
            raise ValueError("summary mismatch")
        memory = json.loads((output / f"{cohort}-MEMORY.json").read_text())
        expected_memory = [(case["id"], q, method) for case in cases
                           for q in ((32,) if case["task"] == "cache" else (1, 16))
                           for method in campaign.methods(case)]
        if [(r["case"], r["q"], r["method"]) for r in memory] != expected_memory:
            raise ValueError("memory schedule mismatch")
        if any(r["cache"]["entry_bytes"] > r["cache"]["max_bytes"] for r in memory):
            raise ValueError("memory budget violation")
        memory_rows += len(memory)
    lifecycle = json.loads((output / "LIFECYCLE.json").read_text())
    indexed = {case["id"]: case for cases in fixtures.values() for case in cases}
    for row in lifecycle:
        if not row["exact"] or row["result"] != campaign.expected(indexed[row["case"]], row["q"]):
            raise ValueError("lifecycle output mismatch")
    receipt = {"schema": "cm-packed-queries-replay/v1", "status": "verified",
               "timing_rows": checked, "cold_outputs": outputs,
               "warm_outputs_asserted_in_run_not_saved": outputs,
               "memory_rows": memory_rows, "lifecycle_children": len(lifecycle),
               "shared_oracle_and_bootstrap_code": True,
               "artifacts": {p.name: campaign.sha(p) for p in output.iterdir() if p.is_file()}}
    campaign.write(output / "VERIFICATION.json", receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != "artifacts"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=campaign.Path, required=True)
    args = parser.parse_args()
    verify(args.output)


if __name__ == "__main__":
    main()
