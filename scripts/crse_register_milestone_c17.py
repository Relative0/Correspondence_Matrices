"""Register the independently verified local C17 exact dispatcher study."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c17-gf2-task-dispatcher-windows-20260831-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C17_GF2_TASK_DISPATCHER_2026_08_31.md"
MACHINE = "learning_milestone_c17_gf2_task_dispatcher_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def upsert(container: dict, scope: str) -> None:
    value = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    matches = [row for row in container["results"] if row.get("report") == REPORT]
    if len(matches) > 1:
        raise SystemExit("duplicate C17 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    policy = load(RUN / "policy.json")
    if (not (DOCS / REPORT).is_file() or result.get("status") != "complete"
            or result.get("measurement_rows") != 320
            or result.get("semantic_or_artifact_mismatches") != 0
            or result["summary"].get("exactness_gate") is not True
            or result["summary"].get("local_research_gate") is not False
            or result["claims"].get("production_promotion") is not False
            or result.get("decision_counts") != {
                "advice_globally_disabled": 40, "c16_screened_tail": 35,
                "tiny_case_bypass": 5}
            or verification.get("status") != "verified"
            or verification.get("functional_cases_replayed") != 40
            or verification.get("measurement_rows_checked") != 320
            or policy.get("production_promotion") is not False):
        raise SystemExit("refusing C17 registration: evidence incomplete")
    machine = {
        "schema": "crse-learning-milestone-c17-gf2-task-dispatcher-summary/v1",
        "date": "2026-08-31", "status": "locally_measured_research_gate_failed",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "verification": {"path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace("\\", "/"), **verification},
        "policy_sha256": policy["policy_sha256"], "dataset": result["dataset"],
        "decision_counts": result["decision_counts"], "measurement_rows": 320,
        "summary": result["summary"], "semantic_or_artifact_mismatches": 0,
        "failed_attempt": "docs/recognition/runs/c17-gf2-task-dispatcher-windows-20260831-attempt1-timeout",
        "runpod": result["runpod"], "production_promotion": False,
        "interpretation": (
            "The exact dispatcher preserved all artifacts and achieved 3.831x aggregate "
            "speedup, while advice-off matched direct exhaustive cost. Its 0.769x slow-tail "
            "and 0.597x minimum small case failed the no-regret gate; C18 independent transfer "
            "and a lower-level tiny-task bypass are required."
        ),
    }
    write(DOCS / MACHINE, machine)

    data = load(REGISTER)
    if ([row["id"] for row in data.get("tracks", [])] !=
            [f"R{index:02d}" for index in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing C17 update: 18-track or 8-application shape changed")
    tracks = {track["id"]: track for track in data["tracks"]}
    scope = (
        "A frozen platform-bound dispatcher selected only exact exhaustive or screened CM/GF(2) "
        "arms. All 40 functional and 320 measured rows were exact; aggregate speedup was 3.831x, "
        "but 0.769x slow-tail and 0.597x minimum-case results refused production promotion."
    )
    for track_id in ("R01", "R06", "R16", "R17", "R18"):
        upsert(tracks[track_id], scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = scope
    tracks["R01"]["next_experiment"] = "Evaluate the frozen C17 policy without refitting on the C18 independent circuit corpus."
    tracks["R06"]["next_experiment"] = "Measure exact screened decomposition on independent VTR and LogikBench-derived cones."
    tracks["R16"]["next_experiment"] = "Move the n<=3 bypass below dispatcher construction and charge its complete call boundary."
    tracks["R17"]["next_experiment"] = "Retain platform abstention and require independent-source and second-machine transfer."
    tracks["R18"]["next_experiment"] = "Retain the n=2 0.597x and n=3 0.769x cases as mandatory no-regret controls."
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    upsert(hardware, scope)
    data["milestones"]["C"] = (
        "C17 exact task dispatch is verified and aggregate-profitable on reused engineering data; "
        "small-case no-regret fails, so C18 independent transfer and a lower-level bypass remain"
    )
    data["updated"] = "2026-08-31"
    write(REGISTER, data)
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "updated_tracks": ["R01", "R06", "R16", "R17", "R18"],
                      "milestone": "C17", "production_promotion": False}, sort_keys=True))


if __name__ == "__main__":
    main()
