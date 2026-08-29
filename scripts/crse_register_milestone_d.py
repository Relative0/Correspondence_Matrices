"""Record the measured Milestone D slice while preserving R01-R18 and all applications."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs" / "recognition" / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_D_2026_08_29.md"
MACHINE = "learning_milestone_d_results.json"

UPDATES = {
    "R01": ("measured",
        "A fitted task/query cost policy selected only exact backends. It improved partial restrictions by 1.654x on generated test and 1.530x on the nonoverlapping EPFL D slice, but slowed complete-vector requests; no policy is promoted.",
        "Add one bounded expression-size/tail-risk feature, freeze before evaluation, and replicate on a new natural source family."),
    "R03": ("measured",
        "The bounded exact candidate path now covers canonical affine, three-input mux and three-input majority roots. The retained run found and safely accepted only ten generated affine functions; no natural EPFL D candidate was found.",
        "Add provenance-reviewed natural mux/majority positives and compare a compiled structural matcher with per-instance CM detection."),
    "R04": ("negative-result",
        "A stop-versus-one-rewrite experiment accepted 100 exact workload instances with zero errors, but full CM detection and per-instance proof dominated every downstream saving (aggregate speedups about 0.03-0.24 versus the task rule).",
        "Prove one bounded rule over metavariables, compile a cheap matcher, and measure repeated applications without repeating the full instance proof."),
    "R06": ("negative-result",
        "Explicit dense CM construction, lookup and cofactoring were measured from the original expression. On EPFL D they achieved only 0.093-0.472x the task-rule speed across the four tasks; decomposition and already-materialized-CM contracts remain pending.",
        "Measure exact cofactor/block reuse when a CM is already present, then add one GF(2) or repeated-block decomposition control."),
    "R09": ("measured",
        "An exact per-request answer cache improved repeated-vector work by 1.435-1.452x across validation, test, confirmatory and EPFL D splits. Version identity, invalidation and cross-request sessions remain pending.",
        "Add a finite two-version workload with explicit cache identity, invalidation, serialized provenance and a localized change."),
    "R13": ("measured",
        "The method comparison now includes a fitted task/query cost table against a predeclared task rule and four exact backends. Gains were task-specific and routing overhead remained visible.",
        "Compare the cost table with one bounded expression-aware linear/ranking control under the same retained task rows."),
    "R16": ("measured",
        "Construction, routing, candidate, proof, kernel, cache and audit costs are separated. Cheap task routing helped restrictions/reuse, while complete-vector routing overhead and dense-CM construction remained material.",
        "Batch task decisions and test a zero-allocation compiled rule matcher before any larger neural inference path."),
    "R18": ("measured",
        "Dense CM construction and per-instance rewrite proof serve as retained overhead controls: both lost to simpler exact paths at this bounded scale while preserving zero semantic errors.",
        "Add dense incompressible/no-sharing functions and raw packed primitive controls under the same four task contracts."),
}


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    if ([track["id"] for track in data.get("tracks", [])] != [f"R{i:02d}" for i in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer contains exact R01-R18 and eight applications")
    result = {"report": REPORT, "machine_summary": MACHINE}
    for track in data["tracks"]:
        if track["id"] not in UPDATES:
            continue
        if any(item.get("report") == REPORT for item in track["results"]):
            raise SystemExit(f"Milestone D already registered for {track['id']}")
        status, reason, next_experiment = UPDATES[track["id"]]
        track["status"] = status
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        track["results"].append({**result, "scope": reason})
    hardware = next(application for application in data["applications"]
                    if application["name"] == "Hardware verification/design")
    if any(item.get("report") == REPORT for item in hardware["results"]):
        raise SystemExit("Milestone D already registered for hardware application")
    hardware["status"] = "measured"
    hardware["results"].append({**result,
        "scope": "Four exact task contracts measured on 12 evaluation-only EPFL cones selected after excluding every Milestone-C record ID; all outputs verified, no natural root motif found, and no backend promoted."})
    data["updated"] = "2026-08-29"
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "updated_tracks": sorted(UPDATES), "hardware_status": hardware["status"]}))


if __name__ == "__main__":
    main()
