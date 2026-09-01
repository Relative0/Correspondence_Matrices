"""Register the verified C21 task-matched exact GF(2) method table."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c21-task-matched-gf2-table-windows-20260831-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C21_TASK_MATCHED_GF2_METHOD_TABLE_2026_08_31.md"
MACHINE = "learning_milestone_c21_task_matched_gf2_method_table_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def upsert(container: dict, scope: str) -> None:
    value = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    rows = [row for row in container["results"] if row.get("report") == REPORT]
    if len(rows) > 1:
        raise SystemExit("duplicate C21 registration")
    if rows:
        rows[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verify = load(RUN / "independent_verification.json")
    dataset_verify = load(DOCS / "c21_decomposition_table_dataset_verification.json")
    summary = result["summary"]
    packed = summary["methods"]["source_packed_anf"]
    screened = summary["methods"]["cm_screened"]
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("measurement_rows") != 3360
        or result.get("memory_measurement_rows") != 84
        or result.get("semantic_or_artifact_mismatches") != 0
        or summary.get("exactness_gate") is not True
        or summary.get("best_fixed_method") != "source_packed_anf"
        or result["claims"].get("same_requested_artifact") is not True
        or result["claims"].get("proposal_is_not_certificate") is not True
        or result["claims"].get("fresh_confirmation") is not False
        or result["claims"].get("production_promotion") is not False
        or verify.get("status") != "verified"
        or verify.get("contracts_checked") != 96
        or verify.get("measurement_rows_checked") != 3360
        or verify.get("summary_recomputed") is not True
        or dataset_verify.get("status") != "verified"
        or dataset_verify.get("cases_replayed") != 96
    ):
        raise SystemExit("refusing C21 registration: evidence incomplete")
    machine = {
        "schema": "crse-learning-milestone-c21-task-matched-gf2-method-table-summary/v1",
        "date": "2026-08-31",
        "status": "retrospective_task_matched_exact_table_verified",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "dataset": result["dataset"],
        "methods": list(summary["methods"]),
        "measurement_rows": result["measurement_rows"],
        "memory_measurement_rows": result["memory_measurement_rows"],
        "summary": summary,
        "verification": {
            "path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace("\\", "/"),
            **verify,
        },
        "dataset_verification": {
            "path": "docs/recognition/c21_decomposition_table_dataset_verification.json",
            **dataset_verify,
        },
        "semantic_or_artifact_mismatches": 0,
        "runpod": result["runpod"],
        "fresh_confirmation": False,
        "production_promotion": False,
        "interpretation": (
            f"All seven methods delivered the same exhaustive-best artifact. Packed source ANF "
            f"was the fastest fixed path at {packed['aggregate_speedup_over_exhaustive']:.3f}x "
            f"over exhaustive and {packed['aggregate_speedup_over_screened']:.3f}x over screened "
            f"CM; screened CM itself reached {screened['aggregate_speedup_over_exhaustive']:.3f}x. "
            f"Only {summary['oracle_headroom_over_best_fixed']:.3f}x per-case oracle headroom "
            "remains before routing cost. The table is retrospective and one-machine."
        ),
    }
    write(DOCS / MACHINE, machine)

    data = load(REGISTER)
    if (
        [row["id"] for row in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
        or len(data.get("applications", [])) != 8
    ):
        raise SystemExit("refusing C21 update: 18-track or 8-application shape changed")
    tracks = {row["id"]: row for row in data["tracks"]}
    scope = (
        "C21 compared seven exact methods under one exhaustive-best GF(2) artifact contract on 96 "
        "LogikBench cones. Packed source ANF was narrowly best at 3.007x over exhaustive; screened "
        "CM reached 2.988x, fresh BDD was negative, and only 1.059x oracle routing headroom remains."
    )
    for track_id in ("R01", "R06", "R07", "R11", "R13", "R16", "R18"):
        upsert(tracks[track_id], scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = scope
    tracks["R01"]["next_experiment"] = (
        "Add packed source ANF as an opt-in exact representation arm with screened and exhaustive fallback."
    )
    tracks["R06"]["next_experiment"] = (
        "Freeze a new source-family decomposition table and repeat the unchanged methods on a second CPU machine."
    )
    tracks["R07"]["next_experiment"] = (
        "Retain fresh BDD as a negative control; test resident BDD only for repeated-query task contracts."
    )
    tracks["R11"]["next_experiment"] = (
        "Use packed source ANF as an exact teacher/input path without treating its proposal as a certificate."
    )
    tracks["R13"]["next_experiment"] = (
        "Do not resume neural routing until fresh data shows headroom materially above the 1.059x retrospective oracle."
    )
    tracks["R16"]["next_experiment"] = (
        "Charge source representation, proposal, completion, exact checking, cleanup, and fallback in every future table."
    )
    tracks["R18"]["next_experiment"] = (
        "Keep exhaustive, screened, fresh BDD, all-abstain structural, and no-pruning proposal paths as controls."
    )
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    upsert(hardware, scope)
    data["milestones"]["F"] = (
        "C21/F2 completes the first task-matched exact GF(2) method table: packed source ANF and "
        "screened CM lead; proposal routing and fresh BDD do not; fresh-source replication remains"
    )
    data["updated"] = "2026-08-31"
    write(REGISTER, data)
    print(json.dumps({
        "tracks": len(data["tracks"]),
        "applications": len(data["applications"]),
        "updated_tracks": ["R01", "R06", "R07", "R11", "R13", "R16", "R18"],
        "milestone": "C21/F2",
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
