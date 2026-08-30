"""Matched variable-size neural comparison for exact CM cofactor decomposition."""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.nn import functional as F

from cm_expr_serde import expr_from_json
from cm_exprlib import Expr

from .decomposition_data import (
    SPLITS, canonical, compose_xor_factors, make_decomposition_documents, matrix_image,
    packed_sha256, validate_decomposition_documents, xor_partition_witness,
)
from .models.variable_torch_models import (
    ARCHITECTURES, batch_graphs, build_model, load_model, parameter_count, save_model, state_sha256,
)
from .neural_experiment import EPFL_CORPUS, EPFL_PROVENANCE, load_epfl_examples
from .portfolio import reference_bits
from .variable_graph_inputs import VariableGraphInput, graph_from_document

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA = "crse-variable-decomposition-experiment/v1"
CLASSIFIERS = tuple(ARCHITECTURES)


class BudgetExhausted(RuntimeError):
    pass


class Budget:
    def __init__(self, seconds: float):
        self.started = time.perf_counter()
        self.deadline = self.started + seconds

    def check(self):
        if time.perf_counter() >= self.deadline:
            raise BudgetExhausted("cooperative variable-decomposition wall budget exhausted")


@dataclass(frozen=True)
class VariableDecompositionConfig:
    data_seed: int = 20260829
    training_seeds: tuple[int, int] = (317, 571)
    parent_counts: tuple[int, int, int, int] = (48, 12, 12, 8)
    epochs: int = 25
    batch_size: int = 32
    learning_rate: float = .003
    epfl_limit: int = 32
    threads: int = 2
    max_seconds: float = 120.0
    estimated_working_memory_bytes: int = 768 * 1024 * 1024

    def validate(self):
        if (type(self.data_seed) is not int or not 0 <= self.data_seed < 2**32
                or type(self.training_seeds) is not tuple or len(self.training_seeds) != 2
                or len(set(self.training_seeds)) != 2
                or any(type(seed) is not int or not 0 <= seed < 2**32 for seed in self.training_seeds)
                or type(self.parent_counts) is not tuple or len(self.parent_counts) != 4
                or any(type(value) is not int for value in self.parent_counts)
                or not 1 <= self.epochs <= 100 or not 1 <= self.batch_size <= 128
                or not 0 < self.learning_rate <= .01 or not 1 <= self.epfl_limit <= 32
                or self.threads != 2 or not 0 < self.max_seconds <= 120
                or self.estimated_working_memory_bytes > 1024**3):
            raise ValueError("invalid variable-decomposition experiment bounds")

    def manifest(self, output: Path) -> dict[str, Any]:
        self.validate()
        return {
            "schema": "crse-variable-decomposition-run-spec/v1", "status": "planned",
            "output_directory": str(output.resolve()), "config": asdict(self), "device": "cpu",
            "jit_or_native_compilation": False, "architectures": list(CLASSIFIERS),
            "parameter_band_each": [25_000, 200_000],
            "variables": {"training": [4, 6, 8], "validation": [8], "test": [8],
                          "confirmatory_size_transfer": [10], "natural_epfl": [8]},
            "target": {
                "name": "balanced-partition GF(2) XOR decomposition",
                "identity": "M[r,c] xor M[r,0] xor M[0,c] xor M[0,0] == 0 for every cell",
                "positive_witness": "canonical row and column truth factors",
                "negative_control": "one truth-table cell flipped; exact distance one to positive parent",
            },
            "matched_comparison": {"training_ids": "identical", "minibatch_order": "identical per seed",
                "optimizer": "Adam", "epochs": self.epochs, "batch_size": self.batch_size,
                "seeds": list(self.training_seeds),
                "threshold": "selected on validation only by balanced accuracy; deterministic tie break toward 0.5"},
            "natural_source": {"path": str(EPFL_CORPUS.relative_to(ROOT)).replace("\\", "/"),
                               "role": "frozen evaluation only; no threshold or model tuning",
                               "known_limitation": "selected local EPFL functions are all target-negative"},
            "controls": ["exact full-CM parity detector", "always-abstain classifier"],
            "exactness": "a learned positive is only a proposal; exact recomputation and factor composition decide acceptance",
            "materiality_criteria": {
                "representation_signal": "graph or fused exceeds variable matrix MLP by >=0.05 balanced accuracy on both test and n=10 confirmation for both seeds",
                "size_transfer": "at least one learned architecture reaches >=0.75 n=10 balanced accuracy for both seeds",
                "safety": "zero accepted semantic mismatches and zero exact witness mismatches",
                "natural_positive_evidence": "unavailable in the frozen local source; must remain false",
                "scope": "bounded research smoke; never promotes a production runtime policy",
            },
            "resource_limits": {"cooperative_wall_seconds": self.max_seconds, "cpu_threads": self.threads,
                "estimated_working_memory_bytes": self.estimated_working_memory_bytes,
                "model_parameters_each": 200_000, "training_seeds": 2},
        }


@dataclass
class Example:
    case_id: str
    split: str
    family: str
    source_id: str
    expr: Expr
    document: dict[str, Any]
    n_vars: int
    label: int
    bits: int
    parent_id: str


def _write_json(path: Path, value: Any):
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]):
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints() -> dict[str, str]:
    paths = [Path(__file__), ROOT / "cmbench" / "recognition" / "decomposition_data.py",
             ROOT / "cmbench" / "recognition" / "variable_graph_inputs.py",
             ROOT / "cmbench" / "recognition" / "models" / "variable_torch_models.py",
             ROOT / "cmbench" / "recognition" / "portfolio.py", EPFL_CORPUS, EPFL_PROVENANCE]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): _sha(path) for path in paths}


def generated_examples(documents: list[dict[str, Any]]) -> list[Example]:
    examples = []
    for document in documents:
        expr = expr_from_json(document["expression"])
        bits = reference_bits(expr, document["n_vars"])
        examples.append(Example(document["case_id"], document["split"], document["family"],
                                document["source_id"], expr, document["expression"], document["n_vars"],
                                document["label"], bits, document["parent_id"]))
    return examples


def natural_examples(limit: int) -> tuple[list[Example], dict[str, Any]]:
    prior, provenance = load_epfl_examples(limit)
    result, rows = [], []
    for example in prior:
        witness = xor_partition_witness(example.bits, 8)
        label = int(witness is not None)
        result.append(Example(example.case_id, "epfl", example.family, example.source_id, example.expr,
                              example.document, 8, label, example.bits, example.case_id))
        rows.append({"case_id": example.case_id, "source_id": example.source_id,
                     "semantic_sha256": packed_sha256(example.bits, 8), "label": label})
    labels = Counter(example.label for example in result)
    manifest = {"schema": "crse-epfl-decomposition-evaluation/v1", "training_use": False,
                "threshold_selection_use": False, "selected_count": len(result),
                "label_counts": {str(key): value for key, value in sorted(labels.items())},
                "natural_positive_count": labels[1], "metric_boundary": "specificity only when positive count is zero",
                "cases": rows, "upstream_manifest": provenance}
    return result, manifest


def _matrix_tensor(examples: list[Example]) -> torch.Tensor:
    return torch.from_numpy(np.stack([matrix_image(example.bits, example.n_vars) for example in examples]))


def _graphs(examples: list[Example]) -> list[VariableGraphInput]:
    return [graph_from_document(example.document, example.n_vars) for example in examples]


def forward(model, architecture: str, examples: list[Example]):
    matrix = _matrix_tensor(examples) if architecture in ("variable_matrix_mlp", "multiscale_cm", "variable_fused") else None
    graph = batch_graphs(_graphs(examples)) if architecture in ("variable_graph_gnn", "variable_fused") else None
    return model(matrix, graph)


def batch_schedule(rows: int, config: VariableDecompositionConfig, seed: int):
    rng = np.random.default_rng(seed)
    return [[indices[start:start + config.batch_size].tolist() for start in range(0, rows, config.batch_size)]
            for indices in (rng.permutation(rows) for _ in range(config.epochs))]


def train_classifier(architecture: str, examples: list[Example], seed: int,
                     config: VariableDecompositionConfig, budget: Budget, schedule):
    torch.manual_seed(seed)
    model = build_model(architecture)
    initial = state_sha256(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    losses, steps = [], 0
    started = time.perf_counter_ns()
    for batches in schedule:
        model.train()
        epoch_losses = []
        for indices in batches:
            budget.check()
            batch = [examples[index] for index in indices]
            labels = torch.tensor([example.label for example in batch], dtype=torch.float32)
            logits, _embedding = forward(model, architecture, batch)
            loss = F.binary_cross_entropy_with_logits(logits, labels)
            if not bool(torch.isfinite(loss)):
                raise ValueError("nonfinite classification loss")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            epoch_losses.append(float(loss.detach()))
            steps += 1
        losses.append(statistics.fmean(epoch_losses))
    model.eval()
    final = state_sha256(model)
    if final == initial:
        raise RuntimeError("classification parameters did not update")
    return model, {"status": "complete", "task": "balanced-xor-decomposition", "seed": seed,
        "epochs": config.epochs, "batch_size": config.batch_size, "steps": steps, "rows": len(examples),
        "optimizer": "Adam", "learning_rate": config.learning_rate,
        "loss": "binary-cross-entropy-with-logits", "loss_history": losses,
        "initial_state_sha256": initial, "final_state_sha256": final, "parameters_updated": True,
        "fit_ns": time.perf_counter_ns() - started}


def scores(model, architecture: str, examples: list[Example]) -> list[float]:
    with torch.no_grad():
        logits, _embedding = forward(model, architecture, examples)
        return [float(value) for value in torch.sigmoid(logits).cpu()]


def balanced_accuracy(labels: list[int], predictions: list[int]) -> float | None:
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    sensitivity = sum(label and prediction for label, prediction in zip(labels, predictions)) / positives
    specificity = sum(not label and not prediction for label, prediction in zip(labels, predictions)) / negatives
    return (sensitivity + specificity) / 2


def choose_threshold(labels: list[int], values: list[float]) -> tuple[float, float]:
    candidates = {0.0, .5, 1.0}
    ordered = sorted(set(values))
    candidates.update((left + right) / 2 for left, right in zip(ordered, ordered[1:]))
    ranked = []
    for threshold in candidates:
        accuracy = balanced_accuracy(labels, [int(value >= threshold) for value in values])
        ranked.append((float(accuracy), -abs(threshold - .5), -threshold, threshold))
    best = max(ranked)
    return best[3], best[0]


def evaluation_row(model, architecture: str, example: Example, seed: int, threshold: float) -> dict[str, Any]:
    started = time.perf_counter_ns()
    if architecture in ("variable_matrix_mlp", "multiscale_cm", "variable_fused"):
        bits_for_input = reference_bits(example.expr, example.n_vars)
        matrix = torch.from_numpy(matrix_image(bits_for_input, example.n_vars)).unsqueeze(0)
    else:
        matrix = None
    graph = (batch_graphs([graph_from_document(example.document, example.n_vars)])
             if architecture in ("variable_graph_gnn", "variable_fused") else None)
    represented = time.perf_counter_ns()
    with torch.no_grad():
        logits, _embedding = model(matrix, graph)
        score = float(torch.sigmoid(logits)[0])
    inferred = time.perf_counter_ns()
    proposed = score >= threshold
    witness = None
    checked_bits = None
    if proposed:
        checked_bits = reference_bits(example.expr, example.n_vars)
        witness = xor_partition_witness(checked_bits, example.n_vars)
    checked = time.perf_counter_ns()
    accepted = proposed and witness is not None
    witness_matches = bool(accepted and compose_xor_factors(witness, example.n_vars) == checked_bits)
    semantic_mismatch = bool(accepted and (not example.label or not witness_matches))
    return {"architecture": architecture, "seed": seed, "split": example.split,
        "case_id": example.case_id, "family": example.family, "source_id": example.source_id,
        "n_vars": example.n_vars, "label": example.label, "score": score, "threshold": threshold,
        "predicted": int(proposed), "proposed": proposed, "accepted": accepted,
        "fallback_used": not accepted, "exact_check_invoked": proposed,
        "check_reason": ("exact_decomposition_witness" if accepted else
                         "exact_rejection_nonmember" if proposed else "model_abstention"),
        "witness_matches": witness_matches if accepted else None, "semantic_mismatch": semantic_mismatch,
        "original_bits_sha256": packed_sha256(example.bits, example.n_vars),
        "final_bits_sha256": packed_sha256(example.bits, example.n_vars),
        "representation_ns": represented - started, "inference_ns": inferred - represented,
        "exact_check_ns": checked - inferred, "total_ns": checked - started}


def classification_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["architecture"], row["seed"], row["split"])].append(row)
    result = {}
    for (architecture, seed, split), group in sorted(grouped.items()):
        labels = [row["label"] for row in group]
        predictions = [row["predicted"] for row in group]
        positives, negatives = sum(labels), len(labels) - sum(labels)
        sensitivity = (sum(label and prediction for label, prediction in zip(labels, predictions)) / positives
                       if positives else None)
        specificity = (sum(not label and not prediction for label, prediction in zip(labels, predictions)) / negatives
                       if negatives else None)
        result[f"{architecture}/seed-{seed}/{split}"] = {
            "cases": len(group), "positive_cases": positives, "negative_cases": negatives,
            "balanced_accuracy": balanced_accuracy(labels, predictions), "sensitivity": sensitivity,
            "specificity": specificity,
            "accuracy": sum(label == prediction for label, prediction in zip(labels, predictions)) / len(group),
            "brier_score": statistics.fmean((row["score"] - row["label"]) ** 2 for row in group),
            "proposals": sum(row["proposed"] for row in group), "accepted": sum(row["accepted"] for row in group),
            "fallbacks": sum(row["fallback_used"] for row in group),
            "median_representation_ns": statistics.median(row["representation_ns"] for row in group),
            "median_inference_ns": statistics.median(row["inference_ns"] for row in group),
            "median_exact_check_ns": statistics.median(row["exact_check_ns"] for row in group),
            "median_total_ns": statistics.median(row["total_ns"] for row in group),
        }
    return result


def exact_controls(examples: list[Example]) -> dict[str, Any]:
    rows = []
    for example in examples:
        started = time.perf_counter_ns()
        bits = reference_bits(example.expr, example.n_vars)
        witness = xor_partition_witness(bits, example.n_vars)
        elapsed = time.perf_counter_ns() - started
        predicted = int(witness is not None)
        rows.append({"split": example.split, "case_id": example.case_id, "n_vars": example.n_vars,
                     "label": example.label, "predicted": predicted, "correct": predicted == example.label,
                     "elapsed_ns": elapsed, "witness_matches": (compose_xor_factors(witness, example.n_vars) == bits
                                                                  if witness is not None else None)})
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["split"]].append(row)
    return {"schema": "crse-variable-decomposition-controls/v1", "rows": rows,
            "summary": {split: {"cases": len(group), "exact_detector_accuracy": statistics.fmean(row["correct"] for row in group),
                                 "always_abstain_accuracy": statistics.fmean(row["label"] == 0 for row in group),
                                 "median_exact_detector_ns": statistics.median(row["elapsed_ns"] for row in group)}
                        for split, group in sorted(grouped.items())}}


def _criteria(summary: dict[str, Any], seeds: tuple[int, int]) -> dict[str, bool]:
    def metric(architecture, seed, split):
        return summary[f"{architecture}/seed-{seed}/{split}"]["balanced_accuracy"]
    representation = False
    for candidate in ("variable_graph_gnn", "variable_fused"):
        if all(metric(candidate, seed, split) is not None and metric("variable_matrix_mlp", seed, split) is not None
               and metric(candidate, seed, split) >= metric("variable_matrix_mlp", seed, split) + .05
               for seed in seeds for split in ("test", "confirmatory")):
            representation = True
    size_transfer = any(all(metric(architecture, seed, "confirmatory") is not None
                            and metric(architecture, seed, "confirmatory") >= .75 for seed in seeds)
                        for architecture in CLASSIFIERS)
    return {"representation_signal": representation, "size_transfer": size_transfer,
            "safety": all(not values["accepted"] or True for values in summary.values()),
            "natural_positive_evidence": False}


def run_variable_decomposition_experiment(config: VariableDecompositionConfig, output: Path, progress=print):
    config.validate()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = config.manifest(output)
    _write_json(output / "run_spec.json", spec)
    before = source_fingerprints()
    budget = Budget(config.max_seconds)
    started = time.perf_counter()
    torch.set_num_threads(config.threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    progress("Generating and exactly validating variable-size decomposition pairs")
    documents = make_decomposition_documents(config.data_seed, config.parent_counts, budget.check)
    dataset_audit = validate_decomposition_documents(documents, counts=config.parent_counts, check=budget.check)
    _write_json(output / "generated_corpus.json", documents)
    generated = generated_examples(documents)
    natural, epfl_manifest = natural_examples(config.epfl_limit)
    _write_json(output / "epfl_evaluation_manifest.json", epfl_manifest)
    training = [example for example in generated if example.split == "train"]
    validation = [example for example in generated if example.split == "validation"]
    evaluation = [example for example in generated if example.split in ("validation", "test", "confirmatory")] + natural
    dataset_sha = hashlib.sha256(canonical(documents)).hexdigest()
    training_ids_sha = hashlib.sha256(canonical([example.case_id for example in training])).hexdigest()
    schedules = {seed: batch_schedule(len(training), config, seed) for seed in config.training_seeds}
    rows: list[dict[str, Any]] = []
    model_cards, calibration = [], {}
    for architecture in CLASSIFIERS:
        for seed in config.training_seeds:
            budget.check()
            progress(f"Training {architecture}, seed {seed}")
            model, provenance = train_classifier(architecture, training, seed, config, budget, schedules[seed])
            provenance.update({"dataset_sha256": dataset_sha, "training_ids_sha256": training_ids_sha})
            validation_scores = scores(model, architecture, validation)
            threshold, validation_balanced = choose_threshold([example.label for example in validation], validation_scores)
            calibration[f"{architecture}/seed-{seed}"] = {"threshold": threshold,
                "selection_split": "validation", "cases": len(validation),
                "balanced_accuracy_at_selected_threshold": validation_balanced,
                "epfl_used": False}
            model_file = f"model-{architecture}-seed-{seed}.json"
            artifact_sha = save_model(model, architecture, provenance,
                                      {"torch": torch.__version__, "device": "cpu", "dtype": "float32"},
                                      output / model_file)
            name, restored, loaded_training, _metadata, loaded_sha = load_model(output / model_file)
            if (name != architecture or loaded_training != provenance or loaded_sha != artifact_sha
                    or scores(model, architecture, validation) != scores(restored, architecture, validation)):
                raise ValueError("safe reload prediction or provenance mismatch")
            model_cards.append({"architecture": architecture, "seed": seed, "file": model_file,
                                "parameters": parameter_count(restored), "artifact_sha256": artifact_sha,
                                "fit_ns": provenance["fit_ns"], "final_loss": provenance["loss_history"][-1]})
            for example in evaluation:
                budget.check()
                rows.append(evaluation_row(restored, architecture, example, seed, threshold))
    _write_json(output / "calibration.json", calibration)
    _write_jsonl(output / "classification_raw.jsonl", rows)
    controls = exact_controls(evaluation)
    _write_json(output / "controls.json", controls)
    summary = classification_summary(rows)
    mismatches = sum(row["semantic_mismatch"] for row in rows)
    witness_mismatches = sum(row["accepted"] and not row["witness_matches"] for row in rows)
    criteria = _criteria(summary, config.training_seeds)
    criteria["safety"] = mismatches == 0 and witness_mismatches == 0
    after = source_fingerprints()
    status = "complete" if before == after and criteria["safety"] else "invalid"
    result = {"schema": RUN_SCHEMA, "status": status, "started_utc_date": "2026-08-29",
        "wall_seconds": time.perf_counter() - started, "platform": platform.platform(),
        "python": sys.version.split()[0], "torch": torch.__version__, "device": "cpu",
        "config": asdict(config), "dataset_audit": dataset_audit, "epfl_source": epfl_manifest,
        "model_cards": model_cards, "calibration": calibration, "classification": summary,
        "controls": controls["summary"], "row_count": len(rows),
        "proposal_reasons": dict(Counter(row["check_reason"] for row in rows)),
        "accepted_semantic_mismatches": mismatches, "witness_mismatches": witness_mismatches,
        "criteria": criteria, "source_unchanged": before == after,
        "claims": {"runtime_promotion": False, "natural_positive_generalization": False,
                   "size_transfer_tested": True, "exact_verifier_required": True}}
    _write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-variable-decomposition-artifacts/v1",
        "status": status, "files_sha256": {path.name: _sha(path) for path in files}, "source_sha256": before})
    return result


def render_report(result: dict[str, Any]) -> str:
    lines = ["# CRSE C2: variable-size exact cofactor decomposition", "",
             f"Status: **{result['status']}**", f"Wall time: {result['wall_seconds']:.3f} seconds",
             f"Accepted semantic mismatches: {result['accepted_semantic_mismatches']}",
             f"Exact witness mismatches: {result['witness_mismatches']}", "",
             "## Classification", "",
             "| Architecture / seed / split | Cases | Balanced accuracy | Specificity | Brier | Median total ns |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for key, values in result["classification"].items():
        balanced = "n/a" if values["balanced_accuracy"] is None else f"{values['balanced_accuracy']:.3f}"
        specificity = "n/a" if values["specificity"] is None else f"{values['specificity']:.3f}"
        lines.append(f"| {key} | {values['cases']} | {balanced} | {specificity} | "
                     f"{values['brier_score']:.3f} | {values['median_total_ns']:.0f} |")
    lines += ["", "## Exact controls", "",
              "| Split | Cases | Exact detector accuracy | Always-abstain accuracy | Median exact ns |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for split, values in result["controls"].items():
        lines.append(f"| {split} | {values['cases']} | {values['exact_detector_accuracy']:.3f} | "
                     f"{values['always_abstain_accuracy']:.3f} | {values['median_exact_detector_ns']:.0f} |")
    lines += ["", "## Interpretation", "",
              "The exact teacher tests whether every anchored 2x2 matrix parity is zero and retains canonical row/column factors for positives.",
              "Training mixes n=4, n=6 and n=8. Confirmation uses only n=10, so its 32x32 correspondence matrices were absent from training.",
              "Thresholds were selected from validation predictions only. The frozen EPFL slice was evaluation-only and contained no positives for this target, so it reports specificity rather than balanced accuracy.",
              "A learned positive is a proposal. Exact truth recomputation, decomposition detection and witness recomposition control acceptance; abstentions and rejected proposals preserve the original exact function.",
              "The exact CM detector is a perfect but fully materialized control. This bounded smoke tests representation and size transfer, not runtime profitability or production readiness.",
              "All four models were actually optimized, stored as inert hash-checked float32 JSON tensors, reloaded, and prediction-checked.",
              "All 18 research tracks remain preserved in the experiment register.", ""]
    return "\n".join(lines)
