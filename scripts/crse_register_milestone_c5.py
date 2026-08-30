"""Register verified C5 evidence without dropping research tracks."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
RUN = DOCS / "runs" / "natural-variable-cut-20260829-001"
VERIFY = DOCS / "verification" / "natural-variable-cut-20260829-001.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C5_VARIABLE_CONDITIONED_CUT_2026_08_29.md"
MACHINE = "learning_milestone_c5_variable_conditioned_cut_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


UPDATES = {
    "R01": ("An exact bounded symbolic-ANF source-DAG control now avoids initial truth-vector construction and retains proof-compatible partitions.",
        "Implement bitset monomial sets, product caching and an operation-budget fallback to truth-vector ANF."),
    "R02": ("Bidirectional per-variable cut scoring improved confirmatory recovery but held-out square recall remained only 0.125-0.188.",
        "Pause neural tuning until a representation change or more training circuits are available."),
    "R03": ("Exact source symbolic ANF provides canonical partitions before CM construction and still passes the same exact witness boundary.",
        "Build a bounded hybrid that switches to truth-vector ANF before symbolic-product tails dominate."),
    "R06": ("Source-DAG GF(2) polynomial propagation exactly reproduced all 188 scalar truth tables and arbitrary partitions.",
        "Optimize polynomial representation and characterize term/product complexity by circuit and variable count."),
    "R11": ("Cut supervision now attaches to context-rich variable nodes through one shared head with exact fixed-anchor permutation equivariance.",
        "Retain this architecture as the neural control; do not add capacity without more independent training circuits."),
    "R12": ("The 136,962-parameter variable-conditioned GNN reached 0.750-0.778 confirmatory BA but only 0.562-0.594 test BA.",
        "Prefer the no-ranking variable-conditioned arm if neural work resumes; the ranking loss reduced exact acceptance."),
    "R13": ("Non-anchor variable-permutation audits had exactly zero error, while same-pair ranking still failed consistent held-out transfer.",
        "Keep equivariance audits and separate ranking from cut optimization in any later study."),
    "R16": ("Safe learned paths were 6.3-9.2x slower than exact ANF. Symbolic source ANF was faster at the median but had a 63.7 ms confirmatory p95 tail.",
        "Measure cached bitset symbolic ANF with median, p95, maximum and explicit budget fallbacks."),
    "R17": ("Variable-conditioned readout improved confirmatory results but did not close the held-out circuit gap; no second-family run is justified yet.",
        "Require stable EPFL test recovery or a deterministic hybrid win before independent-family evaluation."),
    "R18": ("The conservative source approximation safely abstained everywhere, and symbolic ANF exposed severe polynomial-product tail cases despite perfect accuracy.",
        "Retain abstention and truth-vector fallbacks as negative and tail controls for the symbolic hybrid."),
}


def main():
    summary = load(RUN / "summary.json"); verification = load(VERIFY)
    expected = {"accepted_partition": False, "c4_improvement": False, "classification": False,
        "equivariance": True, "learned_cost": False, "pair_ranking": False,
        "production_promotion": False, "safety": True, "source_symbolic": True,
        "source_symbolic_cost": False}
    if (summary.get("status") != "complete" or verification.get("status") != "pass"
            or summary.get("criteria") != expected or summary.get("accepted_semantic_mismatches") != 0):
        raise SystemExit("refusing C5 registration: verified evidence differs from reviewed result")
    machine = {"schema": "crse-learning-milestone-c5-variable-cut-summary/v1", "date": "2026-08-29",
        "status": "complete", "report": REPORT, "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "verification": {"path": str(VERIFY.relative_to(ROOT)).replace("\\", "/"), **verification},
        "dataset": summary["dataset_audit"], "retained_c4": summary["retained_c4"],
        "models": summary["model_cards"], "classification": summary["classification"],
        "pair_ranking": summary["pair_ranking"], "equivariance": summary["equivariance"],
        "source_controls": summary["source_controls"], "controls": summary["controls"],
        "cost_ratios": summary["cost_ratios"], "criteria": summary["criteria"],
        "accepted_semantic_mismatches": 0,
        "interpretation": "Per-variable equivariance improved some cut recovery but not held-out transfer or learned cost. Exact source symbolic ANF was perfect and median-fast, with a severe confirmatory p95 tail requiring a bounded hybrid."}
    target = DOCS / MACHINE
    if target.exists(): raise SystemExit("refusing C5 registration: machine summary already exists")
    target.write_text(json.dumps(machine, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    data = load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer contains exact R01-R18 and eight applications")
    by_id = {track["id"]: track for track in data["tracks"]}
    for track_id, (reason, next_experiment) in UPDATES.items():
        track = by_id[track_id]
        if any(item.get("report") == REPORT for item in track["results"]):
            raise SystemExit(f"C5 already registered for {track_id}")
        track["status"] = "measured"; track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        track["results"].append({"report": REPORT, "machine_summary": MACHINE, "scope": reason})
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    hardware["results"].append({"report": REPORT, "machine_summary": MACHINE,
        "scope": "Variable-conditioned GNNs remained unprofitable, while exact source symbolic ANF achieved perfect natural decomposition recognition and median gains with an unresolved p95 tail."})
    data["milestones"]["C"] = "C5 variable-conditioned equivariant cuts complete; equivariance and exact symbolic source recognition passed, transfer and tail-cost criteria failed safely"
    data["updated"] = "2026-08-29"
    REGISTER.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "c5_tracks": sorted(UPDATES), "models": len(summary["model_cards"]),
        "source_symbolic": True, "production_promotion": False, "safety": True}))


if __name__ == "__main__": main()
