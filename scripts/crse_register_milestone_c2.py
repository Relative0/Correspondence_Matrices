"""Register verified CRSE C2 evidence without dropping any research track."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
RUN = DOCS / "runs" / "variable-decomposition-20260829-001"
VERIFY = DOCS / "verification" / "variable-decomposition-20260829-001.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C2_2026_08_29.md"
MACHINE = "learning_milestone_c2_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


UPDATES = {
    "R02": ("Balanced GF(2) row/column decomposition is now an exact recognized subclass over variable-size CMs. Learned classification did not transfer beyond chance on n=10.",
            "Acquire an independently sourced dataset containing both natural positive and negative decomposable functions before fitting another classifier."),
    "R03": ("Positive proposals now carry canonical exact row/column factor witnesses; every accepted proposal was recomposed and checked with zero mismatches.",
            "Compile a source-level replacement only after a graph proposal generalizes on independently sourced positives."),
    "R06": ("An executable cofactor/decomposition teacher now detects M[r,c]=g[r] XOR h[c], retains exact factors, and checks distance-one controls across n=4,6,8,10.",
            "Extend the exact teacher to discovered variable partitions, repeated/complementary blocks, and AND/GF(2) rank controls."),
    "R11": ("CM supervision now includes exact cofactor relations, canonical factor witnesses, and functional distance one rather than affine membership alone.",
            "Train auxiliary residual/factor heads only after adding source-independent positives; keep exact witness verification mandatory."),
    "R12": ("Variable matrix MLP, shared multiscale CM, variable graph GNN, and fused models were matched across two seeds. None met the sealed representation or n=10 transfer criteria.",
            "Use multiple training encodings and a source-independent natural-positive family before increasing model capacity."),
    "R13": ("The matched experiment adds validation-only calibration and size curriculum n=4/6/8 to n=10, but all learned arms failed the transfer criterion.",
            "Add a deterministic cofactor-signature classifier and one linear auxiliary-target baseline before another neural run."),
    "R16": ("Representation construction, inference, exact-check, training, safe-load, and exact-control costs were retained for eight trained models.",
            "Measure graph shortlist plus exact verification only where a positive rewrite has proven operation-count headroom."),
    "R17": ("Validation-only thresholds transferred poorly: EPFL specificity varied from 0.000 to 0.844 and the frozen source had no target positives.",
            "Require a new source family with natural positives and negatives; freeze calibration before its one-pass evaluation."),
    "R18": ("One-cell near-decompositions defeated the CM learners and held-out syntax defeated graph/fused models despite zero training loss; these failures are retained.",
            "Keep exact detector and always-abstain controls, then add dense multi-cell and structure-matched hard negatives."),
}


def main():
    summary = load(RUN / "summary.json")
    verification = load(VERIFY)
    if (summary.get("status") != "complete" or verification.get("status") != "pass"
            or summary.get("accepted_semantic_mismatches") != 0 or summary.get("witness_mismatches") != 0
            or summary.get("criteria", {}).get("representation_signal") is not False
            or summary.get("criteria", {}).get("size_transfer") is not False
            or summary.get("criteria", {}).get("safety") is not True
            or summary.get("criteria", {}).get("natural_positive_evidence") is not False):
        raise SystemExit("refusing C2 registration: verified evidence or negative criteria disagree")
    selected = {}
    for key, values in summary["classification"].items():
        if key.endswith(("/test", "/confirmatory", "/epfl")):
            selected[key] = {field: values[field] for field in
                             ("cases", "balanced_accuracy", "specificity", "brier_score", "median_total_ns")}
    machine = {
        "schema": "crse-learning-milestone-c2-summary/v1", "date": "2026-08-29", "status": "complete",
        "run": "docs/recognition/runs/variable-decomposition-20260829-001", "report": REPORT,
        "verification": {"path": "docs/recognition/verification/variable-decomposition-20260829-001.json",
                         **verification},
        "data": {"generated_functions": 160, "generated_parent_pairs": 80, "training": 96,
                 "validation": 24, "test": 24, "confirmatory_n10": 16, "natural_epfl_n8": 32,
                 "training_sizes": [4, 6, 8], "confirmatory_sizes": [10],
                 "natural_positive_count": summary["epfl_source"]["natural_positive_count"]},
        "models": summary["model_cards"], "classification": selected, "controls": summary["controls"],
        "accepted_semantic_mismatches": 0, "witness_mismatches": 0,
        "criteria": summary["criteria"],
        "interpretation": "The exact variable-size decomposition teacher and safety boundary passed. Learned representations failed the sealed representation and n=10 transfer criteria; the natural slice supports specificity only.",
    }
    target = DOCS / MACHINE
    if target.exists():
        raise SystemExit("refusing C2 registration: machine summary already exists")
    target.write_text(json.dumps(machine, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")

    data = load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer contains exact R01-R18 and eight applications")
    by_id = {track["id"]: track for track in data["tracks"]}
    for track_id, (reason, next_experiment) in UPDATES.items():
        track = by_id[track_id]
        if any(item.get("report") == REPORT for item in track["results"]):
            raise SystemExit(f"C2 already registered for {track_id}")
        track["status"] = "measured"
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        track["results"].append({"report": REPORT, "machine_summary": MACHINE, "scope": reason})
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    hardware["results"].append({"report": REPORT, "machine_summary": MACHINE,
        "scope": "A frozen 32-function EPFL n=8 slice was checked for balanced XOR decomposition. All were negative, so only specificity and exact rejection were measured; no natural-positive transfer claim is made."})
    data["milestones"]["C"] = "C2 variable-size exact decomposition teacher complete; neural representation and n=10 transfer criteria failed safely"
    data["updated"] = "2026-08-29"
    REGISTER.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "c2_tracks": sorted(UPDATES), "representation_signal": False,
                      "size_transfer": False, "safety": True}))


if __name__ == "__main__":
    main()
