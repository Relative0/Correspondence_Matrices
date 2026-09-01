"""Adjudicate frozen local C30 and second-machine C31 evidence without refitting."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_prepared_policy_adjudication import (
    adjudicate_cross_machine,
)


CONTRACT = ROOT / "docs/recognition/c31_prepared_policy_replication_contract.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def execution(run: Path, execution_id: str, physical_machine_id: str):
    result = load(run / "results.json")
    verification = load(run / "independent_verification.json")
    measurements = run / "measurements.jsonl"
    if (
        result.get("status") != "complete"
        or result.get("semantic_or_artifact_mismatches") != 0
        or verification.get("status") != "verified"
        or verification.get("results_sha256") != sha256(run / "results.json")
        or verification.get("measurement_batches_checked") != 128
        or verification.get("timed_query_records_checked") != 1024
    ):
        raise ValueError(f"unverified C30/C31 execution: {run}")
    return {
        "execution_id": execution_id,
        "physical_machine_id": physical_machine_id,
        "environment": result["environment"],
        "measurements_sha256": sha256(measurements),
        "independent_verification_sha256": sha256(
            run / "independent_verification.json"),
        "lifecycle_preparation_ns": result["summary"]["lifecycle_preparation_ns"],
        "rows": load_rows(measurements),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-run", type=Path, required=True)
    parser.add_argument("--remote-execution-id", required=True)
    parser.add_argument("--remote-physical-machine-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = load(CONTRACT)
    local = ROOT / contract["local_execution"]["run"]
    for name, expected in contract["local_execution"]["files"].items():
        if sha256(local / name) != expected["sha256"]:
            raise ValueError(f"frozen local C30 evidence changed: {name}")
    adjudication = adjudicate_cross_machine([
        execution(
            local,
            contract["local_execution"]["execution_id"],
            contract["local_execution"]["physical_machine_id"],
        ),
        execution(
            args.remote_run.resolve(),
            args.remote_execution_id,
            args.remote_physical_machine_id,
        ),
    ])
    adjudication["contract_sha256"] = sha256(CONTRACT)
    adjudication["local_run"] = contract["local_execution"]["run"]
    adjudication["remote_run"] = str(args.remote_run.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(adjudication, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({
        "status": "complete",
        "replication_admissible": adjudication["replication_admissible"],
        "decision": adjudication["decision"],
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
