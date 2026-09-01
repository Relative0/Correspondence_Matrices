"""Extend the sealed C27 zero-create record through controller attempt 001c."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_linux_confirmation"
PRIOR = HERE / "RUNPOD_C27_AVAILABILITY_BLOCKED_VERIFICATION_20260901.json"
ATTEMPT = HERE / "runpod-c27-linux-execute-001c"
AUTHORIZATION = HERE / "RUNPOD_C27_EXACT_PAYLOAD_AUTHORIZED_2026_08_31.json"
OUTPUT = HERE / "RUNPOD_C27_AVAILABILITY_BLOCKED_VERIFICATION_V2_20260901.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 availability verification v2")
    prior = load(PRIOR)
    run = load(ATTEMPT / "RUN.json")
    availability = rows(ATTEMPT / "preflight-availability.jsonl")
    released = load(ATTEMPT / "HOST-AWAKE-RELEASED-c27-http-controller.json")
    done = load(ATTEMPT / "watchdog-done.json")
    video = [["vqos7wif838oxx", "cm-video-first5-production-v1-a1-339b3cfb0d"]]
    if (
        prior.get("status") != "verified_reconciled"
        or prior.get("create_requests") != 0
        or prior.get("authorization_remains_unused") is not True
        or run.get("status") != "failed"
        or run.get("creation_attempted") is not False
        or run.get("creation_uncertain") is not False
        or run.get("pod_created") is not False
        or run.get("uploaded_source_files") != 0
        or run.get("automatic_replacement_queued") is not False
        or run.get("error") != "C27 Secure CPU availability wait expired before create"
        or not availability
        or any(row.get("selected_offer") is not None for row in availability)
        or any(row.get("unrelated_baseline_allowed") is not True for row in availability)
        or any(row.get("normalized_inventory") != {"v1": video, "v2": video}
               for row in availability)
        or released.get("released") is not True
        or done.get("no_create_request") is not True
        or sha256(AUTHORIZATION) != prior.get("authorization_sha256")
    ):
        raise ValueError("C27 availability-blocked v2 evidence mismatch")
    result = {
        "schema": "crse-runpod-c27-availability-blocked-verification/v2",
        "status": "verified_reconciled",
        "controller_invocations_checked": prior["controller_invocations_checked"] + 1,
        "read_only_wait_checks": prior["read_only_wait_checks"],
        "controller_availability_checks": (
            prior["controller_availability_checks"] + len(availability)),
        "create_requests": 0,
        "pod_created": False,
        "files_uploaded": 0,
        "estimated_cost_usd": 0.0,
        "automatic_replacement_queued": False,
        "authorization_remains_unused": True,
        "authorization_sha256": sha256(AUTHORIZATION),
        "authorized_create_requests": prior["authorized_create_requests"],
        "unrelated_pod": prior["unrelated_pod"],
        "final_observed_inventories": {"v1": 1, "v2": 1},
        "blocker": "no_eligible_secure_cpu_offer",
        "prior_verification_sha256": sha256(PRIOR),
        "attempt_c_run_sha256": sha256(ATTEMPT / "RUN.json"),
        "attempt_c_availability_sha256": sha256(
            ATTEMPT / "preflight-availability.jsonl"),
        "host_awake_released": True,
        "credentials_recorded_or_uploaded": False,
        "production_write": False,
    }
    OUTPUT.write_bytes(json.dumps(
        result, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
