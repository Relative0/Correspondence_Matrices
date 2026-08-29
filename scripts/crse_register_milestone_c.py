"""Record the measured Milestone C slice without dropping any research track."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs" / "recognition" / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C_2026_08_29.md"
MACHINE = "learning_milestone_c_results.json"

UPDATES = {
    "R02": ("measured",
            "Hidden-affine classification now compares matched matrix, CNN, GNN and fused inputs. Graph/fused learned generated held-out structure, but all models transferred poorly to the all-negative EPFL slice; other subclasses remain planned.",
            "Add natural positive and negative examples for another subclass without tuning on the retained EPFL slice."),
    "R03": ("measured",
            "Neural motif gates produced exact-checked affine replacements: 630 accepted, 552 semantic rejections and zero final mismatches across repeated cells. Generalized macro/rule discovery remains pending.",
            "Extend the exact proposal boundary to a bounded mux or repeated-cone replacement with deterministic controls."),
    "R08": ("negative-result",
            "An actual contrastive GNN was trained on exact-equivalent graph pairs. Top-1 exact retrieval was 0.469 on both test seeds, missing the predeclared 0.80 threshold; exact checks safely rejected misses.",
            "Compare deterministic truth/signature retrieval and train on more independent functional groups before another sealed evaluation."),
    "R11": ("measured",
            "Exact CM labels now supervise a source-DAG GNN that does not require the full CM for classification inference. Rich cofactor/distance targets and larger independent sources remain pending.",
            "Add explicit cofactor-relation and functional-distance targets with matched deterministic controls."),
    "R12": ("measured",
            "Actual matrix MLP, matrix CNN, graph GNN and fused models were trained/reloaded under matched budgets. Graph/fused won on generated held-out structure; CNN collapsed and every representation showed weak EPFL specificity.",
            "Add recursive/shared-block and hierarchical controls plus natural positive examples; retain the current run as sealed evidence."),
    "R13": ("measured",
            "Supervised classification and contrastive retrieval are now both exercised in addition to trees/MLPs. Forests, boosting, ranking, transfer, curriculum and other listed methods remain pending.",
            "Compare the GNN with a deterministic signature retriever and one non-neural linear/ranking control on the same splits."),
    "R16": ("measured",
            "Parameter bytes, graph-input memory, training time, safe load time, representation construction, inference, verification and fallback latency are retained. Quantization/distillation/compilation remain pending.",
            "Profile batched versus single-request inference and test a bounded early-exit/distillation control without JIT."),
    "R17": ("measured",
            "The EPFL transfer check exposed severe negative transfer and uncalibrated false proposals; exact rejection and the learned-bypass switch preserved all outputs. Calibrated novelty remains pending.",
            "Fit calibration on validation only, freeze it, then test abstention on a new natural source family."),
    "R18": ("measured",
            "One-bit near-matches, CNN collapse, failed retrieval threshold and poor all-negative EPFL transfer are retained as negative controls/results. Dense random and raw packed-operation controls remain pending.",
            "Add dense incompressible/no-sharing cases and packed primitive controls with the same output contract."),
}


def main():
    data = json.loads(PATH.read_text(encoding="utf-8"))
    ids = [track["id"] for track in data["tracks"]]
    if ids != [f"R{index:02d}" for index in range(1, 19)] or len(data.get("applications", [])) != 8:
        raise SystemExit("refusing update: register no longer contains the exact R01-R18 and eight applications")
    result = {"report": REPORT, "machine_summary": MACHINE}
    for track in data["tracks"]:
        dependencies = track["dependencies"]
        available = dependencies["available"]
        pytorch = "PyTorch 2.10.0+cpu (isolated optional environment)"
        if pytorch not in available:
            available.append(pytorch)
        dependencies["optional_not_installed"] = [item for item in dependencies["optional_not_installed"]
                                                    if not item.startswith("PyTorch")]
        if track["id"] in UPDATES:
            status, reason, next_experiment = UPDATES[track["id"]]
            track["status"] = status
            track["status_reason"] = reason
            track["next_experiment"] = next_experiment
            if any(item.get("report") == REPORT for item in track["results"]):
                raise SystemExit(f"Milestone C already registered for {track['id']}")
            track["results"].append({**result, "scope": reason})
    hardware = next(application for application in data["applications"]
                    if application["name"] == "Hardware verification/design")
    hardware["status"] = "measured"
    hardware["results"].append({**result,
        "scope": "Evaluation-only transfer smoke on 16 provenance-reviewed eight-variable EPFL cones from 15 circuits; all were non-affine, so only specificity and exact rejection were measured."})
    data["updated"] = "2026-08-29"
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "updated_tracks": sorted(UPDATES), "hardware_status": hardware["status"]}))


if __name__ == "__main__":
    main()
