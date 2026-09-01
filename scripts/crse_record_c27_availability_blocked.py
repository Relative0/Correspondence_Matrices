"""Seal C27 RunPod availability exhaustion with zero create requests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_linux_confirmation"
ATTEMPT_A = HERE / "runpod-c27-linux-execute-001"
ATTEMPT_B = HERE / "runpod-c27-linux-execute-001b"
WAIT_A = HERE / "C27_ZERO_INVENTORY_WAIT_20260831.jsonl"
WAIT_B = HERE / "C27_AVAILABILITY_WAIT_V2_20260901.jsonl"
AUTHORIZATION = HERE / "RUNPOD_C27_EXACT_PAYLOAD_AUTHORIZED_2026_08_31.json"
OUTPUT = HERE / "RUNPOD_C27_AVAILABILITY_BLOCKED_VERIFICATION_20260901.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 availability verification")
    runs = [load(ATTEMPT_A / "RUN.json"), load(ATTEMPT_B / "RUN.json")]
    waits = rows(WAIT_A) + rows(WAIT_B)
    preflight_rows = rows(ATTEMPT_B / "preflight-availability.jsonl")
    video_name = "cm-video-first5-production-v1-a1-339b3cfb0d"
    if (
        any(run.get("status") != "failed" for run in runs)
        or any(run.get("creation_attempted") is not False for run in runs)
        or any(run.get("creation_uncertain") is not False for run in runs)
        or any(run.get("pod_created") is not False for run in runs)
        or any(run.get("uploaded_source_files") != 0 for run in runs)
        or any(run.get("automatic_replacement_queued") is not False for run in runs)
        or runs[1].get("error") != "C27 Secure CPU availability wait expired before create"
        or not waits or not preflight_rows
        or any(row.get("resource_writes") != 0 for row in waits)
        or any(row.get("credential_values_recorded") is not False for row in waits)
        or any(row.get("pod_names") != [video_name] for row in waits)
        or any(row.get("unrelated_baseline_allowed") is not True for row in preflight_rows)
        or any(row.get("selected_offer") is not None for row in preflight_rows)
    ):
        raise ValueError("C27 availability-blocked evidence mismatch")
    authorization = load(AUTHORIZATION)
    result = {
        "schema": "crse-runpod-c27-availability-blocked-verification/v1",
        "status": "verified_reconciled",
        "controller_invocations_checked": 2,
        "read_only_wait_checks": len(waits),
        "controller_availability_checks": len(preflight_rows),
        "create_requests": 0,
        "pod_created": False,
        "files_uploaded": 0,
        "estimated_cost_usd": 0.0,
        "automatic_replacement_queued": False,
        "authorization_remains_unused": True,
        "authorization_sha256": sha256(AUTHORIZATION),
        "authorized_create_requests": authorization["create_requests"],
        "unrelated_pod": {
            "pod_id": "vqos7wif838oxx", "pod_name": video_name,
            "ownership": "unrelated_not_modified",
        },
        "final_observed_inventories": {"v1": 1, "v2": 1},
        "blocker": "no_eligible_secure_cpu_offer",
        "attempt_a_run_sha256": sha256(ATTEMPT_A / "RUN.json"),
        "attempt_b_run_sha256": sha256(ATTEMPT_B / "RUN.json"),
        "wait_a_sha256": sha256(WAIT_A),
        "wait_b_sha256": sha256(WAIT_B),
        "credentials_recorded_or_uploaded": False,
        "production_write": False,
    }
    OUTPUT.write_bytes(json.dumps(
        result, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
