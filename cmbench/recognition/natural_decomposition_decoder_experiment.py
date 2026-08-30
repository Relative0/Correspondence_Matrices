"""Validation-only minimum-cut decoder for retained natural multitask models."""
from __future__ import annotations

import hashlib
import json
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .decomposition_data import canonical, packed_sha256
from .models.natural_torch_models import load_model
from .natural_decomposition import partition_witness
from .natural_decomposition_experiment import examples_from_documents, outputs
from .portfolio import reference_bits

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_RUN = ROOT / "docs" / "recognition" / "runs" / "natural-decomposition-20260829-001"
RUN_SCHEMA = "crse-natural-decomposition-mincut-decoder/v1"


@dataclass(frozen=True)
class DecoderConfig:
    max_seconds: float = 60.0
    max_variables: int = 10
    model_architecture: str = "natural_multitask_gnn"
    training_seeds: tuple[int, int] = (619, 887)

    def validate(self):
        if (not 0 < self.max_seconds <= 60 or self.max_variables != 10
                or self.model_architecture != "natural_multitask_gnn"
                or self.training_seeds != (619, 887)):
            raise ValueError("invalid frozen decoder bounds")


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any):
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def _write_jsonl(path: Path, rows):
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_base_run(base: Path):
    manifest = read_json(base / "manifest.json")
    summary = read_json(base / "summary.json")
    if manifest.get("schema") != "crse-natural-decomposition-artifacts/v1" or manifest.get("status") != "complete":
        raise ValueError("base natural decomposition run is not complete")
    actual = {path.name for path in base.iterdir() if path.is_file() and path.name != "manifest.json"}
    if set(manifest["files_sha256"]) != actual:
        raise ValueError("base natural artifact inventory changed")
    for name, digest in manifest["files_sha256"].items():
        if sha(base / name) != digest:
            raise ValueError(f"base natural artifact changed: {name}")
    if summary.get("status") != "complete" or summary.get("accepted_semantic_mismatches") != 0:
        raise ValueError("base natural summary is unsafe or incomplete")
    return manifest, summary


def minimum_cut_partition(edge_scores: tuple[float, ...], n_vars: int):
    if len(edge_scores) != 45 or not 2 <= n_vars <= 10:
        raise ValueError("invalid bounded interaction scores")
    edge = {}
    index = 0
    for left in range(10):
        for right in range(left + 1, 10):
            if right < n_vars:
                edge[(left, right)] = edge_scores[index]
            index += 1
    candidates = []
    # x0 stays on the row side to remove A|B/B|A duplicates.
    for rest_mask in range(1 << (n_vars - 1)):
        row = (0,) + tuple(variable for variable in range(1, n_vars)
                           if rest_mask & (1 << (variable - 1)))
        if len(row) == n_vars:
            continue
        row_set = set(row)
        crossing = [score for (left, right), score in edge.items() if (left in row_set) != (right in row_set)]
        if not crossing:
            continue
        mean_cross = statistics.fmean(crossing)
        candidates.append((mean_cross, abs(len(row) - (n_vars - len(row))), max(len(row), n_vars - len(row)), row))
    if not candidates:
        raise ValueError("no bounded nontrivial cut")
    score, _imbalance, _largest, row = min(candidates)
    return row, float(score)


def _balanced_accuracy(labels, predictions):
    positives, negatives = sum(labels), len(labels) - sum(labels)
    return .5 * (sum(label and prediction for label, prediction in zip(labels, predictions)) / positives
                 + sum(not label and not prediction for label, prediction in zip(labels, predictions)) / negatives)


def _thresholds(values):
    ordered = sorted(set(values))
    result = {0.0, .5, 1.0}
    result.update((left + right) / 2 for left, right in zip(ordered, ordered[1:]))
    return sorted(result)


def calibrate(examples, model_outputs):
    decoded = [(score, *minimum_cut_partition(edges, example.n_vars))
               for example, (score, edges) in zip(examples, model_outputs)]
    candidates = []
    labels = [example.label for example in examples]
    for class_threshold in _thresholds([row[0] for row in decoded]):
        for cut_threshold in _thresholds([row[2] for row in decoded]):
            predictions = [int(score >= class_threshold and cut_score <= cut_threshold)
                           for score, _partition, cut_score in decoded]
            balanced = _balanced_accuracy(labels, predictions)
            false_positives = sum(not label and prediction for label, prediction in zip(labels, predictions))
            candidates.append((balanced, -false_positives, -abs(class_threshold - .5),
                               -abs(cut_threshold - .5), -class_threshold, -cut_threshold,
                               class_threshold, cut_threshold))
    best = max(candidates)
    return {"class_threshold": best[6], "cut_threshold": best[7],
            "validation_balanced_accuracy": best[0], "validation_false_positives": -best[1],
            "selection": "maximum proposal balanced accuracy, then fewer false positives, thresholds nearest 0.5"}


def evaluate(example, score, edge_scores, seed: int, calibration):
    started = time.perf_counter_ns()
    partition, cut_score = minimum_cut_partition(edge_scores, example.n_vars)
    decoded = time.perf_counter_ns()
    proposed = score >= calibration["class_threshold"] and cut_score <= calibration["cut_threshold"]
    witness = None
    if proposed:
        bits = reference_bits(example.expr, example.n_vars)
        witness = partition_witness(bits, example.n_vars, partition)
    checked = time.perf_counter_ns()
    accepted = proposed and witness is not None
    return {"seed": seed, "split": example.split, "case_id": example.case_id,
        "circuit": example.circuit, "variant": example.variant, "n_vars": example.n_vars,
        "label": example.label, "class_score": score, "cut_score": cut_score,
        "class_threshold": calibration["class_threshold"], "cut_threshold": calibration["cut_threshold"],
        "row_variables": list(partition), "proposed": proposed, "predicted": int(proposed),
        "accepted": accepted, "fallback_used": not accepted,
        "check_reason": ("exact_mincut_partition_witness" if accepted else
                         "exact_mincut_partition_rejection" if proposed else "decoder_abstention"),
        "semantic_mismatch": bool(accepted and not example.label),
        "original_bits_sha256": packed_sha256(example.bits, example.n_vars),
        "final_bits_sha256": packed_sha256(example.bits, example.n_vars),
        "decode_ns": decoded - started, "exact_check_ns": checked - decoded,
        "total_ns": checked - started}


def summarize(rows):
    grouped = defaultdict(list)
    for row in rows: grouped[(row["seed"], row["split"])].append(row)
    result = {}
    for (seed, split), group in sorted(grouped.items()):
        labels = [row["label"] for row in group]; predictions = [row["predicted"] for row in group]
        positives, negatives = sum(labels), len(labels) - sum(labels)
        result[f"seed-{seed}/{split}"] = {"cases": len(group),
            "proposal_balanced_accuracy": _balanced_accuracy(labels, predictions),
            "proposal_sensitivity": sum(label and prediction for label, prediction in zip(labels, predictions)) / positives,
            "proposal_specificity": sum(not label and not prediction for label, prediction in zip(labels, predictions)) / negatives,
            "accepted_positive_recall": sum(label and row["accepted"] for label, row in zip(labels, group)) / positives,
            "wrong_partition_rejections": sum(row["proposed"] and not row["accepted"] and row["label"] for row in group),
            "negative_proposal_rejections": sum(row["proposed"] and not row["label"] for row in group),
            "proposals": sum(row["proposed"] for row in group), "accepted": sum(row["accepted"] for row in group),
            "fallbacks": sum(row["fallback_used"] for row in group),
            "median_decode_ns": statistics.median(row["decode_ns"] for row in group),
            "median_exact_check_ns": statistics.median(row["exact_check_ns"] for row in group),
            "median_total_ns": statistics.median(row["total_ns"] for row in group)}
    return result


def run_decoder_experiment(config: DecoderConfig, output: Path, base: Path = DEFAULT_BASE_RUN, progress=print):
    config.validate(); output = output.resolve(); base = base.resolve()
    output.mkdir(parents=True, exist_ok=False)
    base_manifest, base_summary = verify_base_run(base)
    spec = {"schema": "crse-natural-decomposition-decoder-run-spec/v1", "status": "planned",
        "config": asdict(config), "base_run": str(base), "base_manifest_sha256": sha(base / "manifest.json"),
        "training": "none; frozen retained multitask model artifacts", "selection_split": "validation only",
        "decoder": "enumerate bounded A|B cuts containing x0; minimize mean predicted cross-edge probability; validation-calibrate class and cut thresholds",
        "evaluation": ["test", "confirmatory"], "production_promotion": False}
    _write_json(output / "run_spec.json", spec)
    documents = read_json(base / "dataset.json")
    examples = examples_from_documents(documents)
    validation = [example for example in examples if example.split == "validation"]
    evaluation = [example for example in examples if example.split in ("test", "confirmatory")]
    cards = {(card["architecture"], card["seed"]): card for card in base_summary["model_cards"]}
    rows, calibrations, model_artifacts = [], {}, []
    started = time.perf_counter()
    for seed in config.training_seeds:
        if time.perf_counter() - started >= config.max_seconds:
            raise TimeoutError("decoder experiment wall budget exhausted")
        card = cards[(config.model_architecture, seed)]
        name, model, training, _metadata, digest = load_model(base / card["file"])
        if name != config.model_architecture or training["seed"] != seed or digest != card["artifact_sha256"]:
            raise ValueError("frozen multitask model identity mismatch")
        progress(f"Calibrating minimum-cut decoder, seed {seed}")
        calibration = calibrate(validation, outputs(model, name, validation))
        calibrations[f"seed-{seed}"] = calibration
        model_artifacts.append({"seed": seed, "path": str((base / card["file"]).relative_to(ROOT)).replace("\\", "/"),
                                "sha256": sha(base / card["file"]), "payload_sha256": digest})
        for example, (score, edge_scores) in zip(evaluation, outputs(model, name, evaluation)):
            rows.append(evaluate(example, score, edge_scores, seed, calibration))
    _write_json(output / "decoder_calibration.json", calibrations); _write_jsonl(output / "decoder_raw.jsonl", rows)
    summaries = summarize(rows)
    criteria = {"proposal_balanced_accuracy": all(summaries[f"seed-{seed}/{split}"]["proposal_balanced_accuracy"] >= .70
        for seed in config.training_seeds for split in ("test", "confirmatory")),
        "accepted_positive_recall": all(summaries[f"seed-{seed}/{split}"]["accepted_positive_recall"] >= .50
        for seed in config.training_seeds for split in ("test", "confirmatory")),
        "safety": all(not row["semantic_mismatch"] for row in rows), "production_promotion": False}
    result = {"schema": RUN_SCHEMA, "status": "complete" if criteria["safety"] else "invalid",
        "wall_seconds": time.perf_counter() - started, "base_run": str(base.relative_to(ROOT)).replace("\\", "/"),
        "base_manifest_sha256": sha(base / "manifest.json"), "model_artifacts": model_artifacts,
        "calibration": calibrations, "summaries": summaries, "row_count": len(rows),
        "proposal_reasons": dict(Counter(row["check_reason"] for row in rows)),
        "semantic_mismatches": sum(row["semantic_mismatch"] for row in rows), "criteria": criteria,
        "claims": {"model_retrained": False, "test_or_confirmatory_used_for_calibration": False,
                   "independent_dataset_family": False, "production_promotion": False}}
    _write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-natural-decomposition-decoder-artifacts/v1",
        "status": result["status"], "files_sha256": {path.name: sha(path) for path in files},
        "base_manifest_sha256": result["base_manifest_sha256"]})
    return result


def render_report(result):
    lines = ["# CRSE natural decomposition minimum-cut decoder", "",
        f"Status: **{result['status']}**", f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Semantic mismatches: {result['semantic_mismatches']}", "",
        "| Seed / split | Cases | Proposal balanced accuracy | Sensitivity | Specificity | Accepted-positive recall | Median decode ns |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for key, values in result["summaries"].items():
        lines.append(f"| {key} | {values['cases']} | {values['proposal_balanced_accuracy']:.3f} | "
            f"{values['proposal_sensitivity']:.3f} | {values['proposal_specificity']:.3f} | "
            f"{values['accepted_positive_recall']:.3f} | {values['median_decode_ns']:.0f} |")
    lines += ["", "The decoder uses frozen model edge probabilities. It performs no training and calibrates class/cut thresholds on validation only.",
        "Each bounded cut contains x0 to remove complement duplicates. The candidate minimizes mean predicted cross-edge probability, with balance and lexical tie breaks.",
        "Exact truth recomputation and a full candidate-partition witness still decide acceptance. This is a development decoder study, not independent-family confirmation or production promotion.", ""]
    return "\n".join(lines)
