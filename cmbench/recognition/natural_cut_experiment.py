"""Direct-cut and matched-pair ranking experiment on frozen natural EPFL cones."""
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

from .decomposition_data import canonical, packed_sha256
from .models.natural_cut_torch_models import (
    ARCHITECTURES,
    build_model,
    load_model,
    parameter_count,
    save_model,
    state_sha256,
)
from .models.variable_torch_models import batch_graphs
from .natural_decomposition import analyze_decomposition, partition_witness
from .natural_decomposition_data import EPFL_LICENSE
from .natural_decomposition_experiment import (
    DEFAULT_SCOUT,
    Budget,
    Example,
    examples_from_documents,
    structural_features,
)
from .natural_decomposition_matched_data import (
    make_matched_natural_documents,
    validate_matched_documents,
)
from .portfolio import reference_bits
from .variable_graph_inputs import graph_from_document

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA = "crse-natural-cut-ranking-experiment/v1"
MAX_VARS = 10


@dataclass(frozen=True)
class NaturalCutConfig:
    data_seed: int = 20260829
    training_seeds: tuple[int, int] = (1049, 1301)
    epochs: int = 30
    batch_pairs: int = 16
    learning_rate: float = 0.003
    cut_weight: float = 0.75
    ranking_weight: float = 0.50
    ranking_margin: float = 0.50
    threads: int = 2
    max_seconds: float = 120.0
    estimated_working_memory_bytes: int = 768 * 1024 * 1024

    def validate(self):
        if (
            type(self.data_seed) is not int
            or not 0 <= self.data_seed < 2**32
            or type(self.training_seeds) is not tuple
            or len(self.training_seeds) != 2
            or len(set(self.training_seeds)) != 2
            or any(type(seed) is not int or not 0 <= seed < 2**32 for seed in self.training_seeds)
            or not 1 <= self.epochs <= 100
            or not 1 <= self.batch_pairs <= 64
            or not 0 < self.learning_rate <= 0.01
            or not 0 < self.cut_weight <= 2
            or not 0 < self.ranking_weight <= 2
            or not 0 < self.ranking_margin <= 2
            or self.threads != 2
            or not 0 < self.max_seconds <= 120
            or self.estimated_working_memory_bytes > 1024**3
        ):
            raise ValueError("invalid natural cut experiment bounds")

    def run_spec(self, output: Path, scout: Path):
        self.validate()
        return {
            "schema": "crse-natural-cut-ranking-run-spec/v1",
            "status": "planned",
            "output_directory": str(output.resolve()),
            "scout": str(scout.resolve()),
            "config": asdict(self),
            "device": "cpu",
            "dataset": {
                "source": "frozen C3 same-circuit structure-matched EPFL pairs",
                "pairs": {"train": 48, "validation": 12, "test": 16, "confirmatory": 18},
                "selection_disclosure": "development follow-up after C3; no independent-family claim",
            },
            "architectures": list(ARCHITECTURES),
            "losses": {
                "classification": 1.0,
                "direct_cut": self.cut_weight,
                "same_pair_margin": self.ranking_weight,
                "ranking_margin": self.ranking_margin,
                "ranking_arms": ["structural_pair_ranker", "cut_rank_gnn"],
            },
            "decoding": "enumerate nontrivial row sides containing x0 and minimize direct-membership negative log likelihood",
            "calibration": "membership threshold selected on validation balanced accuracy only",
            "acceptance": "fresh truth-vector computation plus exact candidate-partition witness; structural control triggers full exact ANF proof",
            "controls": ["exact ANF interaction signature", "always abstain", "structural same-pair ranker"],
            "criteria": {
                "classification": "cut-rank GNN >=0.65 proposal balanced accuracy on test and confirmatory for both seeds",
                "accepted_partition": "cut-rank GNN >=0.30 accepted-positive recall on test and confirmatory for both seeds",
                "pair_ranking": "cut-rank GNN >=0.70 positive-over-matched-negative ranking accuracy on test and confirmatory for both seeds",
                "ranking_improvement": "cut-rank GNN accepted-positive recall exceeds direct-cut GNN by >=0.10 on both held-out splits and seeds",
                "cost": "safe cut-rank median end-to-end time no slower than exact ANF on both held-out splits and seeds",
                "safety": "zero accepted negative functions and zero final semantic changes",
                "production_promotion": False,
            },
            "limits": {
                "cooperative_wall_seconds": self.max_seconds,
                "cpu_threads": self.threads,
                "estimated_working_memory_bytes": self.estimated_working_memory_bytes,
                "max_variables": MAX_VARS,
                "max_parameters": 150_000,
                "network": False,
            },
        }


@dataclass(frozen=True)
class CutExample:
    base: Example
    pair_id: str
    row_target: tuple[int, ...]
    row_mask: tuple[int, ...]


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any):
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def write_jsonl(path: Path, rows):
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


def source_fingerprints(scout: Path):
    paths = [
        Path(__file__),
        ROOT / "cmbench" / "recognition" / "models" / "natural_cut_torch_models.py",
        ROOT / "cmbench" / "recognition" / "models" / "natural_torch_models.py",
        ROOT / "cmbench" / "recognition" / "natural_decomposition.py",
        ROOT / "cmbench" / "recognition" / "natural_decomposition_data.py",
        ROOT / "cmbench" / "recognition" / "natural_decomposition_experiment.py",
        ROOT / "cmbench" / "recognition" / "natural_decomposition_matched_data.py",
        ROOT / "cmbench" / "recognition" / "variable_graph_inputs.py",
        scout,
        EPFL_LICENSE,
    ]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in paths}


def cut_examples_from_documents(documents):
    base_examples = examples_from_documents(documents)
    result = []
    for row, base in zip(documents, base_examples):
        if row["case_id"] != base.case_id or row.get("matched_pair_id") is None:
            raise ValueError("natural cut document/example identity mismatch")
        target = [0] * MAX_VARS
        mask = [int(index < base.n_vars) for index in range(MAX_VARS)]
        if base.label:
            witness = row.get("witness")
            if type(witness) is not dict:
                raise ValueError("positive cut example lacks exact witness")
            variables = tuple(witness["row_variables"])
            if not variables or variables[0] != 0 or len(variables) == base.n_vars:
                raise ValueError("positive canonical cut orientation changed")
            for variable in variables:
                target[variable] = 1
            if partition_witness(base.bits, base.n_vars, variables) is None:
                raise ValueError("retained direct cut target is not exact")
        result.append(CutExample(base, row["matched_pair_id"], tuple(target), tuple(mask)))
    paired_examples(result)
    return result


def paired_examples(examples, split: str | None = None):
    groups = defaultdict(list)
    for example in examples:
        if split is None or example.base.split == split:
            groups[example.pair_id].append(example)
    pairs = []
    for pair_id, group in sorted(groups.items()):
        if len(group) != 2 or {item.base.label for item in group} != {0, 1}:
            raise ValueError(f"invalid natural cut pair: {pair_id}")
        positive = next(item for item in group if item.base.label == 1)
        negative = next(item for item in group if item.base.label == 0)
        if positive.base.split != negative.base.split or positive.base.circuit != negative.base.circuit:
            raise ValueError("natural cut pair crosses split or circuit")
        pairs.append((positive, negative))
    return pairs


def pair_schedule(pair_count: int, config: NaturalCutConfig, seed: int):
    rng = np.random.default_rng(seed)
    return [
        [indices[start:start + config.batch_pairs].tolist() for start in range(0, pair_count, config.batch_pairs)]
        for indices in (rng.permutation(pair_count) for _ in range(config.epochs))
    ]


def batch_inputs(examples, architecture: str):
    graphs = [graph_from_document(example.base.document, example.base.n_vars) for example in examples]
    structural = (
        torch.from_numpy(np.stack([
            structural_features(example.base, graph) for example, graph in zip(examples, graphs)
        ]))
        if architecture == "structural_pair_ranker"
        else None
    )
    graph_batch = batch_graphs(graphs) if architecture != "structural_pair_ranker" else None
    return structural, graph_batch


def forward(model, architecture: str, examples):
    structural, graph = batch_inputs(examples, architecture)
    return model(structural, graph)


def architecture_weights(architecture: str, config: NaturalCutConfig):
    return {
        "classification": 1.0,
        "cut": config.cut_weight if architecture != "structural_pair_ranker" else 0.0,
        "ranking": config.ranking_weight if architecture in ("structural_pair_ranker", "cut_rank_gnn") else 0.0,
        "ranking_margin": config.ranking_margin,
    }


def train_model(architecture: str, pairs, seed: int, config: NaturalCutConfig, budget: Budget, schedule):
    torch.manual_seed(seed)
    model = build_model(architecture)
    initial = state_sha256(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    weights = architecture_weights(architecture, config)
    losses, cut_losses, ranking_losses, steps = [], [], [], 0
    started = time.perf_counter_ns()
    for batches in schedule:
        model.train()
        epoch_losses, epoch_cut, epoch_ranking = [], [], []
        for indices in batches:
            budget.check()
            selected = [pairs[index] for index in indices]
            batch = [item for pair in selected for item in pair]
            labels = torch.tensor([item.base.label for item in batch], dtype=torch.float32)
            logits, cut_logits, _embedding = forward(model, architecture, batch)
            classification_loss = F.binary_cross_entropy_with_logits(logits, labels)
            cut_loss = torch.tensor(0.0)
            if cut_logits is not None:
                positive_logits = cut_logits[0::2]
                targets = torch.tensor([pair[0].row_target for pair in selected], dtype=torch.float32)
                masks = torch.tensor([pair[0].row_mask for pair in selected], dtype=torch.float32)
                element_loss = F.binary_cross_entropy_with_logits(positive_logits, targets, reduction="none")
                cut_loss = (element_loss * masks).sum() / masks.sum().clamp_min(1)
            ranking_loss = F.relu(weights["ranking_margin"] - logits[0::2] + logits[1::2]).mean()
            loss = (
                weights["classification"] * classification_loss
                + weights["cut"] * cut_loss
                + weights["ranking"] * ranking_loss
            )
            if not bool(torch.isfinite(loss)):
                raise ValueError("nonfinite natural cut loss")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            epoch_losses.append(float(loss.detach()))
            epoch_cut.append(float(cut_loss.detach()))
            epoch_ranking.append(float(ranking_loss.detach()))
            steps += 1
        losses.append(statistics.fmean(epoch_losses))
        cut_losses.append(statistics.fmean(epoch_cut))
        ranking_losses.append(statistics.fmean(epoch_ranking))
    model.eval()
    final = state_sha256(model)
    if final == initial:
        raise RuntimeError("natural cut parameters did not update")
    return model, {
        "status": "complete",
        "task": "natural-xor-cut-ranking",
        "seed": seed,
        "epochs": config.epochs,
        "batch_pairs": config.batch_pairs,
        "steps": steps,
        "pairs": len(pairs),
        "rows": 2 * len(pairs),
        "optimizer": "Adam",
        "learning_rate": config.learning_rate,
        "loss": "classification + direct-cut + same-pair-margin",
        "weights": weights,
        "loss_history": losses,
        "cut_loss_history": cut_losses,
        "ranking_loss_history": ranking_losses,
        "initial_state_sha256": initial,
        "final_state_sha256": final,
        "parameters_updated": True,
        "fit_ns": time.perf_counter_ns() - started,
    }


def outputs(model, architecture: str, examples):
    with torch.no_grad():
        logits, cut_logits, _embedding = forward(model, architecture, examples)
        scores = torch.sigmoid(logits).cpu().tolist()
        cuts = torch.sigmoid(cut_logits).cpu().tolist() if cut_logits is not None else [None] * len(examples)
    return [
        (float(score), None if cut is None else tuple(float(value) for value in cut))
        for score, cut in zip(scores, cuts)
    ]


def balanced_accuracy(labels, predictions):
    positives, negatives = sum(labels), len(labels) - sum(labels)
    if not positives or not negatives:
        raise ValueError("balanced accuracy requires both labels")
    return 0.5 * (
        sum(label and prediction for label, prediction in zip(labels, predictions)) / positives
        + sum(not label and not prediction for label, prediction in zip(labels, predictions)) / negatives
    )


def choose_threshold(examples, model_outputs):
    values = [row[0] for row in model_outputs]
    ordered = sorted(set(values))
    candidates = {0.0, 0.5, 1.0}
    candidates.update((left + right) / 2 for left, right in zip(ordered, ordered[1:]))
    labels = [example.base.label for example in examples]
    ranked = []
    for threshold in candidates:
        predictions = [int(score >= threshold) for score, _cut in model_outputs]
        score = balanced_accuracy(labels, predictions)
        false_positives = sum(not label and prediction for label, prediction in zip(labels, predictions))
        ranked.append((score, -false_positives, -abs(threshold - 0.5), -threshold, threshold))
    best = max(ranked)
    return best[4], best[0], -best[1]


def decode_direct_cut(probabilities: tuple[float, ...], n_vars: int):
    if len(probabilities) != MAX_VARS or not 2 <= n_vars <= MAX_VARS:
        raise ValueError("invalid direct-cut probabilities")
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in probabilities):
        raise ValueError("nonfinite direct-cut probability")
    clipped = [min(1 - 1e-7, max(1e-7, value)) for value in probabilities]
    candidates = []
    for rest_mask in range(1 << (n_vars - 1)):
        row = (0,) + tuple(
            variable for variable in range(1, n_vars)
            if rest_mask & (1 << (variable - 1))
        )
        if len(row) == n_vars:
            continue
        row_set = set(row)
        nll = -statistics.fmean(
            math.log(clipped[variable] if variable in row_set else 1 - clipped[variable])
            for variable in range(n_vars)
        )
        candidates.append((nll, abs(2 * len(row) - n_vars), max(len(row), n_vars - len(row)), row))
    if not candidates:
        raise ValueError("no direct-cut candidate")
    candidates.sort()
    nll, _imbalance, _largest, row = candidates[0]
    margin = candidates[1][0] - nll if len(candidates) > 1 else 0.0
    return row, float(nll), float(margin)


def evaluation_row(model, architecture: str, example: CutExample, seed: int, threshold: float):
    started = time.perf_counter_ns()
    structural, graph = batch_inputs([example], architecture)
    represented = time.perf_counter_ns()
    with torch.no_grad():
        logits, cut_logits, _embedding = model(structural, graph)
        score = float(torch.sigmoid(logits)[0])
        probabilities = (
            tuple(float(value) for value in torch.sigmoid(cut_logits)[0])
            if cut_logits is not None else None
        )
    inferred = time.perf_counter_ns()
    partition = None
    cut_nll = None
    cut_margin = None
    if probabilities is not None:
        partition, cut_nll, cut_margin = decode_direct_cut(probabilities, example.base.n_vars)
    proposed = score >= threshold
    witness = None
    if proposed:
        bits = reference_bits(example.base.expr, example.base.n_vars)
        witness = (
            analyze_decomposition(bits, example.base.n_vars).witness
            if partition is None
            else partition_witness(bits, example.base.n_vars, partition)
        )
    checked = time.perf_counter_ns()
    accepted = proposed and witness is not None
    mismatch = bool(accepted and not example.base.label)
    canonical = tuple(index for index, value in enumerate(example.row_target[:example.base.n_vars]) if value)
    canonical_match = bool(example.base.label and partition is not None and partition == canonical)
    return {
        "architecture": architecture,
        "seed": seed,
        "split": example.base.split,
        "pair_id": example.pair_id,
        "case_id": example.base.case_id,
        "circuit": example.base.circuit,
        "variant": example.base.variant,
        "n_vars": example.base.n_vars,
        "label": example.base.label,
        "score": score,
        "threshold": threshold,
        "predicted": int(proposed),
        "proposed": proposed,
        "row_variables": list(partition) if partition is not None else None,
        "cut_nll": cut_nll,
        "cut_margin": cut_margin,
        "canonical_partition_match": canonical_match,
        "accepted": accepted,
        "fallback_used": not accepted,
        "check_reason": (
            "full_exact_anf_witness" if accepted and partition is None
            else "exact_direct_cut_witness" if accepted
            else "exact_direct_cut_rejection" if proposed and partition is not None
            else "exact_anf_rejection" if proposed
            else "model_abstention"
        ),
        "semantic_mismatch": mismatch,
        "original_bits_sha256": packed_sha256(example.base.bits, example.base.n_vars),
        "final_bits_sha256": packed_sha256(example.base.bits, example.base.n_vars),
        "representation_ns": represented - started,
        "inference_ns": inferred - represented,
        "exact_check_ns": checked - inferred,
        "total_ns": checked - started,
    }


def summarize(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["architecture"], row["seed"], row["split"])].append(row)
    result = {}
    for (architecture, seed, split), group in sorted(grouped.items()):
        labels = [row["label"] for row in group]
        predictions = [row["predicted"] for row in group]
        positives, negatives = sum(labels), len(labels) - sum(labels)
        cut_rows = [row for row in group if row["row_variables"] is not None]
        result[f"{architecture}/seed-{seed}/{split}"] = {
            "cases": len(group),
            "balanced_accuracy": balanced_accuracy(labels, predictions),
            "sensitivity": sum(label and prediction for label, prediction in zip(labels, predictions)) / positives,
            "specificity": sum(not label and not prediction for label, prediction in zip(labels, predictions)) / negatives,
            "accepted_positive_recall": sum(row["label"] and row["accepted"] for row in group) / positives,
            "canonical_partition_recall": (
                sum(row["canonical_partition_match"] for row in group) / positives if cut_rows else None
            ),
            "proposals": sum(row["proposed"] for row in group),
            "accepted": sum(row["accepted"] for row in group),
            "fallbacks": sum(row["fallback_used"] for row in group),
            "median_representation_ns": statistics.median(row["representation_ns"] for row in group),
            "median_inference_ns": statistics.median(row["inference_ns"] for row in group),
            "median_exact_check_ns": statistics.median(row["exact_check_ns"] for row in group),
            "median_total_ns": statistics.median(row["total_ns"] for row in group),
        }
    return result


def pair_ranking(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["architecture"], row["seed"], row["split"], row["pair_id"])].append(row)
    by_split = defaultdict(list)
    detail = []
    for (architecture, seed, split, pair_id), group in sorted(groups.items()):
        if len(group) != 2 or {row["label"] for row in group} != {0, 1}:
            raise ValueError("evaluation pair inventory changed")
        positive = next(row for row in group if row["label"] == 1)
        negative = next(row for row in group if row["label"] == 0)
        correct = positive["score"] > negative["score"]
        margin = positive["score"] - negative["score"]
        detail.append({
            "architecture": architecture, "seed": seed, "split": split, "pair_id": pair_id,
            "positive_case_id": positive["case_id"], "negative_case_id": negative["case_id"],
            "positive_score": positive["score"], "negative_score": negative["score"],
            "score_margin": margin, "correct": correct,
        })
        by_split[(architecture, seed, split)].append((correct, margin))
    summary = {
        f"{architecture}/seed-{seed}/{split}": {
            "pairs": len(values),
            "ranking_accuracy": statistics.fmean(value[0] for value in values),
            "median_score_margin": statistics.median(value[1] for value in values),
        }
        for (architecture, seed, split), values in sorted(by_split.items())
    }
    return {"schema": "crse-natural-cut-pair-ranking/v1", "rows": detail, "summary": summary}


def exact_controls(examples):
    rows = []
    for example in examples:
        started = time.perf_counter_ns()
        bits = reference_bits(example.base.expr, example.base.n_vars)
        analysis = analyze_decomposition(bits, example.base.n_vars)
        elapsed = time.perf_counter_ns() - started
        rows.append({
            "case_id": example.base.case_id,
            "split": example.base.split,
            "label": example.base.label,
            "predicted": int(analysis.decomposable),
            "correct": int(analysis.decomposable) == example.base.label,
            "elapsed_ns": elapsed,
            "truth_sha256": packed_sha256(bits, example.base.n_vars),
        })
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["split"]].append(row)
    return {
        "schema": "crse-natural-cut-exact-controls/v1",
        "rows": rows,
        "summary": {
            split: {
                "cases": len(group),
                "exact_anf_accuracy": statistics.fmean(row["correct"] for row in group),
                "always_abstain_accuracy": statistics.fmean(row["label"] == 0 for row in group),
                "median_exact_anf_ns": statistics.median(row["elapsed_ns"] for row in group),
            }
            for split, group in sorted(grouped.items())
        },
    }


def cost_ratios(classification, controls):
    result = {}
    for key, values in classification.items():
        split = key.rsplit("/", 1)[1]
        exact_ns = controls[split]["median_exact_anf_ns"]
        result[key] = {
            "exact_anf_over_safe_learned": exact_ns / values["median_total_ns"],
            "safe_learned_over_exact_anf": values["median_total_ns"] / exact_ns,
        }
    return result


def measured_criteria(classification, ranking, costs, seeds):
    value = lambda architecture, seed, split, field: classification[f"{architecture}/seed-{seed}/{split}"][field]
    rank = lambda architecture, seed, split: ranking[f"{architecture}/seed-{seed}/{split}"]["ranking_accuracy"]
    classification_ok = all(
        value("cut_rank_gnn", seed, split, "balanced_accuracy") >= 0.65
        for seed in seeds for split in ("test", "confirmatory")
    )
    accepted_ok = all(
        value("cut_rank_gnn", seed, split, "accepted_positive_recall") >= 0.30
        for seed in seeds for split in ("test", "confirmatory")
    )
    ranking_ok = all(
        rank("cut_rank_gnn", seed, split) >= 0.70
        for seed in seeds for split in ("test", "confirmatory")
    )
    improvement_ok = all(
        value("cut_rank_gnn", seed, split, "accepted_positive_recall")
        >= value("direct_cut_gnn", seed, split, "accepted_positive_recall") + 0.10
        for seed in seeds for split in ("test", "confirmatory")
    )
    cost_ok = all(
        costs[f"cut_rank_gnn/seed-{seed}/{split}"]["safe_learned_over_exact_anf"] <= 1.0
        for seed in seeds for split in ("test", "confirmatory")
    )
    return {
        "classification": classification_ok,
        "accepted_partition": accepted_ok,
        "pair_ranking": ranking_ok,
        "ranking_improvement": improvement_ok,
        "cost": cost_ok,
        "safety": False,
        "production_promotion": False,
    }


def run_natural_cut_experiment(
    config: NaturalCutConfig,
    output: Path,
    scout: Path = DEFAULT_SCOUT,
    progress=print,
):
    config.validate()
    output = output.resolve()
    scout = scout.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "run_spec.json", config.run_spec(output, scout))
    before = source_fingerprints(scout)
    budget = Budget(config.max_seconds)
    started = time.perf_counter()
    torch.set_num_threads(config.threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass

    progress("Regenerating frozen structure-matched EPFL pairs")
    documents, provenance = make_matched_natural_documents(scout, seed=config.data_seed, check=budget.check)
    audit = validate_matched_documents(documents, check=budget.check)
    examples = cut_examples_from_documents(documents)
    write_json(output / "dataset.json", documents)
    write_json(output / "dataset_provenance.json", provenance)
    dataset_sha = hashlib.sha256(canonical(documents)).hexdigest()
    training_pairs = paired_examples(examples, "train")
    validation = [example for example in examples if example.base.split == "validation"]
    evaluation = [example for example in examples if example.base.split in ("test", "confirmatory")]
    pair_ids_sha = hashlib.sha256(canonical([pair[0].pair_id for pair in training_pairs])).hexdigest()
    schedules = {
        seed: pair_schedule(len(training_pairs), config, seed) for seed in config.training_seeds
    }

    rows, cards, calibration = [], [], {}
    for architecture in ARCHITECTURES:
        for seed in config.training_seeds:
            budget.check()
            progress(f"Training {architecture}, seed {seed}")
            model, training = train_model(
                architecture, training_pairs, seed, config, budget, schedules[seed]
            )
            training.update({"dataset_sha256": dataset_sha, "training_pair_ids_sha256": pair_ids_sha})
            validation_outputs = outputs(model, architecture, validation)
            threshold, balanced, false_positives = choose_threshold(validation, validation_outputs)
            calibration[f"{architecture}/seed-{seed}"] = {
                "threshold": threshold,
                "selection_split": "validation",
                "cases": len(validation),
                "balanced_accuracy": balanced,
                "false_positives": false_positives,
            }
            filename = f"model-{architecture}-seed-{seed}.json"
            digest = save_model(
                model,
                architecture,
                training,
                {"torch": torch.__version__, "device": "cpu", "dtype": "float32"},
                output / filename,
            )
            name, restored, loaded_training, _metadata, loaded_digest = load_model(output / filename)
            if (
                name != architecture
                or loaded_training != training
                or loaded_digest != digest
                or outputs(model, architecture, validation) != outputs(restored, architecture, validation)
            ):
                raise ValueError("natural cut model reload mismatch")
            cards.append({
                "architecture": architecture,
                "seed": seed,
                "file": filename,
                "parameters": parameter_count(restored),
                "artifact_sha256": digest,
                "fit_ns": training["fit_ns"],
                "final_loss": training["loss_history"][-1],
                "final_cut_loss": training["cut_loss_history"][-1],
                "final_ranking_loss": training["ranking_loss_history"][-1],
            })
            for example in evaluation:
                budget.check()
                rows.append(evaluation_row(restored, architecture, example, seed, threshold))

    write_json(output / "calibration.json", calibration)
    write_jsonl(output / "classification_raw.jsonl", rows)
    ranking = pair_ranking(rows)
    write_json(output / "pair_ranking.json", ranking)
    controls = exact_controls(evaluation)
    write_json(output / "controls.json", controls)
    classification = summarize(rows)
    costs = cost_ratios(classification, controls["summary"])
    criteria = measured_criteria(classification, ranking["summary"], costs, config.training_seeds)
    mismatches = sum(row["semantic_mismatch"] for row in rows)
    criteria["safety"] = mismatches == 0 and all(
        row["final_bits_sha256"] == row["original_bits_sha256"] for row in rows
    )
    after = source_fingerprints(scout)
    status = "complete" if before == after and criteria["safety"] else "invalid"
    result = {
        "schema": RUN_SCHEMA,
        "status": status,
        "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "config": asdict(config),
        "dataset_audit": audit,
        "dataset_provenance": provenance,
        "model_cards": cards,
        "calibration": calibration,
        "classification": classification,
        "pair_ranking": ranking["summary"],
        "controls": controls["summary"],
        "cost_ratios": costs,
        "row_count": len(rows),
        "proposal_reasons": dict(Counter(row["check_reason"] for row in rows)),
        "accepted_semantic_mismatches": mismatches,
        "criteria": criteria,
        "source_unchanged": before == after,
        "claims": {
            "direct_partition_supervision": True,
            "same_circuit_pair_ranking": True,
            "independent_dataset_family": False,
            "development_followup": True,
            "production_promotion": False,
        },
    }
    write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    write_json(output / "manifest.json", {
        "schema": "crse-natural-cut-ranking-artifacts/v1",
        "status": status,
        "files_sha256": {path.name: sha(path) for path in files},
        "source_sha256": before,
    })
    return result


def render_report(result):
    lines = [
        "# CRSE natural direct-cut and matched-pair ranking",
        "",
        f"Status: **{result['status']}**",
        f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Semantic mismatches: {result['accepted_semantic_mismatches']}",
        "",
        "| Architecture / seed / split | Balanced accuracy | Pair ranking | Accepted-positive recall | Canonical-cut recall | Safe learned / exact ANF |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, values in result["classification"].items():
        ranking = result["pair_ranking"][key]["ranking_accuracy"]
        canonical = values["canonical_partition_recall"]
        canonical_text = "n/a" if canonical is None else f"{canonical:.3f}"
        slowdown = result["cost_ratios"][key]["safe_learned_over_exact_anf"]
        lines.append(
            f"| {key} | {values['balanced_accuracy']:.3f} | {ranking:.3f} | "
            f"{values['accepted_positive_recall']:.3f} | {canonical_text} | {slowdown:.3f}x |"
        )
    lines += [
        "",
        "The structural arm uses membership and matched-pair ranking but has no learned partition; a positive triggers the full exact ANF proof. The two graph arms predict a complete row-variable cut directly.",
        "All thresholds use validation only. Test and confirmatory circuits never affect fitting or calibration.",
        "Every proposal pays for fresh truth recomputation and an exact witness. Rejection and abstention retain the original function. This remains an EPFL development experiment and cannot support independent-family or production claims.",
        "",
    ]
    return "\n".join(lines)
