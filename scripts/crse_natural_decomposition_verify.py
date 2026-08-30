"""Independent artifact/scalar verifier for natural decomposition learning."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.expr.eval import eval_expr_assignment
from cmbench.recognition.decomposition_data import packed_sha256
from cmbench.recognition.models.natural_torch_models import ARCHITECTURES, load_model, parameter_count
from cmbench.recognition.natural_decomposition_data import make_natural_decomposition_documents
from cmbench.recognition.natural_decomposition_experiment import (
    NaturalDecompositionConfig, choose_threshold, examples_from_documents, outputs,
    predicted_partition, source_fingerprints,
)


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path, limit=32 * 1024 * 1024):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key in {path}: {key}")
            result[key] = value
        return result
    raw = path.read_bytes()
    if len(raw) > limit:
        raise ValueError(f"bounded JSON limit exceeded: {path}")
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def read_jsonl(path: Path, cap: int):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
        if len(rows) > cap:
            raise ValueError(f"row cap exceeded: {path}")
    return rows


def scalar_bits(expr, n_vars: int):
    names = [f"x{index}" for index in range(n_vars)]
    result = 0
    for assignment_index in range(1 << n_vars):
        assignment = {name: (assignment_index >> (n_vars - 1 - index)) & 1
                      for index, name in enumerate(names)}
        result |= eval_expr_assignment(expr, assignment) << assignment_index
    return result


def independent_edges(bits: int, n_vars: int):
    coefficients = [(bits >> index) & 1 for index in range(1 << n_vars)]
    for position in range(n_vars):
        bit = 1 << position
        for mask in range(1 << n_vars):
            if mask & bit:
                coefficients[mask] ^= coefficients[mask ^ bit]
    edges = set()
    for mask, coefficient in enumerate(coefficients):
        if not coefficient:
            continue
        variables = [n_vars - 1 - position for position in range(n_vars) if mask & (1 << position)]
        for first in range(len(variables)):
            for second in range(first + 1, len(variables)):
                edges.add(tuple(sorted((variables[first], variables[second]))))
    return edges


def independent_decomposable(bits: int, n_vars: int):
    edges = independent_edges(bits, n_vars)
    seen = set()
    components = []
    adjacency = {variable: set() for variable in range(n_vars)}
    for left, right in edges:
        adjacency[left].add(right); adjacency[right].add(left)
    for variable in range(n_vars):
        if variable in seen:
            continue
        component, stack = [], [variable]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current); component.append(current); stack.extend(adjacency[current] - seen)
        components.append(tuple(sorted(component)))
    return len(components) > 1, tuple(sorted(components, key=lambda group: group[0]))


def independent_partition_check(bits: int, n_vars: int, row_variables):
    if row_variables is None:
        return False
    row = tuple(row_variables)
    column = tuple(variable for variable in range(n_vars) if variable not in row)
    def original_index(row_assignment, column_assignment):
        result = 0
        for local, variable in enumerate(row):
            result |= ((row_assignment >> (len(row) - 1 - local)) & 1) << (n_vars - 1 - variable)
        for local, variable in enumerate(column):
            result |= ((column_assignment >> (len(column) - 1 - local)) & 1) << (n_vars - 1 - variable)
        return result
    at = lambda r, c: (bits >> original_index(r, c)) & 1
    for r in range(1 << len(row)):
        for c in range(1 << len(column)):
            if at(r, c) ^ at(r, 0) ^ at(0, c) ^ at(0, 0):
                return False
    return True


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run = args.run.resolve()
    manifest = read_json(run / "manifest.json")
    summary = read_json(run / "summary.json")
    spec = read_json(run / "run_spec.json")
    if manifest.get("schema") != "crse-natural-decomposition-artifacts/v1" or manifest.get("status") != "complete":
        raise SystemExit("natural run manifest is not complete")
    actual = {path.name for path in run.iterdir() if path.is_file() and path.name != "manifest.json"}
    if set(manifest["files_sha256"]) != actual:
        raise SystemExit("natural artifact inventory mismatch")
    for name, digest in manifest["files_sha256"].items():
        if sha(run / name) != digest:
            raise SystemExit(f"natural artifact hash mismatch: {name}")
    if summary.get("schema") != "crse-natural-decomposition-learning-experiment/v1" or summary.get("status") != "complete":
        raise SystemExit("natural summary is not complete")
    config_data = spec["config"]
    config = NaturalDecompositionConfig(data_seed=config_data["data_seed"],
        training_seeds=tuple(config_data["training_seeds"]), epochs=config_data["epochs"],
        batch_size=config_data["batch_size"], learning_rate=config_data["learning_rate"],
        auxiliary_weight=config_data["auxiliary_weight"], threads=config_data["threads"],
        max_seconds=config_data["max_seconds"],
        estimated_working_memory_bytes=config_data["estimated_working_memory_bytes"])
    config.validate()
    scout = Path(spec["scout"])
    if config.max_seconds != 120 or config.threads != 2 or spec.get("status") != "planned":
        raise SystemExit("natural finite pre-run specification changed")
    if manifest["source_sha256"] != source_fingerprints(scout):
        raise SystemExit("natural implementation/source seal changed")

    documents = read_json(run / "dataset.json")
    regenerated, provenance = make_natural_decomposition_documents(scout, seed=config.data_seed)
    if documents != regenerated or read_json(run / "dataset_provenance.json") != provenance:
        raise SystemExit("natural dataset or provenance does not regenerate")
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
        if (bits != example.bits or int(decomposable) != example.label or target_edges != expected_edges
                or packed_sha256(bits, example.n_vars) != row["semantic_sha256"]
                or [list(group) for group in components] != row["components"]):
            raise SystemExit(f"natural independent scalar/ANF disagreement: {example.case_id}")
        scalar[example.case_id] = bits

    training = [example for example in examples if example.split == "train"]
    validation = [example for example in examples if example.split == "validation"]
    evaluation = [example for example in examples if example.split != "train"]
    expected_models = {(architecture, seed) for architecture in ARCHITECTURES for seed in config.training_seeds}
    cards = {(card["architecture"], card["seed"]): card for card in summary["model_cards"]}
    if set(cards) != expected_models:
        raise SystemExit("natural trained model inventory mismatch")
    reproduced = {}
    thresholds = {}
    for key, card in cards.items():
        architecture, seed = key
        name, model, training_data, _metadata, digest = load_model(run / card["file"])
        if (name != architecture or training_data["seed"] != seed or training_data["rows"] != len(training)
                or digest != card["artifact_sha256"] or parameter_count(model) != card["parameters"]):
            raise SystemExit(f"natural model provenance mismatch: {key}")
        validation_outputs = outputs(model, architecture, validation)
        threshold, accuracy = choose_threshold(validation, validation_outputs,
                                               architecture == "natural_multitask_gnn")
        retained_calibration = summary["calibration"][f"{architecture}/seed-{seed}"]
        if (threshold != retained_calibration["threshold"]
                or accuracy != retained_calibration["balanced_accuracy_at_selected_threshold"]):
            raise SystemExit(f"natural validation calibration mismatch: {key}")
        thresholds[key] = threshold
        for example, model_output in zip(evaluation, outputs(model, architecture, evaluation)):
            reproduced[(architecture, seed, example.case_id)] = model_output

    rows = read_jsonl(run / "classification_raw.jsonl", 2_000)
    if len(rows) != len(expected_models) * len(evaluation) or summary["row_count"] != len(rows):
        raise SystemExit("natural classification row count mismatch")
    seen, reasons = set(), Counter()
    for row in rows:
        key = (row["architecture"], row["seed"], row["case_id"])
        if key in seen or key not in reproduced:
            raise SystemExit("duplicate or unknown natural classification row")
        seen.add(key)
        example = by_id[row["case_id"]]
        score, edge_scores = reproduced[key]
        partition = predicted_partition(edge_scores, example.n_vars) if edge_scores is not None else None
        proposed = score >= thresholds[(row["architecture"], row["seed"])] and (edge_scores is None or partition is not None)
        accepted = (independent_decomposable(scalar[example.case_id], example.n_vars)[0]
                    if proposed and partition is None else
                    independent_partition_check(scalar[example.case_id], example.n_vars, partition) if proposed else False)
        if (abs(row["score"] - score) > 5e-6 or row["predicted"] != int(proposed)
                or row["proposed"] != proposed or row["accepted"] != accepted
                or row["predicted_row_variables"] != (list(partition) if partition is not None else None)
                or row["label"] != example.label or row["semantic_mismatch"]
                or row["original_bits_sha256"] != packed_sha256(scalar[example.case_id], example.n_vars)
                or row["final_bits_sha256"] != row["original_bits_sha256"]):
            raise SystemExit(f"natural classification exactness mismatch: {key}")
        reasons[row["check_reason"]] += 1
    controls = read_json(run / "controls.json")
    if (len(controls["rows"]) != len(evaluation) or any(not row["correct"] for row in controls["rows"])
            or summary["accepted_semantic_mismatches"] != 0
            or summary["proposal_reasons"] != dict(reasons) or not summary["source_unchanged"]):
        raise SystemExit("natural exact-control or summary consistency mismatch")
    result = {"schema": "crse-natural-decomposition-independent-verification/v1", "status": "pass",
        "run": str(run), "manifest_sha256": sha(run / "manifest.json"), "models_loaded": len(cards),
        "dataset_rows_regenerated": len(documents), "scalar_truth_tables_recomputed": len(examples),
        "classification_rows_recomputed": len(rows), "exact_control_rows_checked": len(controls["rows"]),
        "natural_positive_count": sum(example.label for example in examples),
        "natural_negative_count": len(examples) - sum(example.label for example in examples),
        "semantic_mismatches": 0, "limits": {"max_variables": 10, "threads": 2,
            "wall_seconds": summary["wall_seconds"], "max_parameters": max(card["parameters"] for card in cards.values())}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
