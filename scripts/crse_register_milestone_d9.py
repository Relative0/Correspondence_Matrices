"""Register verified CRSE Milestone D9 without dropping any track."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
RUN = DOCS / "runs" / "natural-profitability-policy-20260829-003"
VERIFY = DOCS / "verification" / "natural-profitability-policy-20260829-003.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "NATURAL_PROFITABILITY_POLICY_MILESTONE_D9_2026_08_29.md"
MACHINE = "natural_profitability_policy_milestone_d9_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


UPDATES = {
    "R01": ("A frozen calibrated structural policy was evaluated on 33 circuit-disjoint BLIF workloads; it safely selected no rewrite for every workload.",
            "Only revisit learned rewrite routing after an independently sourced corpus shows measured positive headroom for at least one rule region."),
    "R03": ("The proved pack transferred exactly to optimized BLIF/SOP cones: 43 common-factor applications reduced evaluation CSE operations from 478 to 437 with zero semantic mismatches.",
            "Seek an independently sourced natural factoring or mux corpus before extending the proved pack."),
    "R04": ("The separately trained frozen policy abstained on all 33 evaluation workloads; unconditional one pass measured 0.429x and the charged gate measured 0.982x versus no rewrite.",
            "Add a compile-time no-op bypass and seek larger motifs with measured rewrite headroom before fitting a richer scheduler."),
    "R13": ("The bounded cost tree collapsed to a conservative leaf because normalized training cost was 1.000 for no rewrite versus 3.141 for one pass.",
            "Compare an analytic break-even rule only after a training source contains both profitable and unprofitable exact rewrite regions."),
    "R16": ("Machine-calibrated inference remained cheap but nonzero; the all-abstain gate was 1.8% slower while unconditional rewriting was about 2.33 times slower on the new BLIF slice.",
            "Compile constant policies away and measure larger independently sourced cones where operation-count reduction can amortize rewrite and rebuild cost."),
    "R17": ("The frozen policy refused 23 in-range cases for insufficient gain and abstained on 10 out-of-range cases; all 33 decisions matched the faster fixed arm.",
            "Test calibration-identity mismatch and positive/negative decisions on an independent benchmark family with no post-freeze tuning."),
    "R18": ("The new BLIF evaluation retained unconditional one pass as a negative control: it found exact structure but measured only 0.429x the no-rewrite speed.",
            "Keep no rewrite and unconditional one pass as mandatory controls; do not claim value from structural reduction alone."),
}


def main() -> None:
    summary = load(RUN / "summary.json")
    verification = load(VERIFY)
    if (summary.get("status") != "complete" or summary.get("semantic_mismatches") != 0
            or verification.get("status") != "pass"
            or summary.get("criteria", {}).get("profitability_met") is not False
            or summary.get("criteria", {}).get("production_promotion") is not False):
        raise SystemExit("refusing D9 registration: evidence or negative criteria disagree")
    evaluation = summary["summaries"]["evaluation"]
    machine = {
        "schema": "crse-natural-profitability-policy-milestone-d9-summary/v1",
        "date": "2026-08-29", "status": "complete",
        "run": "docs/recognition/runs/natural-profitability-policy-20260829-003",
        "report": REPORT,
        "verification": {"path": "docs/recognition/verification/natural-profitability-policy-20260829-003.json",
                         **verification},
        "data": {"training_cases": 10, "validation_cases": 2, "evaluation_cases": 11,
                 "evaluation_workloads": 33, "measurement_rows": 501,
                 "semantic_checks": summary["semantic_checks"],
                 "prior_d5_d8_structural_overlap_count": summary["prior_d5_d8_structural_overlap_count"],
                 "circuit_disjoint": True, "new_blif_representation": True,
                 "independent_benchmark_family": False},
        "policy": {"sha256": verification["policy_sha256"],
                   "apply_count": evaluation["gate_apply_count"],
                   "abstain_count": evaluation["gate_abstain_count"],
                   "decision_reasons": evaluation["decision_reasons"]},
        "timing": {key: evaluation[key] for key in (
            "frozen_gate_speedup_over_no_rewrite", "one_pass_speedup_over_no_rewrite",
            "frozen_gate_regret_fraction", "median_cell_totals_ns")},
        "semantic_mismatches": 0, "criteria": summary["criteria"],
        "interpretation": "The leakage-controlled gate and abstention contract passed, but the learned policy found no profitable rewrite region and production promotion remains refused.",
    }
    target = DOCS / MACHINE
    if target.exists():
        raise SystemExit("refusing D9 registration: machine summary already exists")
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
            raise SystemExit(f"D9 already registered for {track_id}")
        track["status"] = "measured"
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        track["results"].append({"report": REPORT, "machine_summary": MACHINE, "scope": reason})
    hardware = next(item for item in data["applications"]
                    if item["name"] == "Hardware verification/design")
    hardware["results"].append({"report": REPORT, "machine_summary": MACHINE,
        "scope": "A calibrated frozen policy was exact on circuit-disjoint optimized BLIF cones but abstained everywhere; unconditional one pass measured 0.429x and promotion was refused."})
    data["milestones"]["D"] = "D9 frozen calibrated natural profitability policy complete; safety/abstention passed and profitability failed"
    data["updated"] = "2026-08-29"
    REGISTER.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "d9_tracks": sorted(UPDATES), "profitability_met": False,
                      "production_promotion": False}))


if __name__ == "__main__":
    main()
