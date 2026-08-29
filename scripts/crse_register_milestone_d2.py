"""Record Milestone D2 while preserving exact R01-R18 and all applications."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs" / "recognition" / "experiment_register.json"
REPORT = "PROVED_RULE_MILESTONE_D2_2026_08_29.md"
MACHINE = "proved_rule_milestone_d2_results.json"

UPDATES = {
    "R03": ("measured",
        "A fixed compiled matcher now recognizes an exhaustively proved AIG-XOR macro at structurally equal metavariable bindings. It applied exactly at 128 generated sites and five internal sites in two evaluation-only EPFL cones.",
        "Add a second independently proved mux or factoring macro and measure interactions and deterministic priority."),
    "R04": ("measured",
        "One universal Boolean proof replaced per-instance explicit-CM proof. Warm compiled reuse was 2.09-2.91x faster end to end than per-site CM proof on generated batches, but remained slower than no rewrite, so no scheduler is promoted.",
        "Measure the fixed rule in related DAG versions with structural match caching, changed-cone invalidation, and a no-rewrite control."),
    "R05": ("measured",
        "The first generalized rule boundary is implemented: exhaustive Boolean metavariable evidence, strict hashed inert artifact, repeated-binding side conditions, and a fixed non-executable matcher. Rule discovery itself remains planned.",
        "Add bounded duplicate/overlap/conflict checks for a two-rule pack before attempting any learned rule proposal."),
    "R16": ("measured",
        "Proof, artifact load, matcher, candidate, per-instance CM verification, CSE build and kernel costs are separated. The one-time proof-plus-compile cost was 0.469 ms and observed break-even versus repeated CM proof was one application.",
        "Cache structural UIDs and match results across two related DAG versions and charge invalidation inside the timed arm."),
    "R18": ("measured",
        "Sixteen binding-corrupted near matches produced zero false matches. No-rewrite was 2.33-2.43x faster than warm compiled matching on generated batches and 2.75x faster on EPFL, retaining a clear profitability negative control.",
        "Add dense no-match and overlapping-match adversarial cases plus explicit matcher resource-limit tests."),
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
            raise SystemExit(f"Milestone D2 already registered for {track['id']}")
        status, reason, next_experiment = UPDATES[track["id"]]
        track["status"] = status
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        track["results"].append({**result, "scope": reason})
    hardware = next(application for application in data["applications"]
                    if application["name"] == "Hardware verification/design")
    if any(item.get("report") == REPORT for item in hardware["results"]):
        raise SystemExit("Milestone D2 already registered for hardware application")
    hardware["status"] = "measured"
    hardware["results"].append({**result,
        "scope": "The proved matcher found five internal AIG-XOR sites in two of 12 evaluation-only EPFL cones with zero output errors; matching still lost to the no-rewrite CSE control."})
    data["updated"] = "2026-08-29"
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "updated_tracks": sorted(UPDATES), "hardware_status": hardware["status"]}))


if __name__ == "__main__":
    main()
