"""Natural EPFL decomposition learning with circuit-disjoint source splits."""
from __future__ import annotations

import hashlib
import json
import math
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

from .decomposition_data import canonical, packed_sha256
from .models.natural_torch_models import (
    ARCHITECTURES, INTERACTION_TARGETS, STRUCTURAL_FEATURES, build_model, load_model,
    parameter_count, save_model, state_sha256,
)
from .models.variable_torch_models import batch_graphs
from .natural_decomposition import (
    analyze_decomposition, interaction_edges, partition_witness,
)
from .natural_decomposition_data import (
    EPFL_LICENSE, PER_LABEL_COUNTS, SPLIT_CIRCUITS, make_natural_decomposition_documents,
    validate_natural_decomposition_documents,
)
from .portfolio import reference_bits
from .variable_graph_inputs import EDGE_ROLES, OPS, VariableGraphInput, graph_from_document

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCOUT = ROOT / "docs" / "recognition" / "source_scouts" / "natural-decomposition-epfl-20260829-001.json"
CLASSIFIERS = tuple(ARCHITECTURES)
RUN_SCHEMA = "crse-natural-decomposition-learning-experiment/v1"


class BudgetExhausted(RuntimeError):
    pass


class Budget:
    def __init__(self, seconds: float):
        self.started = time.perf_counter()
        self.deadline = self.started + seconds

    def check(self):
        if time.perf_counter() >= self.deadline:
            raise BudgetExhausted("cooperative natural-decomposition wall budget exhausted")


@dataclass(frozen=True)
class NaturalDecompositionConfig:
    data_seed: int = 20260829
    training_seeds: tuple[int, int] = (619, 887)
    epochs: int = 30
    batch_size: int = 32
    learning_rate: float = .003
    auxiliary_weight: float = .30
    threads: int = 2
    max_seconds: float = 120.0
    estimated_working_memory_bytes: int = 768 * 1024 * 1024

    def validate(self):
        if (type(self.data_seed) is not int or not 0 <= self.data_seed < 2**32
                or type(self.training_seeds) is not tuple or len(self.training_seeds) != 2
                or len(set(self.training_seeds)) != 2
                or any(type(seed) is not int or not 0 <= seed < 2**32 for seed in self.training_seeds)
                or not 1 <= self.epochs <= 100 or not 1 <= self.batch_size <= 128
                or not 0 < self.learning_rate <= .01 or not 0 < self.auxiliary_weight <= 1
                or self.threads != 2 or not 0 < self.max_seconds <= 120
                or self.estimated_working_memory_bytes > 1024**3):
            raise ValueError("invalid natural-decomposition experiment bounds")

    def manifest(self, output: Path, scout: Path):
        self.validate()
        return {"schema": "crse-natural-decomposition-run-spec/v1", "status": "planned",
            "output_directory": str(output.resolve()), "config": asdict(self), "device": "cpu",
            "scout": str(scout.resolve()), "architectures": list(CLASSIFIERS),
            "dataset": {"source": "pinned local MIT-licensed EPFL BLIF",
                "split_circuits": {key: list(value) for key, value in SPLIT_CIRCUITS.items()},
                "per_label_counts": PER_LABEL_COUNTS, "variables": [4, 5, 6, 7, 8, 9, 10],
                "selection_disclosure": "circuits were chosen after a source prevalence scout to supply both labels; this is development evidence, not independent source confirmation"},
            "target": {"membership": "exists nontrivial f(X)=g(A) XOR h(B) partition",
                "auxiliary": "45 padded exact ANF variable-interaction edges",
                "multitask_partition": "connected components of predicted interaction graph",
                "exact_acceptance": "recomputed truth vector plus exact candidate-partition witness"},
            "matched_comparison": {"training_ids": "identical", "minibatch_order": "identical per seed",
                "optimizer": "Adam", "epochs": self.epochs, "batch_size": self.batch_size,
                "learning_rate": self.learning_rate, "seeds": list(self.training_seeds),
                "threshold": "validation-only balanced accuracy; deterministic tie break toward 0.5"},
            "controls": ["17-feature structural linear", "exact ANF interaction components", "always abstain"],
            "materiality_criteria": {"natural_multitask": "multitask GNN >=0.70 balanced accuracy on test and confirmatory for both seeds",
                "representation": "multitask GNN exceeds structural linear by >=0.05 on test and confirmatory for both seeds",
                "auxiliary": "multitask valid-edge F1 >=0.70 on test and confirmatory for both seeds",
                "safety": "zero accepted semantic and candidate-partition witness mismatches",
                "production_promotion": False},
            "resource_limits": {"cooperative_wall_seconds": self.max_seconds, "cpu_threads": self.threads,
                "estimated_working_memory_bytes": self.estimated_working_memory_bytes,
                "training_seeds": 2, "network": False, "max_variables": 10, "max_source_nodes": 128}}


@dataclass
class Example:
    case_id: str
    split: str
    circuit: str
    variant: str
    expr: Expr
    document: dict[str, Any]
    n_vars: int
    label: int
    bits: int
    interaction_target: tuple[int, ...]
    interaction_mask: tuple[int, ...]
    source_nodes: int
    source_edges: int
    depth: int


def _write_json(path: Path, value: Any):
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]):
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


def _sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints(scout: Path):
    paths = [Path(__file__), ROOT / "cmbench" / "recognition" / "natural_decomposition.py",
             ROOT / "cmbench" / "recognition" / "natural_decomposition_data.py",
             ROOT / "cmbench" / "recognition" / "models" / "natural_torch_models.py",
             ROOT / "cmbench" / "recognition" / "variable_graph_inputs.py", scout, EPFL_LICENSE]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): _sha(path) for path in paths}


def examples_from_documents(documents: list[dict[str, Any]]):
    result = []
    for row in documents:
        expr = expr_from_json(row["expression_v2"])
        bits = reference_bits(expr, row["n_vars"])
        result.append(Example(row["case_id"], row["split"], row["circuit"], row["variant"], expr,
            row["expression_v2"], row["n_vars"], row["label"], bits,
            tuple(row["interaction_target"]), tuple(row["interaction_mask"]),
            row["source_nodes"], row["source_edges"], row["depth"]))
    return result


def structural_features(example: Example, graph: VariableGraphInput | None = None) -> np.ndarray:
    graph = graph or graph_from_document(example.document, example.n_vars)
    nodes = len(graph.node_features)
    edges = graph.edge_index.shape[1]
    values = [example.n_vars / 10, math.log1p(example.source_nodes) / math.log(129),
              math.log1p(example.source_edges) / math.log(257), example.depth / 128,
              math.log1p(nodes) / math.log(4097), math.log1p(edges) / math.log(8193),
              min(1.0, edges / max(1, 2 * (nodes - 1)))]
    values.extend(float(graph.node_features[:, index].mean()) for index in range(len(OPS)))
    values.extend(float(np.mean(graph.edge_roles == index)) if edges else 0.0 for index in range(len(EDGE_ROLES)))
    result = np.asarray(values, dtype=np.float32)
    if result.shape != (STRUCTURAL_FEATURES,) or not np.isfinite(result).all():
        raise ValueError("invalid structural control features")
    return result


def _batch_inputs(examples: list[Example], architecture: str):
    graphs = [graph_from_document(example.document, example.n_vars) for example in examples]
    structural = (torch.from_numpy(np.stack([structural_features(example, graph)
                                             for example, graph in zip(examples, graphs)]))
                  if architecture == "structural_linear" else None)
    graph_batch = batch_graphs(graphs) if architecture != "structural_linear" else None
    return structural, graph_batch


def forward(model, architecture: str, examples: list[Example]):
    structural, graph = _batch_inputs(examples, architecture)
    return model(structural, graph)


def batch_schedule(rows: int, config: NaturalDecompositionConfig, seed: int):
    rng = np.random.default_rng(seed)
    return [[indices[start:start + config.batch_size].tolist() for start in range(0, rows, config.batch_size)]
            for indices in (rng.permutation(rows) for _ in range(config.epochs))]


def train_model(architecture: str, examples: list[Example], seed: int, config: NaturalDecompositionConfig,
                budget: Budget, schedule):
    torch.manual_seed(seed)
    model = build_model(architecture)
    initial = state_sha256(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    losses, auxiliary_losses, steps = [], [], 0
    started = time.perf_counter_ns()
    auxiliary_weight = config.auxiliary_weight if architecture == "natural_multitask_gnn" else 0.0
    for batches in schedule:
        model.train()
        epoch_losses, epoch_auxiliary = [], []
        for indices in batches:
            budget.check()
            batch = [examples[index] for index in indices]
            labels = torch.tensor([example.label for example in batch], dtype=torch.float32)
            logits, interaction_logits, _embedding = forward(model, architecture, batch)
            classification_loss = F.binary_cross_entropy_with_logits(logits, labels)
            auxiliary_loss = torch.tensor(0.0)
            if interaction_logits is not None:
                targets = torch.tensor([example.interaction_target for example in batch], dtype=torch.float32)
                masks = torch.tensor([example.interaction_mask for example in batch], dtype=torch.float32)
                element_loss = F.binary_cross_entropy_with_logits(interaction_logits, targets, reduction="none")
                auxiliary_loss = (element_loss * masks).sum() / masks.sum().clamp_min(1)
            loss = classification_loss + auxiliary_weight * auxiliary_loss
            if not bool(torch.isfinite(loss)):
                raise ValueError("nonfinite natural decomposition loss")
            optimizer.zero_grad(set_to_none=True); loss.backward(); optimizer.step()
            epoch_losses.append(float(loss.detach())); epoch_auxiliary.append(float(auxiliary_loss.detach())); steps += 1
        losses.append(statistics.fmean(epoch_losses)); auxiliary_losses.append(statistics.fmean(epoch_auxiliary))
    model.eval()
    final = state_sha256(model)
    if final == initial:
        raise RuntimeError("natural decomposition parameters did not update")
    return model, {"status": "complete", "task": "natural-xor-decomposition", "seed": seed,
        "epochs": config.epochs, "batch_size": config.batch_size, "steps": steps, "rows": len(examples),
        "optimizer": "Adam", "learning_rate": config.learning_rate,
        "loss": "binary-cross-entropy-with-logits", "auxiliary_weight": auxiliary_weight,
        "loss_history": losses, "auxiliary_loss_history": auxiliary_losses,
        "initial_state_sha256": initial, "final_state_sha256": final, "parameters_updated": True,
        "fit_ns": time.perf_counter_ns() - started}


def outputs(model, architecture: str, examples: list[Example]):
    with torch.no_grad():
        logits, interactions, _embedding = forward(model, architecture, examples)
        class_scores = torch.sigmoid(logits).cpu().tolist()
        interaction_scores = torch.sigmoid(interactions).cpu().tolist() if interactions is not None else [None] * len(examples)
    return [(float(score), None if edge_scores is None else tuple(float(value) for value in edge_scores))
            for score, edge_scores in zip(class_scores, interaction_scores)]


def _components_from_scores(edge_scores: tuple[float, ...], n_vars: int):
    parent = list(range(n_vars))
    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]; value = parent[value]
        return value
    def union(left, right):
        left, right = find(left), find(right)
        if left != right:
            parent[max(left, right)] = min(left, right)
    index = 0
    for left in range(10):
        for right in range(left + 1, 10):
            if right < n_vars and edge_scores[index] >= .5:
                union(left, right)
            index += 1
    groups = defaultdict(list)
    for variable in range(n_vars):
        groups[find(variable)].append(variable)
    return tuple(sorted((tuple(group) for group in groups.values()), key=lambda group: group[0]))


def _partition_from_components(components, n_vars: int):
    if len(components) < 2:
        return None
    candidates = []
    for mask in range(0, 1 << (len(components) - 1)):
        selected = (0,) + tuple(index for index in range(1, len(components)) if mask & (1 << (index - 1)))
        row = tuple(sorted(variable for index in selected for variable in components[index]))
        if len(row) == n_vars:
            continue
        column = tuple(variable for variable in range(n_vars) if variable not in row)
        candidates.append((abs(len(row) - len(column)), max(len(row), len(column)), row))
    return min(candidates)[2] if candidates else None


def predicted_partition(edge_scores: tuple[float, ...] | None, n_vars: int):
    if edge_scores is None or len(edge_scores) != INTERACTION_TARGETS:
        return None
    return _partition_from_components(_components_from_scores(edge_scores, n_vars), n_vars)


def _balanced_accuracy(labels, predictions):
    positives, negatives = sum(labels), len(labels) - sum(labels)
    if not positives or not negatives:
        return None
    return .5 * (sum(label and prediction for label, prediction in zip(labels, predictions)) / positives
                 + sum(not label and not prediction for label, prediction in zip(labels, predictions)) / negatives)


def choose_threshold(examples: list[Example], model_outputs, multitask: bool):
    values = [value[0] for value in model_outputs]
    ordered = sorted(set(values))
    candidates = {0.0, .5, 1.0}
    candidates.update((left + right) / 2 for left, right in zip(ordered, ordered[1:]))
    ranked = []
    for threshold in candidates:
        predictions = [int(score >= threshold and (not multitask or predicted_partition(edges, example.n_vars) is not None))
                       for example, (score, edges) in zip(examples, model_outputs)]
        balanced = _balanced_accuracy([example.label for example in examples], predictions)
        ranked.append((float(balanced), -abs(threshold - .5), -threshold, threshold))
    best = max(ranked)
    return best[3], best[0]


def _edge_counts(example: Example, scores: tuple[float, ...] | None):
    if scores is None:
        return None
    truth = example.interaction_target
    mask = example.interaction_mask
    predicted = [int(score >= .5) for score in scores]
    tp = sum(m and t and p for m, t, p in zip(mask, truth, predicted))
    fp = sum(m and not t and p for m, t, p in zip(mask, truth, predicted))
    fn = sum(m and t and not p for m, t, p in zip(mask, truth, predicted))
    correct = sum(m and t == p for m, t, p in zip(mask, truth, predicted))
    valid = sum(mask)
    return {"tp": tp, "fp": fp, "fn": fn, "correct": correct, "valid": valid}


def evaluation_row(model, architecture: str, example: Example, seed: int, threshold: float):
    started = time.perf_counter_ns()
    structural, graph = _batch_inputs([example], architecture)
    represented = time.perf_counter_ns()
    with torch.no_grad():
        logits, interactions, _embedding = model(structural, graph)
        score = float(torch.sigmoid(logits)[0])
        edge_scores = (tuple(float(value) for value in torch.sigmoid(interactions)[0])
                       if interactions is not None else None)
    inferred = time.perf_counter_ns()
    candidate_partition = predicted_partition(edge_scores, example.n_vars) if edge_scores is not None else None
    proposed = score >= threshold and (edge_scores is None or candidate_partition is not None)
    exact_witness = None
    if proposed:
        bits = reference_bits(example.expr, example.n_vars)
        if candidate_partition is None:
            exact_witness = analyze_decomposition(bits, example.n_vars).witness
        else:
            exact_witness = partition_witness(bits, example.n_vars, candidate_partition)
    checked = time.perf_counter_ns()
    accepted = proposed and exact_witness is not None
    mismatch = bool(accepted and not example.label)
    edge_counts = _edge_counts(example, edge_scores)
    return {"architecture": architecture, "seed": seed, "split": example.split,
        "case_id": example.case_id, "circuit": example.circuit, "variant": example.variant,
        "n_vars": example.n_vars, "label": example.label, "score": score, "threshold": threshold,
        "predicted": int(proposed), "proposed": proposed,
        "predicted_row_variables": list(candidate_partition) if candidate_partition is not None else None,
        "accepted": accepted, "fallback_used": not accepted, "exact_check_invoked": proposed,
        "check_reason": ("exact_candidate_partition_witness" if accepted else
                         "exact_rejection_or_wrong_partition" if proposed else "model_abstention"),
        "semantic_mismatch": mismatch, "edge_counts": edge_counts,
        "original_bits_sha256": packed_sha256(example.bits, example.n_vars),
        "final_bits_sha256": packed_sha256(example.bits, example.n_vars),
        "representation_ns": represented - started, "inference_ns": inferred - represented,
        "exact_check_ns": checked - inferred, "total_ns": checked - started}


def summarize(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["architecture"], row["seed"], row["split"])].append(row)
    result = {}
    for (architecture, seed, split), group in sorted(grouped.items()):
        labels = [row["label"] for row in group]; predictions = [row["predicted"] for row in group]
        positives, negatives = sum(labels), len(labels) - sum(labels)
        edges = [row["edge_counts"] for row in group if row["edge_counts"] is not None]
        tp, fp, fn = (sum(row[key] for row in edges) for key in ("tp", "fp", "fn")) if edges else (0, 0, 0)
        result[f"{architecture}/seed-{seed}/{split}"] = {"cases": len(group),
            "balanced_accuracy": _balanced_accuracy(labels, predictions),
            "sensitivity": sum(label and prediction for label, prediction in zip(labels, predictions)) / positives,
            "specificity": sum(not label and not prediction for label, prediction in zip(labels, predictions)) / negatives,
            "accuracy": sum(label == prediction for label, prediction in zip(labels, predictions)) / len(group),
            "brier_score": statistics.fmean((row["score"] - row["label"]) ** 2 for row in group),
            "proposals": sum(row["proposed"] for row in group), "accepted": sum(row["accepted"] for row in group),
            "fallbacks": sum(row["fallback_used"] for row in group),
            "interaction_edge_f1": (2 * tp / (2 * tp + fp + fn) if edges and 2 * tp + fp + fn else 0.0) if edges else None,
            "interaction_edge_accuracy": (sum(row["correct"] for row in edges) / sum(row["valid"] for row in edges)
                                          if edges else None),
            "median_total_ns": statistics.median(row["total_ns"] for row in group),
            "median_representation_ns": statistics.median(row["representation_ns"] for row in group),
            "median_inference_ns": statistics.median(row["inference_ns"] for row in group),
            "median_exact_check_ns": statistics.median(row["exact_check_ns"] for row in group)}
    return result


def exact_controls(examples):
    rows = []
    for example in examples:
        started = time.perf_counter_ns(); bits = reference_bits(example.expr, example.n_vars)
        analysis = analyze_decomposition(bits, example.n_vars); elapsed = time.perf_counter_ns() - started
        rows.append({"case_id": example.case_id, "split": example.split, "label": example.label,
            "predicted": int(analysis.decomposable), "correct": int(analysis.decomposable) == example.label,
            "components": len(analysis.components), "elapsed_ns": elapsed})
    grouped = defaultdict(list)
    for row in rows: grouped[row["split"]].append(row)
    return {"schema": "crse-natural-decomposition-controls/v1", "rows": rows,
        "summary": {split: {"cases": len(group), "exact_anf_accuracy": statistics.fmean(row["correct"] for row in group),
            "always_abstain_accuracy": statistics.fmean(row["label"] == 0 for row in group),
            "median_exact_anf_ns": statistics.median(row["elapsed_ns"] for row in group)}
            for split, group in sorted(grouped.items())}}


def criteria(summary, seeds):
    def value(architecture, seed, split, field="balanced_accuracy"):
        return summary[f"{architecture}/seed-{seed}/{split}"][field]
    natural_multitask = all(value("natural_multitask_gnn", seed, split) >= .70
                            for seed in seeds for split in ("test", "confirmatory"))
    representation = all(value("natural_multitask_gnn", seed, split)
                         >= value("structural_linear", seed, split) + .05
                         for seed in seeds for split in ("test", "confirmatory"))
    auxiliary = all(value("natural_multitask_gnn", seed, split, "interaction_edge_f1") >= .70
                    for seed in seeds for split in ("test", "confirmatory"))
    return {"natural_multitask": natural_multitask, "representation": representation,
            "auxiliary": auxiliary, "safety": False, "production_promotion": False}


def run_natural_decomposition_experiment(config: NaturalDecompositionConfig, output: Path,
                                         scout: Path = DEFAULT_SCOUT, progress=print):
    config.validate(); output = output.resolve(); scout = scout.resolve()
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "run_spec.json", config.manifest(output, scout))
    before = source_fingerprints(scout)
    budget = Budget(config.max_seconds); started = time.perf_counter()
    torch.set_num_threads(config.threads)
    try: torch.set_num_interop_threads(1)
    except RuntimeError: pass
    progress("Freezing circuit-disjoint natural EPFL dataset")
    documents, provenance = make_natural_decomposition_documents(scout, seed=config.data_seed, check=budget.check)
    audit = validate_natural_decomposition_documents(documents, check=budget.check)
    _write_json(output / "dataset.json", documents); _write_json(output / "dataset_provenance.json", provenance)
    examples = examples_from_documents(documents)
    training = [example for example in examples if example.split == "train"]
    validation = [example for example in examples if example.split == "validation"]
    evaluation = [example for example in examples if example.split != "train"]
    dataset_sha = hashlib.sha256(canonical(documents)).hexdigest()
    training_ids_sha = hashlib.sha256(canonical([example.case_id for example in training])).hexdigest()
    schedules = {seed: batch_schedule(len(training), config, seed) for seed in config.training_seeds}
    rows, cards, calibration = [], [], {}
    for architecture in CLASSIFIERS:
        for seed in config.training_seeds:
            budget.check(); progress(f"Training {architecture}, seed {seed}")
            model, provenance_model = train_model(architecture, training, seed, config, budget, schedules[seed])
            provenance_model.update({"dataset_sha256": dataset_sha, "training_ids_sha256": training_ids_sha})
            validation_outputs = outputs(model, architecture, validation)
            threshold, validation_balanced = choose_threshold(validation, validation_outputs,
                                                               architecture == "natural_multitask_gnn")
            calibration[f"{architecture}/seed-{seed}"] = {"threshold": threshold,
                "selection_split": "validation", "cases": len(validation),
                "balanced_accuracy_at_selected_threshold": validation_balanced}
            filename = f"model-{architecture}-seed-{seed}.json"
            artifact_sha = save_model(model, architecture, provenance_model,
                {"torch": torch.__version__, "device": "cpu", "dtype": "float32"}, output / filename)
            name, restored, loaded_training, _metadata, loaded_sha = load_model(output / filename)
            if (name != architecture or loaded_training != provenance_model or loaded_sha != artifact_sha
                    or outputs(model, architecture, validation) != outputs(restored, architecture, validation)):
                raise ValueError("natural model reload prediction mismatch")
            cards.append({"architecture": architecture, "seed": seed, "file": filename,
                "parameters": parameter_count(restored), "artifact_sha256": artifact_sha,
                "fit_ns": provenance_model["fit_ns"], "final_loss": provenance_model["loss_history"][-1],
                "final_auxiliary_loss": provenance_model["auxiliary_loss_history"][-1]})
            for example in evaluation:
                budget.check(); rows.append(evaluation_row(restored, architecture, example, seed, threshold))
    _write_json(output / "calibration.json", calibration); _write_jsonl(output / "classification_raw.jsonl", rows)
    controls = exact_controls(evaluation); _write_json(output / "controls.json", controls)
    classification = summarize(rows); measured_criteria = criteria(classification, config.training_seeds)
    mismatches = sum(row["semantic_mismatch"] for row in rows)
    measured_criteria["safety"] = mismatches == 0
    after = source_fingerprints(scout)
    status = "complete" if before == after and measured_criteria["safety"] else "invalid"
    result = {"schema": RUN_SCHEMA, "status": status, "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0], "torch": torch.__version__,
        "config": asdict(config), "dataset_audit": audit, "dataset_provenance": provenance,
        "model_cards": cards, "calibration": calibration, "classification": classification,
        "controls": controls["summary"], "row_count": len(rows),
        "proposal_reasons": dict(Counter(row["check_reason"] for row in rows)),
        "accepted_semantic_mismatches": mismatches, "criteria": measured_criteria,
        "source_unchanged": before == after,
        "claims": {"natural_positive_and_negative_evidence": True, "independent_dataset_family": False,
                   "development_source_selection": True, "production_promotion": False,
                   "exact_verifier_required": True}}
    _write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-natural-decomposition-artifacts/v1",
        "status": status, "files_sha256": {path.name: _sha(path) for path in files}, "source_sha256": before})
    return result


def render_report(result):
    lines = ["# CRSE natural EPFL decomposition learning", "", f"Status: **{result['status']}**",
        f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Accepted semantic mismatches: {result['accepted_semantic_mismatches']}", "",
        "## Circuit-disjoint classification", "",
        "| Architecture / seed / split | Cases | Balanced accuracy | Sensitivity | Specificity | Edge F1 | Median total ns |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for key, values in result["classification"].items():
        edge = "n/a" if values["interaction_edge_f1"] is None else f"{values['interaction_edge_f1']:.3f}"
        lines.append(f"| {key} | {values['cases']} | {values['balanced_accuracy']:.3f} | "
                     f"{values['sensitivity']:.3f} | {values['specificity']:.3f} | {edge} | {values['median_total_ns']:.0f} |")
    lines += ["", "## Exact controls", "",
        "| Split | Cases | Exact ANF accuracy | Always abstain | Median exact ns |",
        "| --- | ---: | ---: | ---: | ---: |"]
    for split, values in result["controls"].items():
        lines.append(f"| {split} | {values['cases']} | {values['exact_anf_accuracy']:.3f} | "
                     f"{values['always_abstain_accuracy']:.3f} | {values['median_exact_anf_ns']:.0f} |")
    lines += ["", "## Scope", "",
        "Every split is label-balanced and circuit-disjoint. Training uses adder, hyp, mem_ctrl, multiplier and router; validation uses div; test uses square; confirmatory development evaluation uses sin, sqrt and voter.",
        "The source scout was used to choose circuits that contain both labels, so this is natural-source development evidence rather than a sealed independent-family confirmation.",
        "The multitask GNN predicts both decomposition membership and all valid ANF variable-interaction edges. Its proposed disconnected components define a concrete candidate partition.",
        "Every proposed partition is checked against a freshly recomputed exact truth vector. Rejection or abstention preserves the original function.",
        "The exact ANF control is perfect but requires complete semantics. The learned graph path is only potentially useful before CM materialization and is not promoted here.", ""]
    return "\n".join(lines)
