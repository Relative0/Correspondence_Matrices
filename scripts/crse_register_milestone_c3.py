"""Register verified CRSE C3 evidence without dropping any research track."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C3_NATURAL_DECOMPOSITION_2026_08_29.md"
MACHINE = "learning_milestone_c3_natural_decomposition_results.json"

RUNS = {
    "natural": DOCS / "runs" / "natural-decomposition-20260829-001",
    "decoder": DOCS / "runs" / "natural-decomposition-decoder-20260829-001",
    "matched": DOCS / "runs" / "natural-decomposition-matched-20260829-001",
}
VERIFICATIONS = {
    "natural": DOCS / "verification" / "natural-decomposition-20260829-001.json",
    "decoder": DOCS / "verification" / "natural-decomposition-decoder-20260829-001.json",
    "matched": DOCS / "verification" / "natural-decomposition-matched-20260829-001.json",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


UPDATES = {
    "R02": (
        "EPFL now supplies exact positive and negative arbitrary-partition XOR decompositions over 4-10 live variables; 188 balanced circuit-disjoint examples are retained.",
        "Train and freeze a direct cut-supervision/ranking comparison on the structure-matched pairs before one-pass evaluation on a second circuit family.",
    ),
    "R03": (
        "Natural positive proposals now carry discovered variable partitions and exact factor witnesses; all acceptance paths preserve the original function on rejection.",
        "Integrate a proposal only after it identifies the correct partition often enough to amortize exact verification in a downstream rewrite.",
    ),
    "R06": (
        "The exact teacher now proves f(X)=g(A) XOR h(B) for arbitrary nontrivial partitions using disconnected ANF interaction components.",
        "Add complementary AND/rank controls and compare their exact signatures under the same circuit-disjoint data contract.",
    ),
    "R11": (
        "Supervision now includes the exact class, canonical components, partition witnesses, and all 45 padded ANF interaction-edge targets.",
        "Replace independent edge thresholding with a directly supervised cut or partition-ranking objective.",
    ),
    "R12": (
        "Structural, source-DAG GNN, and multitask GNN models were trained on natural circuit cones. None passed both-seed held-out-circuit criteria.",
        "Compare a deterministic signature, pairwise matched ranking, and cut-aware GNN without increasing capacity first.",
    ),
    "R13": (
        "Validation-only calibration, circuit-disjoint splits, exact ANF auxiliary targets, and a frozen minimum-cut decoder were measured across two seeds.",
        "Freeze cut-supervision and calibration on EPFL, then run once on a separately licensed circuit family.",
    ),
    "R16": (
        "Six natural and six structure-matched models retain fit, representation, inference, decoding, exact-check, and exact-control measurements.",
        "Measure end-to-end proposal plus exact witness cost only after accepted-positive recall improves materially.",
    ),
    "R17": (
        "Circuit-disjoint natural evaluation is now label-balanced, but structure matching reduced most learned scores toward chance and exposed dataset shortcuts.",
        "Use an independently sourced circuit family for a single sealed confirmation after the EPFL design is frozen.",
    ),
    "R18": (
        "Same-circuit matched negatives with identical variable count and median zero node/depth/edge deltas defeated the current GNNs; the failure is retained.",
        "Keep exact ANF and abstention controls and add adversarial single-edge partition confounders to direct cut training.",
    ),
}


def selected_classification(summary):
    return {
        key: {
            field: values[field]
            for field in ("cases", "balanced_accuracy", "sensitivity", "specificity", "interaction_edge_f1")
        }
        for key, values in summary["classification"].items()
        if key.endswith(("/test", "/confirmatory"))
    }


def main():
    summaries = {name: load(path / "summary.json") for name, path in RUNS.items()}
    verifications = {name: load(path) for name, path in VERIFICATIONS.items()}
    if any(summary.get("status") != "complete" for summary in summaries.values()):
        raise SystemExit("refusing C3 registration: a retained run is incomplete")
    if any(verification.get("status") != "pass" for verification in verifications.values()):
        raise SystemExit("refusing C3 registration: independent verification did not pass")
    if (
        summaries["natural"]["criteria"] != {
            "auxiliary": True,
            "natural_multitask": False,
            "production_promotion": False,
            "representation": False,
            "safety": True,
        }
        or summaries["matched"]["criteria"] != {
            "auxiliary": False,
            "natural_multitask": False,
            "production_promotion": False,
            "representation": False,
            "safety": True,
        }
        or summaries["decoder"]["criteria"] != {
            "accepted_positive_recall": False,
            "production_promotion": False,
            "proposal_balanced_accuracy": False,
            "safety": True,
        }
    ):
        raise SystemExit("refusing C3 registration: retained criteria differ from the reviewed result")
    if any(
        summary.get("accepted_semantic_mismatches", summary.get("semantic_mismatches")) != 0
        for summary in summaries.values()
    ):
        raise SystemExit("refusing C3 registration: semantic mismatch recorded")

    scout = load(DOCS / "source_scouts" / "natural-decomposition-epfl-20260829-001.json")
    machine = {
        "schema": "crse-learning-milestone-c3-natural-decomposition-summary/v1",
        "date": "2026-08-29",
        "status": "complete",
        "report": REPORT,
        "source": {
            "name": "EPFL combinational benchmark suite",
            "upstream_commit": summaries["natural"]["dataset_provenance"]["upstream_commit"],
            "license": summaries["natural"]["dataset_provenance"]["license"],
            "external_download_performed": False,
            "scouted_candidates": sum(scout["totals"].values()),
            "scouted_positive": scout["totals"]["positive"],
            "scouted_negative": scout["totals"]["negative"],
        },
        "dataset": summaries["natural"]["dataset_audit"],
        "matched_dataset": summaries["matched"]["dataset_audit"],
        "runs": {name: str(path.relative_to(ROOT)).replace("\\", "/") for name, path in RUNS.items()},
        "verifications": {
            name: {"path": str(VERIFICATIONS[name].relative_to(ROOT)).replace("\\", "/"), **verification}
            for name, verification in verifications.items()
        },
        "natural_classification": selected_classification(summaries["natural"]),
        "matched_classification": selected_classification(summaries["matched"]),
        "decoder": summaries["decoder"]["summaries"],
        "criteria": {name: summary["criteria"] for name, summary in summaries.items()},
        "accepted_semantic_mismatches": 0,
        "interpretation": (
            "Natural arbitrary-partition labels and exact auxiliary targets are now available, but the learned signal did not survive structure matching or identify exact partitions reliably. Exact ANF remains the accepted control."
        ),
    }
    target = DOCS / MACHINE
    if target.exists():
        raise SystemExit("refusing C3 registration: machine summary already exists")
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
            raise SystemExit(f"C3 already registered for {track_id}")
        track["status"] = "measured"
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        track["results"].append({"report": REPORT, "machine_summary": MACHINE, "scope": reason})
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    hardware["results"].append({
        "report": REPORT,
        "machine_summary": MACHINE,
        "scope": "A 9,060-cone EPFL scout yielded 894 exact arbitrary-partition positives. Balanced circuit-disjoint and structure-matched learning studies failed promotion safely; exact ANF controls were perfect.",
    })
    data["milestones"]["C"] = (
        "C3 natural arbitrary-partition decomposition complete; exact teacher passed, neural and decoder promotion criteria failed safely"
    )
    data["updated"] = "2026-08-29"
    REGISTER.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "tracks": len(data["tracks"]),
        "applications": len(data["applications"]),
        "c3_tracks": sorted(UPDATES),
        "scouted_positive": scout["totals"]["positive"],
        "natural_rows": summaries["natural"]["dataset_audit"]["rows"],
        "matched_pairs": summaries["matched"]["dataset_audit"]["matched_pairs"],
        "production_promotion": False,
        "safety": True,
    }))


if __name__ == "__main__":
    main()
