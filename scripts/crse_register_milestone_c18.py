"""Register the verified C18 independent VTR exact-dispatch transfer."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c18-independent-gf2-transfer-windows-20260831-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C18_INDEPENDENT_GF2_TRANSFER_2026_08_31.md"
MACHINE = "learning_milestone_c18_independent_gf2_transfer_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def upsert(container: dict, scope: str) -> None:
    value = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    rows = [row for row in container["results"] if row.get("report") == REPORT]
    if len(rows) > 1:
        raise SystemExit("duplicate C18 registration")
    if rows:
        rows[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result, verify = load(RUN / "results.json"), load(RUN / "independent_verification.json")
    corpus, dataset = (load(DOCS / "c18_independent_corpus_verification.json"),
                       load(DOCS / "c18_independent_cone_dataset.json"))
    if (not (DOCS / REPORT).is_file() or result.get("status") != "complete"
            or result.get("measurement_rows") != 292
            or result.get("semantic_or_artifact_mismatches") != 0
            or result["summary"].get("exactness_gate") is not True
            or result["summary"].get("local_research_gate") is not False
            or result["claims"].get("single_round_timing") is not True
            or result["claims"].get("production_promotion") is not False
            or verify.get("status") != "verified" or verify.get("functional_cases_replayed") != 73
            or corpus.get("status") != "verified" or corpus.get("cases_replayed") != 73
            or corpus.get("c16_truth_overlaps") != 0 or len(dataset.get("cases", [])) != 73
            or dataset["provenance"].get("policy_refit_allowed") is not False):
        raise SystemExit("refusing C18 registration: evidence incomplete")
    machine = {
        "schema": "crse-learning-milestone-c18-independent-gf2-transfer-summary/v1",
        "date": "2026-08-31", "status": "independent_exact_transfer_timing_scout_complete",
        "report": REPORT, "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "corpus": {"dataset": "docs/recognition/c18_independent_cone_dataset.json",
                   "source_inventory": "docs/recognition/c18_independent_corpus_source_inventory.json",
                   "source_verification": "docs/recognition/c18_independent_corpus_verification.json",
                   "cases": 73, "source_files": 10, "c16_truth_overlaps": 0},
        "verification": {"path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace("\\", "/"), **verify},
        "dataset": result["dataset"], "decision_counts": result["decision_counts"],
        "measurement_rows": 292, "summary": result["summary"],
        "semantic_or_artifact_mismatches": 0, "runpod": result["runpod"],
        "production_promotion": False,
        "interpretation": (
            "The unchanged exact dispatcher transferred to 73 VTR cones with zero mismatches "
            "and 8.378x aggregate speedup. The 1.324x slow-tail gate passed, but an n=4 DES "
            "case measured 0.621x; single-round timing and failed minimum no-regret prevent promotion."
        ),
    }
    write(DOCS / MACHINE, machine)
    data = load(REGISTER)
    if ([row["id"] for row in data.get("tracks", [])] !=
            [f"R{index:02d}" for index in range(1, 19)] or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing C18 update: 18-track or 8-application shape changed")
    tracks = {row["id"]: row for row in data["tracks"]}
    scope = (
        "The unchanged exact C17 dispatcher transferred to 73 evaluation-only VTR BLIF cones "
        "with zero mismatches and 8.378x aggregate speedup. The 1.324x slow-tail passed, but a "
        "0.621x n=4 minimum and single-round timing keep production disabled."
    )
    for track_id in ("R01", "R06", "R16", "R17", "R18"):
        upsert(tracks[track_id], scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = scope
    tracks["R01"]["next_experiment"] = "Add a frozen cheap work estimate for mixed n=4 tasks, with unchanged exact fallback."
    tracks["R06"]["next_experiment"] = "Repeat the 73-cone VTR slice for multiple rounds and freeze a LogikBench RTL-to-BLIF transform."
    tracks["R16"]["next_experiment"] = "Charge a direct call-site bypass and test features that separate profitable and unprofitable n=4 cones."
    tracks["R17"]["next_experiment"] = "Do not refit on C18; validate any new policy on a separately frozen source split."
    tracks["R18"]["next_experiment"] = "Retain the 0.621x DES and 0.821x seq cones as mandatory no-regret controls."
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    upsert(hardware, scope)
    data["milestones"]["C"] = (
        "C18 verifies exact independent VTR transfer and strong aggregate screened speedup; mixed "
        "small-case profitability and repeated/second-machine confirmation remain"
    )
    data["updated"] = "2026-08-31"
    write(REGISTER, data)
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "updated_tracks": ["R01", "R06", "R16", "R17", "R18"],
                      "milestone": "C18", "production_promotion": False}, sort_keys=True))


if __name__ == "__main__":
    main()
