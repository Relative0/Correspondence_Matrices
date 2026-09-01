"""Verify bounded exact C27 outputs inside the pinned Linux runtime."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys

run = Path(sys.argv[1])
output = Path(sys.argv[2])
scope = os.environ.get("CRSE_EVIDENCE_SCOPE")
if scope not in {"same-host", "independent-machine"}:
    raise SystemExit("invalid CRSE_EVIDENCE_SCOPE")
result = json.loads((run / "results.json").read_text(encoding="utf-8"))
verification = json.loads((run / "independent_verification.json").read_text(encoding="utf-8"))
checks = {
    "result_complete": result.get("status") == "complete",
    "measurement_batches": result.get("measurement_batches") == 720,
    "timed_queries": result.get("timed_queries") == 7560,
    "memory_batches": result.get("memory_measurement_batches") == 24,
    "fallback_controls": result.get("fallback_controls") == 48,
    "selected_path_controls": result.get("selected_path_controls") == 48,
    "refusal_controls": result.get("refusal_controls") == 10,
    "result_exactness": result.get("semantic_or_artifact_mismatches") == 0,
    "verification_status": verification.get("status") == "verified",
    "verified_batches": verification.get("measurement_batches_checked") == 720,
    "verified_queries": verification.get("timed_query_records_checked") == 7560,
    "summary_recomputed": verification.get("summary_recomputed") is True,
    "verified_exactness": verification.get("semantic_or_artifact_mismatches") == 0,
}
if not all(checks.values()):
    raise SystemExit("C27 output invariant failed: " + json.dumps(checks, sort_keys=True))
gate = result.get("summary", {}).get("support_aware_confirmation_gate")
if type(gate) is not bool:
    raise SystemExit("C27 timing gate is missing")
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
record = {
    "schema": "crse-c27-independent-docker-result/v1",
    "status": "verified",
    "evidence_scope": scope,
    "second_machine_replication": scope == "independent-machine",
    "measurement_batches": 720,
    "timed_queries": 7560,
    "memory_batches": 24,
    "semantic_or_artifact_mismatches": 0,
    "independent_verification": "verified",
    "support_aware_confirmation_gate": gate,
    "support_aware_break_even_query_count": result["summary"].get(
        "support_aware_break_even_query_count"),
    "results_sha256": digest(run / "results.json"),
    "independent_verification_sha256": digest(run / "independent_verification.json"),
    "network_during_workload": False,
    "production_promotion": False,
    "training": False,
    "production_write": False,
}
output.write_bytes(json.dumps(record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
print(json.dumps(record, sort_keys=True))
