"""Register verified C4 direct-cut evidence while preserving all tracks."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
RUN = DOCS / "runs" / "natural-cut-ranking-20260829-001"
VERIFY = DOCS / "verification" / "natural-cut-ranking-20260829-001.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C4_DIRECT_CUT_RANKING_2026_08_29.md"
MACHINE = "learning_milestone_c4_direct_cut_ranking_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


UPDATES = {
    "R02": (
        "Direct canonical variable-cut supervision was measured on 94 exact same-circuit EPFL pairs; held-out cut recovery remained unstable.",
        "Replace global cut logits with permutation-equivariant per-variable scoring before any second-family run.",
    ),
    "R03": (
        "Graph proposals now name a complete variable partition and pay a fresh exact witness; all unsafe or incorrect partitions fall back unchanged.",
        "Measure a source-level interaction approximation and node-level proposal only if it can reduce complete truth construction.",
    ),
    "R11": (
        "The auxiliary target is now the complete canonical row-membership vector rather than 45 independently thresholded interaction edges.",
        "Attach supervision to variable-node embeddings and retain complement-invariant/permutation-equivariant cut semantics.",
    ),
    "R12": (
        "Direct-cut and cut-plus-ranking GNNs were trained under two seeds; neither met held-out classification or exact-partition criteria.",
        "Use variable-conditioned readout instead of another global-embedding capacity increase.",
    ),
    "R13": (
        "Same-pair margin learning reached 0.833-0.889 ranking accuracy on confirmatory circuits but only 0.375-0.500 on the held-out square circuit.",
        "Keep pair batches and add per-variable equivariance; do not retune thresholds on the retained test circuit.",
    ),
    "R16": (
        "End-to-end graph construction, inference and exact acceptance were charged; cut GNNs were 4.6-6.0x slower than exact ANF.",
        "Profile a deterministic source-level interaction approximation and require near-parity with exact ANF before expanding data.",
    ),
    "R17": (
        "Relative pair ordering transferred to some confirmatory circuits but absolute calibration and exact cuts did not transfer consistently to square.",
        "Freeze a node-level design on EPFL and require stable existing test performance before sealed independent-family evaluation.",
    ),
    "R18": (
        "Direct cut loss corrected the C3 decoder formulation but still yielded only 0.000-0.222 accepted-positive recall across graph arms and held-out splits.",
        "Retain this failure, exact ANF, abstention, and structural pair-ranker controls in the next architecture comparison.",
    ),
}


def main():
    summary = load(RUN / "summary.json")
    verification = load(VERIFY)
    expected_criteria = {
        "accepted_partition": False,
        "classification": False,
        "cost": False,
        "pair_ranking": False,
        "production_promotion": False,
        "ranking_improvement": False,
        "safety": True,
    }
    if (
        summary.get("status") != "complete"
        or verification.get("status") != "pass"
        or summary.get("criteria") != expected_criteria
        or summary.get("accepted_semantic_mismatches") != 0
    ):
        raise SystemExit("refusing C4 registration: verified evidence differs from reviewed result")

    machine = {
        "schema": "crse-learning-milestone-c4-direct-cut-ranking-summary/v1",
        "date": "2026-08-29",
        "status": "complete",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "verification": {"path": str(VERIFY.relative_to(ROOT)).replace("\\", "/"), **verification},
        "dataset": summary["dataset_audit"],
        "models": summary["model_cards"],
        "classification": summary["classification"],
        "pair_ranking": summary["pair_ranking"],
        "controls": summary["controls"],
        "cost_ratios": summary["cost_ratios"],
        "criteria": summary["criteria"],
        "accepted_semantic_mismatches": 0,
        "interpretation": (
            "Direct cut supervision and same-pair ranking did not transfer consistently to the held-out square circuit and remained slower than exact ANF. Node-level variable scoring is required before independent-family evaluation."
        ),
    }
    target = DOCS / MACHINE
    if target.exists():
        raise SystemExit("refusing C4 registration: machine summary already exists")
    target.write_text(json.dumps(machine, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")

    data = load(REGISTER)
    if (
        [track["id"] for track in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
        or len(data.get("applications", [])) != 8
    ):
        raise SystemExit("refusing update: register no longer contains exact R01-R18 and eight applications")
    by_id = {track["id"]: track for track in data["tracks"]}
    for track_id, (reason, next_experiment) in UPDATES.items():
        track = by_id[track_id]
        if any(item.get("report") == REPORT for item in track["results"]):
            raise SystemExit(f"C4 already registered for {track_id}")
        track["status"] = "measured"
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        track["results"].append({"report": REPORT, "machine_summary": MACHINE, "scope": reason})
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    hardware["results"].append({
        "report": REPORT,
        "machine_summary": MACHINE,
        "scope": "Direct variable-cut and same-circuit pair-ranking GNNs were exact-check safe but failed held-out transfer and cost criteria; no rewrite or learned recognizer was promoted.",
    })
    data["milestones"]["C"] = (
        "C4 direct-cut and matched-pair ranking complete; transfer, partition, ranking, improvement and cost criteria failed safely"
    )
    data["updated"] = "2026-08-29"
    REGISTER.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "tracks": len(data["tracks"]),
        "applications": len(data["applications"]),
        "c4_tracks": sorted(UPDATES),
        "models": len(summary["model_cards"]),
        "evaluation_rows": summary["row_count"],
        "production_promotion": False,
        "safety": True,
    }))


if __name__ == "__main__":
    main()
