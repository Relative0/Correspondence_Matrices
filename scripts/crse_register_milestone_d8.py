"""Register verified CRSE Milestone D8 without dropping any track."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
LINUX = DOCS / "linux_confirmation"
RUN = LINUX / "runpod-linux-one-pass-execute-002"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LINUX_ONE_PASS_CONFIRMATION_MILESTONE_D8_2026_08_29.md"
MACHINE = "linux_one_pass_confirmation_milestone_d8_results.json"
FINAL_NAME = "RUNPOD_LINUX_ONE_PASS_FINAL_VERIFICATION_20260829-092727-102016.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


UPDATES = {
    "R03": ("The frozen three-rule pack produced the same 451 one-pass applications on Linux with zero semantic mismatches.",
            "Seek an independently sourced natural factoring or mux corpus before extending the proved pack."),
    "R04": ("Frozen Linux confirmation measured 0.929x for one pass versus no rewrite, reversing the small Windows gain and refusing production promotion.",
            "Train a cheap profitability gate on separate sources and freeze environment calibration before new-source evaluation."),
    "R16": ("The 128-use one-pass policy was 7.6% slower on Linux despite reducing kernel time; rewrite overhead did not portably amortize.",
            "Measure portable structural cost features and environment calibration without tuning on the observed EPFL evaluation slice."),
    "R17": ("Independent hardware transfer was exact but unprofitable: the Windows 1.050x result became 0.929x on Linux.",
            "Treat platform transfer as an abstention signal and test a frozen calibration policy on a new natural source."),
    "R18": ("The frozen Linux run is a retained negative control with zero mismatches, unchanged rule incidence, and a failed profitability criterion.",
            "Keep unconditional one-pass and fixpoint modes as negative controls for future gated policies."),
}


def main() -> None:
    summary = load(RUN / "evidence" / "run-output" / "linux-one-pass-confirmation" / "summary.json")
    run = load(RUN / "RUN.json")
    final = load(LINUX / FINAL_NAME)
    if (summary.get("status") != "complete" or summary.get("semantic_mismatches") != 0
            or run.get("status") != "complete" or final.get("complete") is not True):
        raise SystemExit("refusing D8 registration: run or final verification did not complete")
    machine = {
        "schema": "crse-linux-one-pass-confirmation-milestone-d8-summary/v1",
        "date": "2026-08-29",
        "status": "complete",
        "run": "docs/recognition/linux_confirmation/runpod-linux-one-pass-execute-002",
        "report": REPORT,
        "verification": {"path": "docs/recognition/linux_confirmation/" + FINAL_NAME, **final},
        "data": {"cases": 32, "kernel_repeats": 128, "rounds": 5,
                 "training_use": False, "independent_machine_confirmation": True,
                 "independent_source_confirmation": False},
        "environment": summary["environment"],
        "input": summary["input"],
        "timing": summary["summaries"],
        "semantic_mismatches": 0,
        "criteria": {"safety_met": True, "independent_machine_confirmation": True,
                     "profitability_met": summary["summaries"]["confirmation_passed"],
                     "production_promotion": False},
        "lifecycle": {key: final[key] for key in (
            "create_requests_this_authorization", "automatic_replacement_queued",
            "owned_pod_absent_verified", "elapsed_since_create_seconds",
            "estimated_compute_cost_usd", "total_cost_cap_usd")},
        "interpretation": "Linux preserved exactness but measured 0.929x for one pass versus no rewrite, so the small Windows gain did not independently confirm.",
    }
    target = DOCS / MACHINE
    if target.exists():
        raise SystemExit("refusing D8 registration: machine summary already exists")
    target.write_text(json.dumps(machine, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                      encoding="utf-8")

    data = load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])] != [f"R{i:02d}" for i in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer contains exact R01-R18 and eight applications")
    by_id = {track["id"]: track for track in data["tracks"]}
    for track_id, (reason, next_experiment) in UPDATES.items():
        track = by_id[track_id]
        if any(item.get("report") == REPORT for item in track["results"]):
            raise SystemExit(f"D8 already registered for {track_id}")
        track["status"] = "measured"
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        track["results"].append({"report": REPORT, "machine_summary": MACHINE, "scope": reason})
    hardware = next(item for item in data["applications"]
                    if item["name"] == "Hardware verification/design")
    hardware["results"].append({"report": REPORT, "machine_summary": MACHINE,
        "scope": "Frozen Linux confirmation preserved all exact outputs but measured one pass at 0.929x versus no rewrite; unconditional promotion was refused."})
    data["milestones"]["D"] = "D8 frozen Linux machine confirmation complete; exactness passed and profitability failed"
    data["updated"] = "2026-08-29"
    REGISTER.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "d8_tracks": sorted(UPDATES), "confirmation_passed": False}))


if __name__ == "__main__":
    main()
