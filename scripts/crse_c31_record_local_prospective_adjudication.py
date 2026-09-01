"""Record the frozen C31 gates on the existing C30 Windows execution."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_prepared_policy_adjudication import adjudicate_execution


CONTRACT = ROOT / "docs/recognition/c31_prepared_policy_replication_contract.json"
OUTPUT = (
    ROOT / "docs/recognition/c31_linux_confirmation/"
    "C31_LOCAL_PROSPECTIVE_ADJUDICATION_20260901.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C31 local adjudication")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    run = ROOT / contract["local_execution"]["run"]
    for name, identity in contract["local_execution"]["files"].items():
        path = run / name
        if path.stat().st_size != identity["bytes"] or sha256(path) != identity["sha256"]:
            raise ValueError(f"frozen local C30 evidence changed: {name}")
    result = json.loads((run / "results.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (run / "measurements.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    adjudication = adjudicate_execution(
        rows,
        lifecycle_preparation_ns=result["summary"]["lifecycle_preparation_ns"],
    )
    output = {
        "schema": "crse-c31-local-prospective-adjudication/v1",
        "status": "pass" if adjudication["admissible"] else "fail",
        "prospective_contract_frozen_before_second_machine_timing": True,
        "contract_sha256": sha256(CONTRACT),
        "execution_id": contract["local_execution"]["execution_id"],
        "physical_machine_id": contract["local_execution"]["physical_machine_id"],
        "adjudication": adjudication,
        "policy_refit": False,
        "training": False,
        "shadow_promotion": False,
        "production_promotion": False,
    }
    OUTPUT.write_bytes(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "status": output["status"],
        "contract_sha256": output["contract_sha256"],
        "aggregate_lower": adjudication[
            "paired_block_median_lower_bounds"]["aggregate_speedup"],
        "minimum_width_lower": adjudication[
            "paired_block_median_lower_bounds"]["minimum_width_speedup"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
