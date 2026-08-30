"""Per-variable equivariant cut learning with deterministic source controls."""
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

from .decomposition_data import canonical, packed_sha256
from .models.natural_variable_cut_torch_models import (
    ARCHITECTURES,
    build_model,
    load_model,
    parameter_count,
    save_model,
    state_sha256,
)
from .models.variable_torch_models import GraphBatch, batch_graphs
from .natural_cut_experiment import (
    balanced_accuracy,
    choose_threshold,
    cost_ratios,
    cut_examples_from_documents,
    decode_direct_cut,
    exact_controls,
    pair_ranking,
    pair_schedule,
    paired_examples,
    summarize,
)
from .natural_decomposition import partition_witness
from .natural_decomposition_data import EPFL_LICENSE
from .natural_decomposition_experiment import DEFAULT_SCOUT, Budget
from .natural_decomposition_matched_data import make_matched_natural_documents, validate_matched_documents
from .portfolio import reference_bits
from .source_interaction import source_exact_partition, source_partition_proposal
from .variable_graph_inputs import MAX_VARS, OPS, graph_from_document

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_C4_RUN = ROOT / "docs" / "recognition" / "runs" / "natural-cut-ranking-20260829-001"
RUN_SCHEMA = "crse-natural-variable-cut-experiment/v1"


@dataclass(frozen=True)
class NaturalVariableCutConfig:
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
        if (type(self.data_seed) is not int or not 0 <= self.data_seed < 2**32
                or type(self.training_seeds) is not tuple or self.training_seeds != (1049, 1301)
                or not 1 <= self.epochs <= 100 or not 1 <= self.batch_pairs <= 64
                or not 0 < self.learning_rate <= .01 or not 0 < self.cut_weight <= 2
                or not 0 < self.ranking_weight <= 2 or not 0 < self.ranking_margin <= 2
                or self.threads != 2 or not 0 < self.max_seconds <= 120
                or self.estimated_working_memory_bytes > 1024**3):
            raise ValueError("invalid natural variable-cut bounds")

    def run_spec(self, output: Path, scout: Path, base: Path):
        self.validate()
        return {"schema": "crse-natural-variable-cut-run-spec/v1", "status": "planned",
            "output_directory": str(output.resolve()), "scout": str(scout.resolve()),
            "retained_c4_run": str(base.resolve()), "retained_c4_manifest_sha256": file_sha(base / "manifest.json"),
            "config": asdict(self), "device": "cpu", "architectures": list(ARCHITECTURES),
            "dataset": "exact regeneration of frozen C3/C4 94-pair structure-matched EPFL dataset",
            "model": {"message_direction": "bidirectional", "cut_readout": "shared per-variable head",
                "learned_absolute_variable_identity": False, "orientation_anchor": "x0",
                "equivariance": "permutations of non-anchor variables"},
            "controls": ["sound source interaction over-approximation", "exact source symbolic ANF",
                "truth-vector exact ANF", "always abstain", "retained C4 global cut GNN"],
            "selection": "same C4 seeds, pair batches, loss weights, epochs and validation-only threshold rule",
            "acceptance": "fresh truth vector plus exact candidate-partition witness",
            "criteria": {"classification": ">=0.65 BA for variable-cut-rank on both held-out splits/seeds",
                "accepted_partition": ">=0.30 positive recall on both held-out splits/seeds",
                "pair_ranking": ">=0.70 on both held-out splits/seeds",
                "c4_improvement": ">=0.10 accepted-positive recall over retained C4 cut-rank on every split/seed",
                "equivariance": "maximum fixed-anchor permutation output error <=1e-6",
                "learned_cost": "median safe learned path no slower than exact truth-vector ANF",
                "source_symbolic": "perfect classification and accepted-positive recall",
                "source_symbolic_cost": "median and p95 safe symbolic path no slower than truth-vector ANF",
                "safety": "zero accepted negatives and zero final semantic changes",
                "production_promotion": False},
            "limits": {"cooperative_wall_seconds": self.max_seconds, "cpu_threads": self.threads,
                "estimated_working_memory_bytes": self.estimated_working_memory_bytes,
                "max_variables": MAX_VARS, "max_parameters": 200_000, "network": False}}


def file_sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any):
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def write_jsonl(path: Path, rows):
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


def verify_c4(base: Path):
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "crse-natural-cut-ranking-artifacts/v1" or manifest.get("status") != "complete":
        raise ValueError("retained C4 run is not complete")
    actual = {path.name for path in base.iterdir() if path.is_file() and path.name != "manifest.json"}
    if set(manifest["files_sha256"]) != actual:
        raise ValueError("retained C4 inventory changed")
    for name, digest in manifest["files_sha256"].items():
        if file_sha(base / name) != digest:
            raise ValueError(f"retained C4 artifact changed: {name}")
    if summary.get("status") != "complete" or summary.get("accepted_semantic_mismatches") != 0:
        raise ValueError("retained C4 summary is incomplete or unsafe")
    return manifest, summary


def source_fingerprints(scout: Path):
    paths = [Path(__file__), ROOT / "cmbench" / "recognition" / "source_interaction.py",
        ROOT / "cmbench" / "recognition" / "models" / "natural_variable_cut_torch_models.py",
        ROOT / "cmbench" / "recognition" / "natural_cut_experiment.py",
        ROOT / "cmbench" / "recognition" / "natural_decomposition.py",
        ROOT / "cmbench" / "recognition" / "natural_decomposition_data.py",
        ROOT / "cmbench" / "recognition" / "natural_decomposition_experiment.py",
        ROOT / "cmbench" / "recognition" / "natural_decomposition_matched_data.py",
        ROOT / "cmbench" / "recognition" / "variable_graph_inputs.py", scout, EPFL_LICENSE]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): file_sha(path) for path in paths}


def batch_inputs(examples):
    return batch_graphs([graph_from_document(example.base.document, example.base.n_vars) for example in examples])


def forward(model, examples):
    return model(None, batch_inputs(examples))


def architecture_weights(architecture: str, config: NaturalVariableCutConfig):
    return {"classification": 1.0, "cut": config.cut_weight,
        "ranking": config.ranking_weight if architecture == "variable_cut_rank_gnn" else 0.0,
        "ranking_margin": config.ranking_margin}


def train_model(architecture, pairs, seed, config, budget, schedule):
    torch.manual_seed(seed); model = build_model(architecture); initial = state_sha256(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    weights = architecture_weights(architecture, config)
    losses, cut_losses, ranking_losses, steps = [], [], [], 0
    started = time.perf_counter_ns()
    for batches in schedule:
        model.train(); epoch_loss, epoch_cut, epoch_rank = [], [], []
        for indices in batches:
            budget.check(); selected = [pairs[index] for index in indices]
            batch = [item for pair in selected for item in pair]
            labels = torch.tensor([item.base.label for item in batch], dtype=torch.float32)
            logits, cut_logits, _embedding = forward(model, batch)
            classification_loss = F.binary_cross_entropy_with_logits(logits, labels)
            targets = torch.tensor([pair[0].row_target for pair in selected], dtype=torch.float32)
            masks = torch.tensor([pair[0].row_mask for pair in selected], dtype=torch.float32)
            element = F.binary_cross_entropy_with_logits(cut_logits[0::2], targets, reduction="none")
            cut_loss = (element * masks).sum() / masks.sum().clamp_min(1)
            ranking_loss = F.relu(weights["ranking_margin"] - logits[0::2] + logits[1::2]).mean()
            loss = classification_loss + weights["cut"] * cut_loss + weights["ranking"] * ranking_loss
            if not bool(torch.isfinite(loss)):
                raise ValueError("nonfinite variable-cut loss")
            optimizer.zero_grad(set_to_none=True); loss.backward(); optimizer.step()
            epoch_loss.append(float(loss.detach())); epoch_cut.append(float(cut_loss.detach()))
            epoch_rank.append(float(ranking_loss.detach())); steps += 1
        losses.append(statistics.fmean(epoch_loss)); cut_losses.append(statistics.fmean(epoch_cut))
        ranking_losses.append(statistics.fmean(epoch_rank))
    model.eval(); final = state_sha256(model)
    if final == initial:
        raise RuntimeError("variable-cut parameters did not update")
    return model, {"status": "complete", "task": "natural-variable-cut-ranking", "seed": seed,
        "epochs": config.epochs, "batch_pairs": config.batch_pairs, "steps": steps,
        "pairs": len(pairs), "rows": 2 * len(pairs), "optimizer": "Adam",
        "learning_rate": config.learning_rate,
        "loss": "classification + equivariant-variable-cut + same-pair-margin", "weights": weights,
        "loss_history": losses, "cut_loss_history": cut_losses,
        "ranking_loss_history": ranking_losses, "initial_state_sha256": initial,
        "final_state_sha256": final, "parameters_updated": True,
        "fit_ns": time.perf_counter_ns() - started}


def outputs(model, examples):
    with torch.no_grad():
        logits, cuts, _embedding = forward(model, examples)
        scores = torch.sigmoid(logits).cpu().tolist(); cut_scores = torch.sigmoid(cuts).cpu().tolist()
    return [(float(score), tuple(float(value) for value in cut)) for score, cut in zip(scores, cut_scores)]


def evaluation_row(model, architecture, example, seed, threshold):
    started = time.perf_counter_ns(); graph = batch_inputs([example]); represented = time.perf_counter_ns()
    with torch.no_grad():
        logits, cuts, _embedding = model(None, graph)
        score = float(torch.sigmoid(logits)[0]); probabilities = tuple(float(v) for v in torch.sigmoid(cuts)[0])
    inferred = time.perf_counter_ns(); partition, nll, margin = decode_direct_cut(probabilities, example.base.n_vars)
    proposed = score >= threshold; witness = None
    if proposed:
        bits = reference_bits(example.base.expr, example.base.n_vars)
        witness = partition_witness(bits, example.base.n_vars, partition)
    checked = time.perf_counter_ns(); accepted = proposed and witness is not None
    canonical = tuple(i for i, value in enumerate(example.row_target[:example.base.n_vars]) if value)
    return {"architecture": architecture, "seed": seed, "split": example.base.split,
        "pair_id": example.pair_id, "case_id": example.base.case_id, "circuit": example.base.circuit,
        "variant": example.base.variant, "n_vars": example.base.n_vars, "label": example.base.label,
        "score": score, "threshold": threshold, "predicted": int(proposed), "proposed": proposed,
        "row_variables": list(partition), "cut_nll": nll, "cut_margin": margin,
        "canonical_partition_match": bool(example.base.label and partition == canonical),
        "accepted": accepted, "fallback_used": not accepted,
        "check_reason": ("exact_variable_cut_witness" if accepted else
            "exact_variable_cut_rejection" if proposed else "model_abstention"),
        "semantic_mismatch": bool(accepted and not example.base.label),
        "original_bits_sha256": packed_sha256(example.base.bits, example.base.n_vars),
        "final_bits_sha256": packed_sha256(example.base.bits, example.base.n_vars),
        "representation_ns": represented - started, "inference_ns": inferred - represented,
        "exact_check_ns": checked - inferred, "total_ns": checked - started}


def equivariance_audit(model, examples):
    rows = []
    for example in examples[:8]:
        graph = batch_inputs([example])
        if example.base.n_vars < 3:
            continue
        permutation = list(range(MAX_VARS)); permutation[1], permutation[2] = 2, 1
        with torch.no_grad():
            original_class, original_cut, _ = model(None, graph)
        features = graph.node_features.clone()
        identity = graph.node_features[:, len(OPS):len(OPS) + MAX_VARS]
        renamed = torch.zeros_like(identity)
        for old, new in enumerate(permutation):
            renamed[:, new] = identity[:, old]
        features[:, len(OPS):len(OPS) + MAX_VARS] = renamed
        permuted = GraphBatch(features, graph.edge_index, graph.edge_roles, graph.graph_index, graph.roots, graph.ptr)
        with torch.no_grad():
            renamed_class, renamed_cut, _ = model(None, permuted)
        class_error = abs(float(original_class[0] - renamed_class[0]))
        cut_error = max(abs(float(original_cut[0, old] - renamed_cut[0, new]))
                        for old, new in enumerate(permutation))
        rows.append({"case_id": example.base.case_id, "class_error": class_error,
            "cut_permutation_error": cut_error, "maximum_error": max(class_error, cut_error)})
    return rows


def percentile95(values):
    ordered = sorted(values)
    return ordered[round(.95 * (len(ordered) - 1))]


def source_control_rows(examples, name, proposer):
    rows = []
    for example in examples:
        started = time.perf_counter_ns(); partition = proposer(example.base.document, example.base.n_vars)
        proposed_at = time.perf_counter_ns(); witness = None
        if partition is not None:
            bits = reference_bits(example.base.expr, example.base.n_vars)
            witness = partition_witness(bits, example.base.n_vars, partition)
        checked = time.perf_counter_ns(); accepted = partition is not None and witness is not None
        canonical = tuple(i for i, value in enumerate(example.row_target[:example.base.n_vars]) if value)
        rows.append({"control": name, "split": example.base.split, "case_id": example.base.case_id,
            "label": example.base.label, "row_variables": list(partition) if partition is not None else None,
            "proposed": partition is not None, "predicted": int(partition is not None), "accepted": accepted,
            "canonical_partition_match": bool(example.base.label and partition == canonical),
            "semantic_mismatch": bool(accepted and not example.base.label),
            "signature_ns": proposed_at - started, "exact_check_ns": checked - proposed_at,
            "total_ns": checked - started, "original_bits_sha256": packed_sha256(example.base.bits, example.base.n_vars),
            "final_bits_sha256": packed_sha256(example.base.bits, example.base.n_vars)})
    return rows


def summarize_source_controls(rows):
    grouped = defaultdict(list)
    for row in rows: grouped[(row["control"], row["split"])].append(row)
    result = {}
    for (name, split), group in sorted(grouped.items()):
        labels = [row["label"] for row in group]; predictions = [row["predicted"] for row in group]
        positives = sum(labels)
        result[f"{name}/{split}"] = {"cases": len(group),
            "balanced_accuracy": balanced_accuracy(labels, predictions),
            "sensitivity": sum(label and prediction for label, prediction in zip(labels, predictions)) / positives,
            "specificity": sum(not label and not prediction for label, prediction in zip(labels, predictions)) / (len(labels)-positives),
            "accepted_positive_recall": sum(row["label"] and row["accepted"] for row in group) / positives,
            "canonical_partition_recall": sum(row["canonical_partition_match"] for row in group) / positives,
            "proposals": sum(row["proposed"] for row in group), "accepted": sum(row["accepted"] for row in group),
            "median_signature_ns": statistics.median(row["signature_ns"] for row in group),
            "p95_signature_ns": percentile95([row["signature_ns"] for row in group]),
            "median_total_ns": statistics.median(row["total_ns"] for row in group),
            "p95_total_ns": percentile95([row["total_ns"] for row in group])}
    return result


def enhanced_exact_controls(examples):
    controls = exact_controls(examples)
    grouped = defaultdict(list)
    for row in controls["rows"]: grouped[row["split"]].append(row["elapsed_ns"])
    for split, values in grouped.items(): controls["summary"][split]["p95_exact_anf_ns"] = percentile95(values)
    return controls


def measured_criteria(classification, ranking, costs, source_summary, controls, c4, equivariance, seeds):
    value = lambda arch, seed, split, field: classification[f"{arch}/seed-{seed}/{split}"][field]
    rank = lambda arch, seed, split: ranking[f"{arch}/seed-{seed}/{split}"]["ranking_accuracy"]
    classification_ok = all(value("variable_cut_rank_gnn", seed, split, "balanced_accuracy") >= .65
        for seed in seeds for split in ("test", "confirmatory"))
    accepted_ok = all(value("variable_cut_rank_gnn", seed, split, "accepted_positive_recall") >= .30
        for seed in seeds for split in ("test", "confirmatory"))
    ranking_ok = all(rank("variable_cut_rank_gnn", seed, split) >= .70
        for seed in seeds for split in ("test", "confirmatory"))
    improvement_ok = all(value("variable_cut_rank_gnn", seed, split, "accepted_positive_recall") >=
        c4["classification"][f"cut_rank_gnn/seed-{seed}/{split}"]["accepted_positive_recall"] + .10
        for seed in seeds for split in ("test", "confirmatory"))
    learned_cost = all(costs[f"variable_cut_rank_gnn/seed-{seed}/{split}"]["safe_learned_over_exact_anf"] <= 1
        for seed in seeds for split in ("test", "confirmatory"))
    symbolic = all(source_summary[f"source_symbolic_anf/{split}"][field] == 1.0
        for split in ("test", "confirmatory") for field in ("balanced_accuracy", "accepted_positive_recall"))
    symbolic_cost = all(source_summary[f"source_symbolic_anf/{split}"]["median_total_ns"] <= controls[split]["median_exact_anf_ns"]
        and source_summary[f"source_symbolic_anf/{split}"]["p95_total_ns"] <= controls[split]["p95_exact_anf_ns"]
        for split in ("test", "confirmatory"))
    return {"classification": classification_ok, "accepted_partition": accepted_ok,
        "pair_ranking": ranking_ok, "c4_improvement": improvement_ok,
        "equivariance": max(row["maximum_error"] for rows in equivariance.values() for row in rows) <= 1e-6,
        "learned_cost": learned_cost, "source_symbolic": symbolic,
        "source_symbolic_cost": symbolic_cost, "safety": False, "production_promotion": False}


def run_natural_variable_cut_experiment(config, output: Path, scout: Path = DEFAULT_SCOUT,
                                        base: Path = DEFAULT_C4_RUN, progress=print):
    config.validate(); output = output.resolve(); scout = scout.resolve(); base = base.resolve()
    output.mkdir(parents=True, exist_ok=False); _base_manifest, c4 = verify_c4(base)
    write_json(output / "run_spec.json", config.run_spec(output, scout, base))
    before = source_fingerprints(scout); budget = Budget(config.max_seconds); started = time.perf_counter()
    torch.set_num_threads(config.threads)
    try: torch.set_num_interop_threads(1)
    except RuntimeError: pass
    progress("Regenerating frozen matched EPFL pairs")
    documents, provenance = make_matched_natural_documents(scout, seed=config.data_seed, check=budget.check)
    audit = validate_matched_documents(documents, check=budget.check)
    examples = cut_examples_from_documents(documents); write_json(output / "dataset.json", documents)
    write_json(output / "dataset_provenance.json", provenance)
    dataset_sha = hashlib.sha256(canonical(documents)).hexdigest()
    training_pairs = paired_examples(examples, "train")
    validation = [example for example in examples if example.base.split == "validation"]
    evaluation = [example for example in examples if example.base.split in ("test", "confirmatory")]
    pair_ids_sha = hashlib.sha256(canonical([pair[0].pair_id for pair in training_pairs])).hexdigest()
    schedules = {seed: pair_schedule(len(training_pairs), config, seed) for seed in config.training_seeds}
    rows, cards, calibration, equivariance = [], [], {}, {}
    for architecture in ARCHITECTURES:
        for seed in config.training_seeds:
            budget.check(); progress(f"Training {architecture}, seed {seed}")
            model, training = train_model(architecture, training_pairs, seed, config, budget, schedules[seed])
            training.update({"dataset_sha256": dataset_sha, "training_pair_ids_sha256": pair_ids_sha})
            validation_outputs = outputs(model, validation)
            threshold, balanced, false_positives = choose_threshold(validation, validation_outputs)
            calibration[f"{architecture}/seed-{seed}"] = {"threshold": threshold,
                "selection_split": "validation", "cases": len(validation),
                "balanced_accuracy": balanced, "false_positives": false_positives}
            filename = f"model-{architecture}-seed-{seed}.json"
            digest = save_model(model, architecture, training,
                {"torch": torch.__version__, "device": "cpu", "dtype": "float32"}, output / filename)
            name, restored, loaded_training, _metadata, loaded_digest = load_model(output / filename)
            if (name != architecture or loaded_training != training or loaded_digest != digest
                    or outputs(model, validation) != outputs(restored, validation)):
                raise ValueError("variable-cut model reload mismatch")
            cards.append({"architecture": architecture, "seed": seed, "file": filename,
                "parameters": parameter_count(restored), "artifact_sha256": digest,
                "fit_ns": training["fit_ns"], "final_loss": training["loss_history"][-1],
                "final_cut_loss": training["cut_loss_history"][-1],
                "final_ranking_loss": training["ranking_loss_history"][-1]})
            equivariance[f"{architecture}/seed-{seed}"] = equivariance_audit(restored, evaluation)
            for example in evaluation:
                budget.check(); rows.append(evaluation_row(restored, architecture, example, seed, threshold))
    write_json(output / "calibration.json", calibration); write_jsonl(output / "classification_raw.jsonl", rows)
    ranking = pair_ranking(rows); write_json(output / "pair_ranking.json", ranking)
    write_json(output / "equivariance.json", {"schema": "crse-natural-variable-cut-equivariance/v1", "rows": equivariance})
    source_rows = source_control_rows(evaluation, "source_overapprox", source_partition_proposal)
    source_rows += source_control_rows(evaluation, "source_symbolic_anf", source_exact_partition)
    write_jsonl(output / "source_controls_raw.jsonl", source_rows)
    source_summary = summarize_source_controls(source_rows); write_json(output / "source_controls.json", source_summary)
    controls = enhanced_exact_controls(evaluation); write_json(output / "controls.json", controls)
    classification = summarize(rows); costs = cost_ratios(classification, controls["summary"])
    criteria = measured_criteria(classification, ranking["summary"], costs, source_summary,
        controls["summary"], c4, equivariance, config.training_seeds)
    mismatches = sum(row["semantic_mismatch"] for row in rows + source_rows)
    criteria["safety"] = mismatches == 0 and all(row["original_bits_sha256"] == row["final_bits_sha256"]
                                                  for row in rows + source_rows)
    after = source_fingerprints(scout); status = "complete" if before == after and criteria["safety"] else "invalid"
    result = {"schema": RUN_SCHEMA, "status": status, "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0], "torch": torch.__version__,
        "config": asdict(config), "dataset_audit": audit, "dataset_provenance": provenance,
        "retained_c4": {"path": str(base.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": file_sha(base / "manifest.json")},
        "model_cards": cards, "calibration": calibration, "classification": classification,
        "pair_ranking": ranking["summary"], "equivariance": equivariance,
        "source_controls": source_summary, "controls": controls["summary"], "cost_ratios": costs,
        "row_count": len(rows), "source_control_row_count": len(source_rows),
        "proposal_reasons": dict(Counter(row["check_reason"] for row in rows)),
        "accepted_semantic_mismatches": mismatches, "criteria": criteria,
        "source_unchanged": before == after,
        "claims": {"permutation_equivariant_nonanchor_variables": True,
            "independent_dataset_family": False, "development_followup": True,
            "production_promotion": False}}
    write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    write_json(output / "manifest.json", {"schema": "crse-natural-variable-cut-artifacts/v1",
        "status": status, "files_sha256": {path.name: file_sha(path) for path in files},
        "source_sha256": before, "retained_c4_manifest_sha256": result["retained_c4"]["manifest_sha256"]})
    return result


def render_report(result):
    lines = ["# CRSE per-variable equivariant cut learning", "", f"Status: **{result['status']}**",
        f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Semantic mismatches: {result['accepted_semantic_mismatches']}", "",
        "| Architecture / seed / split | BA | Pair ranking | Accepted-positive recall | Canonical-cut recall | Safe learned / exact ANF |",
        "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for key, values in result["classification"].items():
        lines.append(f"| {key} | {values['balanced_accuracy']:.3f} | "
            f"{result['pair_ranking'][key]['ranking_accuracy']:.3f} | "
            f"{values['accepted_positive_recall']:.3f} | {values['canonical_partition_recall']:.3f} | "
            f"{result['cost_ratios'][key]['safe_learned_over_exact_anf']:.3f}x |")
    lines += ["", "## Deterministic source controls", "",
        "| Control / split | BA | Accepted-positive recall | Median total ns | p95 total ns |",
        "| --- | ---: | ---: | ---: | ---: |"]
    for key, values in result["source_controls"].items():
        lines.append(f"| {key} | {values['balanced_accuracy']:.3f} | "
            f"{values['accepted_positive_recall']:.3f} | {values['median_total_ns']:.0f} | {values['p95_total_ns']:.0f} |")
    lines += ["", "The learned input removes absolute variable identity from message features. A shared head scores context-rich variable nodes; x0 is the sole orientation anchor.",
        "The conservative source over-approximation can abstain when AIG lowering hides a cut. The symbolic source control computes exact ANF monomials over the bounded source DAG without materializing a truth vector.",
        "All learned and deterministic proposals retain exact witness acceptance. This is a matched EPFL development comparison, not independent-family confirmation or production promotion.", ""]
    return "\n".join(lines)
