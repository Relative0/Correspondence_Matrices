"""Register the verified C20 compiled-policy VTR tail milestone."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c20-compiled-policy-vtr-tail-windows-20260831-002"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C20_COMPILED_GF2_POLICY_VTR_TAIL_2026_08_31.md"
MACHINE = "learning_milestone_c20_compiled_gf2_policy_vtr_tail_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def upsert(container: dict, scope: str) -> None:
    value = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    rows = [row for row in container["results"] if row.get("report") == REPORT]
    if len(rows) > 1:
        raise SystemExit("duplicate C20 registration")
    if rows:
        rows[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result, verify = load(RUN / "results.json"), load(RUN / "independent_verification.json")
    summary = result["summary"]
    compiled = summary["methods"]["compiled_c19"]
    direct = summary["methods"]["direct_screened"]
    failed = load(DOCS / "runs/c20-compiled-policy-vtr-tail-windows-20260831-001/failure.json")
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("measurement_rows") != 396
        or result.get("semantic_or_artifact_mismatches") != 0
        or summary.get("functional_exactness") is not True
        or summary.get("research_gate") is not True
        or result["dataset"].get("retrospective") is not True
        or result["dataset"].get("policy_refit") is not False
        or result["policy"].get("compiled_mode") != "constant_leaf"
        or result["policy"].get("requires_features") is not False
        or result["claims"].get("fresh_confirmation") is not False
        or result["claims"].get("production_promotion") is not False
        or verify.get("status") != "verified"
        or verify.get("measurement_rows_checked") != 396
        or verify.get("summary_recomputed") is not True
        or failed.get("failed_before_measurements") is not True
    ):
        raise SystemExit("refusing C20 registration: evidence incomplete")
    machine = {
        "schema": "crse-learning-milestone-c20-compiled-gf2-policy-vtr-tail-summary/v1",
        "date": "2026-08-31",
        "status": "retrospective_repeated_tail_gate_passed",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "failed_attempt": "docs/recognition/runs/c20-compiled-policy-vtr-tail-windows-20260831-001/failure.json",
        "dataset": result["dataset"],
        "policy": result["policy"],
        "measurement_rows": result["measurement_rows"],
        "summary": summary,
        "verification": {
            "path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace("\\", "/"),
            **verify,
        },
        "semantic_or_artifact_mismatches": 0,
        "runpod": result["runpod"],
        "fresh_confirmation": False,
        "production_promotion": False,
        "interpretation": (
            f"Nine balanced rounds on all 11 C18 n=3-4 controls gave the compiled frozen policy "
            f"{compiled['aggregate_speedup_over_exhaustive']:.3f}x aggregate and "
            f"{compiled['minimum_case_speedup_over_exhaustive']:.3f}x minimum speedup. Direct "
            f"screened reached a {direct['minimum_case_speedup_over_exhaustive']:.3f}x minimum, "
            "so the prior single-round 0.716x outlier was not reproduced. The evidence is "
            "retrospective and same-machine, so production remains disabled."
        ),
    }
    write(DOCS / MACHINE, machine)

    data = load(REGISTER)
    if (
        [row["id"] for row in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
        or len(data.get("applications", [])) != 8
    ):
        raise SystemExit("refusing C20 update: 18-track or 8-application shape changed")
    tracks = {row["id"]: row for row in data["tracks"]}
    scope = (
        "C20 constant-folded the frozen screened leaf and repeated all 11 C18 n=3-4 VTR controls "
        "for nine balanced rounds. Exact compiled selection reached 1.760x aggregate / 1.463x "
        "minimum; the prior one-round regression was not reproduced. Evidence is retrospective."
    )
    for track_id in ("R01", "R06", "R16", "R17", "R18"):
        upsert(tracks[track_id], scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = scope
    tracks["R01"]["next_experiment"] = (
        "Measure the compiled frozen policy on a new source-cluster confirmation slice and compare exact task-matched baselines."
    )
    tracks["R06"]["next_experiment"] = (
        "Repeat the frozen C19/C20 package on a second CPU machine without refitting."
    )
    tracks["R16"]["next_experiment"] = (
        "Integrate constant-leaf compilation behind an opt-in exact dispatcher boundary with shadow verification."
    )
    tracks["R17"]["next_experiment"] = (
        "Do not reuse retrospective C18 as fresh promotion evidence; freeze a new source-cluster slice first."
    )
    tracks["R18"]["next_experiment"] = (
        "Keep nine-round balanced timing and the direct screened arm as mandatory future tail controls."
    )
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    upsert(hardware, scope)
    data["milestones"]["C"] = (
        "C20 compiles the frozen exact screened leaf and clears the repeated retrospective VTR "
        "small-support tail; fresh-source and second-machine confirmation remain"
    )
    data["updated"] = "2026-08-31"
    write(REGISTER, data)
    print(json.dumps({
        "tracks": len(data["tracks"]),
        "applications": len(data["applications"]),
        "updated_tracks": ["R01", "R06", "R16", "R17", "R18"],
        "milestone": "C20",
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
