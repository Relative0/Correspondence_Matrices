"""Register the safely reconciled but scientifically incomplete C7 cloud attempt."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
HERE = DOCS / "c7_linux_confirmation"
VERIFY = HERE / "RUNPOD_C7_LINUX_FINAL_VERIFICATION_20260830-031326-558392.json"
RUN = HERE / "runpod-c7-linux-confirmation-execute-002" / "RUN.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C7_SECOND_MACHINE_ATTEMPT_2026_08_30.md"
MACHINE = "learning_milestone_c7_second_machine_attempt_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    verification, run = load(VERIFY), load(RUN)
    if (verification.get("status") != "safe_failure_reconciled"
            or verification.get("complete") is not True
            or verification.get("scientific_confirmation_complete") is not False
            or verification.get("owned_pod_absent_verified") is not True
            or verification.get("automatic_replacement_queued") is not False
            or verification.get("create_requests_this_authorization") != 1
            or verification.get("uploaded_source_files") != 0
            or run.get("cleanup", {}).get("owned_pod_absent") is not True):
        raise SystemExit("refusing registration: C7 cloud failure is not safely reconciled")
    machine = {
        "schema": "crse-learning-milestone-c7-second-machine-attempt-summary/v1",
        "date": "2026-08-30",
        "status": "safe_failure_reconciled",
        "scientific_confirmation_complete": False,
        "report": REPORT,
        "verification": {"path": str(VERIFY.relative_to(ROOT)).replace("\\", "/"), **verification},
        "controller_run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "failure_stage": verification["failure_stage"],
        "failure": verification["failure"],
        "create_requests": 1,
        "automatic_replacement_queued": False,
        "uploaded_source_files": 0,
        "estimated_compute_cost_usd": verification["estimated_compute_cost_usd"],
        "interpretation": (
            "The sole authorized pod matched all resource limits but failed at the proxy payload endpoint before upload. "
            "Cleanup is independently verified; no second-machine scientific timing was produced."
        ),
    }
    (DOCS / MACHINE).write_bytes(json.dumps(machine, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")

    data = load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer contains exact R01-R18 and eight applications")
    updates = {
        "R16": ("The first C7 second-machine attempt failed before upload and was safely reconciled with zero replacements.",
                "Use a separately authorized single-port transport to obtain the missing cross-machine timing."),
        "R18": ("The failed external attempt is retained as transport evidence; it contains no scientific timing and cannot confirm a ranking.",
                "Keep transport success separate from exactness and timing criteria in the corrected confirmation."),
    }
    by_id = {track["id"]: track for track in data["tracks"]}
    for track_id, (reason, next_experiment) in updates.items():
        track = by_id[track_id]
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        result = {"report": REPORT, "machine_summary": MACHINE, "scope": reason}
        existing = [row for row in track["results"] if row.get("report") == REPORT]
        if len(existing) > 1:
            raise SystemExit(f"duplicate C7 Linux-attempt registration for {track_id}")
        if existing:
            existing[0].update(result)
        else:
            track["results"].append(result)
    data["milestones"]["C"] = (
        "C7 independent Yosys confirmation complete locally; first second-machine attempt safely reconciled after pre-upload transport failure, timing still pending"
    )
    data["updated"] = "2026-08-30"
    REGISTER.write_bytes(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "updated_tracks": sorted(updates), "scientific_confirmation_complete": False,
                      "owned_pod_absent": True}, sort_keys=True))


if __name__ == "__main__":
    main()
