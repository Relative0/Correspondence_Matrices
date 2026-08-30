"""Independent replay verifier for the structure-matched EPFL experiment."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.decomposition_data import packed_sha256
from cmbench.recognition.models.natural_torch_models import ARCHITECTURES, load_model, parameter_count
from cmbench.recognition.natural_decomposition_experiment import (
    NaturalDecompositionConfig,
    choose_threshold,
    examples_from_documents,
    outputs,
    predicted_partition,
)
from cmbench.recognition.natural_decomposition_matched_data import make_matched_natural_documents
from cmbench.recognition.natural_decomposition_matched_experiment import source_fingerprints
from crse_natural_decomposition_verify import (
    independent_decomposable,
    independent_edges,
    independent_partition_check,
    read_json,
    read_jsonl,
    scalar_bits,
    sha,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run = args.run.resolve()

    manifest = read_json(run / "manifest.json")
    summary = read_json(run / "summary.json")
    spec = read_json(run / "run_spec.json")
    if manifest.get("schema") != "crse-natural-decomposition-matched-artifacts/v1" or manifest.get("status") != "complete":
        raise SystemExit("matched natural run manifest is not complete")
    actual = {path.name for path in run.iterdir() if path.is_file() and path.name != "manifest.json"}
    if set(manifest["files_sha256"]) != actual:
        raise SystemExit("matched natural artifact inventory mismatch")
    for name, digest in manifest["files_sha256"].items():
        if sha(run / name) != digest:
            raise SystemExit(f"matched natural artifact hash mismatch: {name}")
    if summary.get("schema") != "crse-natural-decomposition-matched-learning/v1" or summary.get("status") != "complete":
        raise SystemExit("matched natural summary is not complete")

    config_data = spec["config"]
    config = NaturalDecompositionConfig(
        data_seed=config_data["data_seed"],
        training_seeds=tuple(config_data["training_seeds"]),
        epochs=config_data["epochs"],
        batch_size=config_data["batch_size"],
        learning_rate=config_data["learning_rate"],
        auxiliary_weight=config_data["auxiliary_weight"],
        threads=config_data["threads"],
        max_seconds=config_data["max_seconds"],
        estimated_working_memory_bytes=config_data["estimated_working_memory_bytes"],
    )
    config.validate()
    scout = Path(spec["scout"])
    if config.max_seconds != 120 or config.threads != 2 or spec.get("status") != "planned":
        raise SystemExit("matched natural finite pre-run specification changed")
    if manifest["source_sha256"] != source_fingerprints(scout):
        raise SystemExit("matched natural implementation/source seal changed")

    documents = read_json(run / "dataset.json")
    regenerated, provenance = make_matched_natural_documents(scout, seed=config.data_seed)
    if documents != regenerated or read_json(run / "dataset_provenance.json") != provenance:
        raise SystemExit("matched natural dataset or provenance does not regenerate")
    examples = examples_from_documents(documents)
    by_id = {example.case_id: example for example in examples}
    scalar = {}
    for row, example in zip(documents, examples):
        bits = scalar_bits(example.expr, example.n_vars)
        decomposable, components = independent_decomposable(bits, example.n_vars)
        target_edges = independent_edges(bits, example.n_vars)
        expected_edges = set()
        index = 0
        for left in range(10):
            for right in range(left + 1, 10):
                if row["interaction_mask"][index] and row["interaction_target"][index]:
                    expected_edges.add((left, right))
                index += 1
        if (
            bits != example.bits
            or int(decomposable) != example.label
            or target_edges != expected_edges
            or packed_sha256(bits, example.n_vars) != row["semantic_sha256"]
            or [list(group) for group in components] != row["components"]
        ):
            raise SystemExit(f"matched natural scalar/ANF disagreement: {example.case_id}")
        scalar[example.case_id] = bits

    training = [example for example in examples if example.split == "train"]
    validation = [example for example in examples if example.split == "validation"]
    evaluation = [example for example in examples if example.split != "train"]
    expected_models = {(architecture, seed) for architecture in ARCHITECTURES for seed in config.training_seeds}
    cards = {(card["architecture"], card["seed"]): card for card in summary["model_cards"]}
    if set(cards) != expected_models:
        raise SystemExit("matched natural trained model inventory mismatch")

    reproduced = {}
    thresholds = {}
    for key, card in cards.items():
        architecture, seed = key
        name, model, training_data, _metadata, digest = load_model(run / card["file"])
        if (
            name != architecture
            or training_data["seed"] != seed
            or training_data["rows"] != len(training)
            or digest != card["artifact_sha256"]
            or parameter_count(model) != card["parameters"]
        ):
            raise SystemExit(f"matched natural model provenance mismatch: {key}")
        threshold, accuracy = choose_threshold(
            validation,
            outputs(model, architecture, validation),
            architecture == "natural_multitask_gnn",
        )
        retained = summary["calibration"][f"{architecture}/seed-{seed}"]
        if threshold != retained["threshold"] or accuracy != retained["balanced_accuracy_at_selected_threshold"]:
            raise SystemExit(f"matched natural validation calibration mismatch: {key}")
        thresholds[key] = threshold
        for example, model_output in zip(evaluation, outputs(model, architecture, evaluation)):
            reproduced[(architecture, seed, example.case_id)] = model_output

    rows = read_jsonl(run / "classification_raw.jsonl", 2_000)
    if len(rows) != len(expected_models) * len(evaluation) or summary["row_count"] != len(rows):
        raise SystemExit("matched natural classification row count mismatch")
    seen, reasons = set(), Counter()
    for row in rows:
        key = (row["architecture"], row["seed"], row["case_id"])
        if key in seen or key not in reproduced:
            raise SystemExit("duplicate or unknown matched natural classification row")
        seen.add(key)
        example = by_id[row["case_id"]]
        score, edge_scores = reproduced[key]
        partition = predicted_partition(edge_scores, example.n_vars) if edge_scores is not None else None
        proposed = score >= thresholds[(row["architecture"], row["seed"])] and (
            edge_scores is None or partition is not None
        )
        accepted = (
            independent_decomposable(scalar[example.case_id], example.n_vars)[0]
            if proposed and partition is None
            else independent_partition_check(scalar[example.case_id], example.n_vars, partition)
            if proposed
            else False
        )
        if (
            abs(row["score"] - score) > 5e-6
            or row["predicted"] != int(proposed)
            or row["proposed"] != proposed
            or row["accepted"] != accepted
            or row["predicted_row_variables"] != (list(partition) if partition is not None else None)
            or row["label"] != example.label
            or row["semantic_mismatch"]
            or row["original_bits_sha256"] != packed_sha256(scalar[example.case_id], example.n_vars)
            or row["final_bits_sha256"] != row["original_bits_sha256"]
        ):
            raise SystemExit(f"matched natural classification exactness mismatch: {key}")
        reasons[row["check_reason"]] += 1

    controls = read_json(run / "controls.json")
    if (
        len(controls["rows"]) != len(evaluation)
        or any(not row["correct"] for row in controls["rows"])
        or summary["accepted_semantic_mismatches"] != 0
        or summary["proposal_reasons"] != dict(reasons)
        or not summary["source_unchanged"]
    ):
        raise SystemExit("matched natural control or summary consistency mismatch")

    positive_count = sum(example.label for example in examples)
    result = {
        "schema": "crse-natural-decomposition-matched-independent-verification/v1",
        "status": "pass",
        "run": str(run),
        "manifest_sha256": sha(run / "manifest.json"),
        "models_loaded": len(cards),
        "dataset_rows_regenerated": len(documents),
        "scalar_truth_tables_recomputed": len(examples),
        "classification_rows_recomputed": len(rows),
        "exact_control_rows_checked": len(controls["rows"]),
        "natural_positive_count": positive_count,
        "natural_negative_count": len(examples) - positive_count,
        "matched_pairs": summary["dataset_audit"]["matched_pairs"],
        "semantic_mismatches": 0,
        "limits": {
            "max_variables": 10,
            "threads": 2,
            "wall_seconds": summary["wall_seconds"],
            "max_parameters": max(card["parameters"] for card in cards.values()),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
