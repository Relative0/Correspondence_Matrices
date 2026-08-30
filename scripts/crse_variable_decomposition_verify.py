"""Independent scalar and artifact verifier for the CRSE C2 retained run."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.expr.eval import eval_expr_assignment
from cmbench.recognition.decomposition_data import (
    compose_xor_factors, make_decomposition_documents, packed_sha256, xor_partition_witness,
)
from cmbench.recognition.models.variable_torch_models import ARCHITECTURES, load_model, parameter_count
from cmbench.recognition.variable_decomposition_experiment import (
    VariableDecompositionConfig, choose_threshold, generated_examples, natural_examples, scores,
    source_fingerprints,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path, limit: int = 32 * 1024 * 1024):
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


def scalar_bits(expr, n_vars: int) -> int:
    result = 0
    names = [f"x{index}" for index in range(n_vars)]
    for assignment_index in range(1 << n_vars):
        assignment = {name: (assignment_index >> (n_vars - 1 - index)) & 1
                      for index, name in enumerate(names)}
        result |= eval_expr_assignment(expr, assignment) << assignment_index
    return result


def independent_witness(bits: int, n_vars: int):
    rows = 1 << (n_vars // 2)
    columns = 1 << (n_vars - n_vars // 2)
    values = [[(bits >> (row * columns + column)) & 1 for column in range(columns)] for row in range(rows)]
    for row in range(1, rows):
        for column in range(1, columns):
            if values[row][column] ^ values[row][0] ^ values[0][column] ^ values[0][0]:
                return None
    row_factor = sum((values[row][0] ^ values[0][0]) << row for row in range(rows))
    column_factor = sum(values[0][column] << column for column in range(columns))
    return {"partition": [n_vars // 2, n_vars - n_vars // 2], "row_factor_bits": row_factor,
            "column_factor_bits": column_factor, "stored_factor_bits": rows + columns,
            "full_truth_bits": rows * columns}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run = args.run.resolve()
    manifest = read_json(run / "manifest.json")
    summary = read_json(run / "summary.json")
    spec = read_json(run / "run_spec.json")
    if manifest.get("schema") != "crse-variable-decomposition-artifacts/v1" or manifest.get("status") != "complete":
        raise SystemExit("run artifact manifest is not complete")
    actual = {path.name for path in run.iterdir() if path.is_file() and path.name != "manifest.json"}
    if set(manifest["files_sha256"]) != actual:
        raise SystemExit("artifact inventory differs from manifest")
    for name, digest in manifest["files_sha256"].items():
        if sha(run / name) != digest:
            raise SystemExit(f"artifact hash mismatch: {name}")
    if summary.get("schema") != "crse-variable-decomposition-experiment/v1" or summary.get("status") != "complete":
        raise SystemExit("summary is not a complete C2 experiment")
    config_data = spec.get("config", {})
    config = VariableDecompositionConfig(
        data_seed=config_data["data_seed"], training_seeds=tuple(config_data["training_seeds"]),
        parent_counts=tuple(config_data["parent_counts"]), epochs=config_data["epochs"],
        batch_size=config_data["batch_size"], learning_rate=config_data["learning_rate"],
        epfl_limit=config_data["epfl_limit"], threads=config_data["threads"],
        max_seconds=config_data["max_seconds"],
        estimated_working_memory_bytes=config_data["estimated_working_memory_bytes"])
    config.validate()
    if config.max_seconds != 120 or config.threads != 2 or spec.get("status") != "planned":
        raise SystemExit("finite pre-run specification missing or altered")
    if manifest.get("source_sha256") != source_fingerprints():
        raise SystemExit("frozen implementation or input source changed")

    documents = read_json(run / "generated_corpus.json")
    regenerated = make_decomposition_documents(config.data_seed, config.parent_counts)
    if documents != regenerated:
        raise SystemExit("generated corpus does not reproduce")
    generated = generated_examples(documents)
    natural, natural_manifest = natural_examples(config.epfl_limit)
    retained_natural = read_json(run / "epfl_evaluation_manifest.json")
    # JSON object keys are strings on disk; the upstream helper's Counter
    # summary has integer label keys in memory.
    normalized_natural_manifest = json.loads(json.dumps(natural_manifest, allow_nan=False))
    if retained_natural != normalized_natural_manifest:
        raise SystemExit("frozen natural evaluation selection changed")
    examples = generated + natural
    by_id = {example.case_id: example for example in examples}
    scalar = {}
    for example in examples:
        bits = scalar_bits(example.expr, example.n_vars)
        witness = independent_witness(bits, example.n_vars)
        if (bits != example.bits or witness != xor_partition_witness(bits, example.n_vars)
                or int(witness is not None) != example.label
                or (witness is not None and compose_xor_factors(witness, example.n_vars) != bits)):
            raise SystemExit(f"independent scalar/witness disagreement: {example.case_id}")
        scalar[example.case_id] = bits

    training = [example for example in generated if example.split == "train"]
    validation = [example for example in generated if example.split == "validation"]
    evaluation = [example for example in generated if example.split in ("validation", "test", "confirmatory")] + natural
    expected_models = {(architecture, seed) for architecture in ARCHITECTURES for seed in config.training_seeds}
    cards = {(card["architecture"], card["seed"]): card for card in summary["model_cards"]}
    if set(cards) != expected_models:
        raise SystemExit("trained model inventory mismatch")
    predicted_scores = {}
    thresholds = {}
    for key, card in cards.items():
        architecture, seed = key
        name, model, provenance, _metadata, digest = load_model(run / card["file"])
        if (name != architecture or provenance["seed"] != seed or digest != card["artifact_sha256"]
                or parameter_count(model) != card["parameters"] or provenance["rows"] != len(training)):
            raise SystemExit(f"model provenance mismatch: {key}")
        validation_values = scores(model, architecture, validation)
        threshold, accuracy = choose_threshold([example.label for example in validation], validation_values)
        calibration = summary["calibration"][f"{architecture}/seed-{seed}"]
        if threshold != calibration["threshold"] or accuracy != calibration["balanced_accuracy_at_selected_threshold"]:
            raise SystemExit(f"validation-only calibration mismatch: {key}")
        thresholds[key] = threshold
        values = scores(model, architecture, evaluation)
        for example, value in zip(evaluation, values):
            predicted_scores[(architecture, seed, example.case_id)] = value

    rows = read_jsonl(run / "classification_raw.jsonl", 2_000)
    expected_rows = len(expected_models) * len(evaluation)
    if len(rows) != expected_rows or summary["row_count"] != expected_rows:
        raise SystemExit("classification row count mismatch")
    seen, reasons = set(), Counter()
    for row in rows:
        key = (row["architecture"], row["seed"], row["case_id"])
        if key in seen or key not in predicted_scores:
            raise SystemExit("duplicate or unknown classification row")
        seen.add(key)
        example = by_id[row["case_id"]]
        score = predicted_scores[key]
        proposed = score >= thresholds[(row["architecture"], row["seed"])]
        witness = independent_witness(scalar[example.case_id], example.n_vars) if proposed else None
        accepted = proposed and witness is not None
        # BLAS accumulation differs slightly between retained single-example
        # inference and this bounded batch recomputation.  The decision itself
        # must still be identical.
        if (abs(row["score"] - score) > 5e-6 or row["threshold"] != thresholds[(row["architecture"], row["seed"])]
                or row["predicted"] != int(proposed) or row["proposed"] != proposed or row["accepted"] != accepted
                or row["label"] != example.label or row["n_vars"] != example.n_vars
                or row["original_bits_sha256"] != packed_sha256(scalar[example.case_id], example.n_vars)
                or row["final_bits_sha256"] != row["original_bits_sha256"] or row["semantic_mismatch"]
                or (accepted and row["witness_matches"] is not True)):
            raise SystemExit(f"classification exactness mismatch: {key}")
        reasons[row["check_reason"]] += 1
    controls = read_json(run / "controls.json")
    if (len(controls["rows"]) != len(evaluation)
            or any(not row["correct"] for row in controls["rows"])
            or any(row["witness_matches"] is False for row in controls["rows"])
            or summary["accepted_semantic_mismatches"] != 0 or summary["witness_mismatches"] != 0
            or summary["proposal_reasons"] != dict(reasons) or not summary["source_unchanged"]):
        raise SystemExit("control or summary consistency mismatch")

    result = {"schema": "crse-variable-decomposition-independent-verification/v1", "status": "pass",
        "run": str(run), "manifest_sha256": sha(run / "manifest.json"),
        "models_loaded": len(cards), "generated_functions_regenerated": len(generated),
        "natural_functions_reloaded": len(natural), "scalar_truth_tables_recomputed": len(examples),
        "classification_rows_recomputed": len(rows), "exact_control_rows_checked": len(controls["rows"]),
        "semantic_mismatches": 0, "witness_mismatches": 0,
        "limits": {"max_variables": 10, "threads": 2, "wall_seconds": summary["wall_seconds"],
                   "max_parameters": max(card["parameters"] for card in cards.values())}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
