"""Matched-pair repeat of the natural EPFL decomposition experiment."""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import torch

from .decomposition_data import canonical
from .models.natural_torch_models import ARCHITECTURES, load_model, parameter_count, save_model
from .natural_decomposition_data import EPFL_LICENSE
from .natural_decomposition_experiment import (
    DEFAULT_SCOUT, Budget, NaturalDecompositionConfig, batch_schedule, choose_threshold,
    criteria, evaluation_row, exact_controls, examples_from_documents, outputs, summarize, train_model,
)
from .natural_decomposition_matched_data import make_matched_natural_documents, validate_matched_documents

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA = "crse-natural-decomposition-matched-learning/v1"


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value):
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def write_jsonl(path: Path, rows):
    with path.open("xb") as handle:
        for row in rows: handle.write(canonical(row) + b"\n")


def source_fingerprints(scout: Path):
    paths = [Path(__file__), ROOT / "cmbench" / "recognition" / "natural_decomposition.py",
        ROOT / "cmbench" / "recognition" / "natural_decomposition_data.py",
        ROOT / "cmbench" / "recognition" / "natural_decomposition_matched_data.py",
        ROOT / "cmbench" / "recognition" / "natural_decomposition_experiment.py",
        ROOT / "cmbench" / "recognition" / "models" / "natural_torch_models.py",
        ROOT / "cmbench" / "recognition" / "variable_graph_inputs.py", scout, EPFL_LICENSE]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in paths}


def run_matched_experiment(config: NaturalDecompositionConfig, output: Path,
                           scout: Path = DEFAULT_SCOUT, progress=print):
    config.validate(); output = output.resolve(); scout = scout.resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = config.manifest(output, scout)
    spec.update({"schema": "crse-natural-decomposition-matched-run-spec/v1",
        "pairing": "each natural positive is paired one-to-one with a same-circuit negative; prioritize same n, same variant, then minimum node/depth/edge deltas",
        "comparison_to_prior": "same architectures, hyperparameters, circuit splits, label counts and seeds; only negative selection is structure-matched",
        "selection_disclosure": "development repeat after unmatched natural results; not confirmatory evidence"})
    write_json(output / "run_spec.json", spec)
    before = source_fingerprints(scout); budget = Budget(config.max_seconds); started = time.perf_counter()
    torch.set_num_threads(config.threads)
    try: torch.set_num_interop_threads(1)
    except RuntimeError: pass
    progress("Freezing structure-matched natural EPFL pairs")
    documents, provenance = make_matched_natural_documents(scout, seed=config.data_seed, check=budget.check)
    audit = validate_matched_documents(documents, check=budget.check)
    write_json(output / "dataset.json", documents); write_json(output / "dataset_provenance.json", provenance)
    examples = examples_from_documents(documents)
    training = [example for example in examples if example.split == "train"]
    validation = [example for example in examples if example.split == "validation"]
    evaluation = [example for example in examples if example.split != "train"]
    dataset_sha = hashlib.sha256(canonical(documents)).hexdigest()
    training_ids_sha = hashlib.sha256(canonical([example.case_id for example in training])).hexdigest()
    schedules = {seed: batch_schedule(len(training), config, seed) for seed in config.training_seeds}
    rows, cards, calibration = [], [], {}
    for architecture in ARCHITECTURES:
        for seed in config.training_seeds:
            budget.check(); progress(f"Training matched {architecture}, seed {seed}")
            model, training_data = train_model(architecture, training, seed, config, budget, schedules[seed])
            training_data.update({"dataset_sha256": dataset_sha, "training_ids_sha256": training_ids_sha})
            validation_outputs = outputs(model, architecture, validation)
            threshold, balanced = choose_threshold(validation, validation_outputs,
                                                   architecture == "natural_multitask_gnn")
            calibration[f"{architecture}/seed-{seed}"] = {"threshold": threshold,
                "selection_split": "validation", "cases": len(validation),
                "balanced_accuracy_at_selected_threshold": balanced}
            filename = f"model-{architecture}-seed-{seed}.json"
            digest = save_model(model, architecture, training_data,
                {"torch": torch.__version__, "device": "cpu", "dtype": "float32"}, output / filename)
            name, restored, loaded_training, _metadata, loaded_digest = load_model(output / filename)
            if (name != architecture or loaded_training != training_data or loaded_digest != digest
                    or outputs(model, architecture, validation) != outputs(restored, architecture, validation)):
                raise ValueError("matched model reload mismatch")
            cards.append({"architecture": architecture, "seed": seed, "file": filename,
                "parameters": parameter_count(restored), "artifact_sha256": digest,
                "fit_ns": training_data["fit_ns"], "final_loss": training_data["loss_history"][-1],
                "final_auxiliary_loss": training_data["auxiliary_loss_history"][-1]})
            for example in evaluation:
                budget.check(); rows.append(evaluation_row(restored, architecture, example, seed, threshold))
    write_json(output / "calibration.json", calibration); write_jsonl(output / "classification_raw.jsonl", rows)
    controls = exact_controls(evaluation); write_json(output / "controls.json", controls)
    classification = summarize(rows); measured_criteria = criteria(classification, config.training_seeds)
    mismatches = sum(row["semantic_mismatch"] for row in rows); measured_criteria["safety"] = mismatches == 0
    after = source_fingerprints(scout); status = "complete" if before == after and not mismatches else "invalid"
    result = {"schema": RUN_SCHEMA, "status": status, "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0], "torch": torch.__version__,
        "config": json.loads(canonical(config.__dict__)), "dataset_audit": audit,
        "dataset_provenance": provenance, "model_cards": cards, "calibration": calibration,
        "classification": classification, "controls": controls["summary"], "row_count": len(rows),
        "proposal_reasons": dict(Counter(row["check_reason"] for row in rows)),
        "accepted_semantic_mismatches": mismatches, "criteria": measured_criteria,
        "source_unchanged": before == after,
        "claims": {"structure_matched": True, "development_repeat": True,
                   "independent_dataset_family": False, "production_promotion": False}}
    write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    write_json(output / "manifest.json", {"schema": "crse-natural-decomposition-matched-artifacts/v1",
        "status": status, "files_sha256": {path.name: sha(path) for path in files}, "source_sha256": before})
    return result


def render_report(result):
    audit = result["dataset_audit"]
    lines = ["# CRSE structure-matched natural decomposition learning", "",
        f"Status: **{result['status']}**", f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Semantic mismatches: {result['accepted_semantic_mismatches']}", "",
        f"Matched pairs: {audit['matched_pairs']}; same n: {audit['same_n_vars_fraction']:.3f}; "
        f"same variant: {audit['same_variant_fraction']:.3f}; median node/depth/edge deltas: "
        f"{audit['median_source_nodes_delta']:.0f}/{audit['median_depth_delta']:.0f}/{audit['median_source_edges_delta']:.0f}.", "",
        "| Architecture / seed / split | Balanced accuracy | Sensitivity | Specificity | Edge F1 |",
        "| --- | ---: | ---: | ---: | ---: |"]
    for key, values in result["classification"].items():
        edge = "n/a" if values["interaction_edge_f1"] is None else f"{values['interaction_edge_f1']:.3f}"
        lines.append(f"| {key} | {values['balanced_accuracy']:.3f} | {values['sensitivity']:.3f} | "
                     f"{values['specificity']:.3f} | {edge} |")
    lines += ["", "This is a development repeat prompted by the unmatched-source result. It uses the same circuit splits, labels, model schedules and seeds, while replacing random negative selection with one-to-one same-circuit structural matching.",
        "All learned positives remain proposals. Exact truth recomputation and partition witnesses decide acceptance; no model is promoted.", ""]
    return "\n".join(lines)
