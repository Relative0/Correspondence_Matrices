"""Seal the C27 preflight block as zero-create evidence and an unrelated baseline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_linux_confirmation"
ATTEMPT = HERE / "runpod-c27-linux-execute-001"
RUN = ATTEMPT / "RUN.json"
PREFLIGHT = ATTEMPT / "PREFLIGHT.json"
WAIT = HERE / "C27_ZERO_INVENTORY_WAIT_20260831.jsonl"
OUTPUT = HERE / "RUNPOD_C27_PRECREATE_BLOCKER_VERIFICATION_20260831.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 precreate verification")
    run, preflight = load(RUN), load(PREFLIGHT)
    inventories = preflight.get("inventories", {})
    normalized = {
        version: sorted({(row.get("id"), row.get("name"))
                         for row in inventories.get(version, [])})
        for version in ("v1", "v2")
    }
    expected = [("vqos7wif838oxx", "cm-video-first5-production-v1-a1-339b3cfb0d")]
    wait_rows = [json.loads(line) for line in WAIT.read_text(encoding="utf-8").splitlines()]
    if (
        run.get("status") != "failed"
        or run.get("creation_attempted") is not False
        or run.get("creation_uncertain") is not False
        or run.get("pod_created") is not False
        or run.get("uploaded_source_files") != 0
        or run.get("automatic_replacement_queued") is not False
        or run.get("error") != "C27 account/resource/budget preflight failed"
        or preflight.get("resource_writes") != 0
        or preflight.get("credential_values_recorded") is not False
        or normalized != {"v1": expected, "v2": expected}
        or not wait_rows
        or any(row.get("resource_writes") != 0 for row in wait_rows)
        or any(row.get("credential_values_recorded") is not False for row in wait_rows)
        or any(row.get("pod_names") != [expected[0][1]] for row in wait_rows)
    ):
        raise ValueError("C27 precreate blocker evidence mismatch")
    record = {
        "schema": "crse-runpod-c27-precreate-blocker-verification/v1",
        "status": "pass",
        "create_requests": 0,
        "pod_created": False,
        "files_uploaded": 0,
        "resource_writes": 0,
        "authorization_remains_unused": True,
        "blocked_by_unrelated_baseline": True,
        "allowed_unrelated_baseline": {
            "pod_id": expected[0][0], "pod_name": expected[0][1],
            "ownership": "unrelated_do_not_modify",
        },
        "failed_run_sha256": sha256(RUN),
        "preflight_sha256": sha256(PREFLIGHT),
        "wait_sha256": sha256(WAIT),
        "read_only_wait_checks": len(wait_rows),
        "credentials_recorded_or_uploaded": False,
    }
    OUTPUT.write_bytes(json.dumps(
        record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
