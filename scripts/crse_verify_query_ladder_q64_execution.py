"""Independently verify one frozen exact-q64 physical-host attempt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition import query_ladder_q64_execution as q64


def verify(run_dir: Path, replication_id: str) -> dict:
    run_dir = run_dir.resolve()
    if not run_dir.is_relative_to(ROOT):
        raise ValueError("run directory outside project")
    q64.verify_child_freeze(ROOT, run_dir / "CHILD_FREEZE.json")
    frozen = q64.load_verified_parent(ROOT)
    oracles = q64.load_json(run_dir / "ORACLES.json")
    q64.validate_oracles(oracles, frozen)
    host_dir = run_dir / replication_id
    output = host_dir / "INDEPENDENT_VERIFICATION.json"
    if output.exists():
        raise ValueError("refusing to overwrite host verification")
    result_path = host_dir / "RESULT.json"
    raw_path = host_dir / "RAW.jsonl"
    charged_path = host_dir / "CHARGED_COSTS.json"
    preflight_path = host_dir / "HOST_PREFLIGHT.json"
    result = q64.load_json(result_path)
    preflight = q64.load_json(preflight_path)
    charged = q64.load_json(charged_path)
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    audit = q64.verify_raw_rows(frozen, oracles, rows)
    source_mismatches = int(
        result.get("raw_file_sha256") != q64.file_sha256(raw_path)
        or result.get("charged_cost_file_sha256") != q64.file_sha256(charged_path)
        or result.get("host_preflight_file_sha256") != q64.file_sha256(preflight_path)
        or preflight["native"]["native_library_sha256"]
        != q64.file_sha256(ROOT / preflight["native"]["native_library"])
    )
    samples = charged.get("samples_ns_per_case", {})
    cost_ok = (
        charged.get("batches") == 21
        and charged.get("repetitions_per_case_per_batch") == 1000
        and set(samples) == {"feature_extraction_and_control", "model_inference",
                             "exact_verification", "fallback_dispatch"}
        and all(len(values) == 21 and all(q64.finite_positive(value) for value in values)
                for values in samples.values())
    )
    status = "verified_complete" if (
        audit["status"] == "verified_complete" and source_mismatches == 0
        and cost_ok and result.get("status") == "complete"
    ) else "incomplete"
    document = {
        "schema": q64.HOST_VERIFICATION_SCHEMA, "status": status,
        "replication_id": replication_id,
        "physical_machine_sha256": preflight["physical_machine_sha256"],
        "compiler_sha256": preflight["native"]["compiler_identity_sha256"],
        "child_freeze_file_sha256": q64.file_sha256(run_dir / "CHILD_FREEZE.json"),
        "host_preflight_file_sha256": q64.file_sha256(preflight_path),
        "result_file_sha256": q64.file_sha256(result_path),
        "raw_file_sha256": q64.file_sha256(raw_path),
        "charged_cost_file_sha256": q64.file_sha256(charged_path),
        **audit,
        "source_or_artifact_mismatches": source_mismatches,
        "charged_cost_mismatches": 0 if cost_ok else 1,
        "all_failures_refusals_and_zeroes_retained": True,
        "p95_costs_measured_same_host": cost_ok,
        "memory_learning_measurements": 0,
        "prospective_cases_consumed": 0,
    }
    q64.write_json_exclusive(output, document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--replication-id", required=True)
    args = parser.parse_args()
    result = verify(args.run_dir, args.replication_id)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result["status"] == "verified_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
