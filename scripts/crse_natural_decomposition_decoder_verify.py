"""Independent replay verifier for the retained minimum-cut decoder study."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.decomposition_data import packed_sha256
from cmbench.recognition.models.natural_torch_models import load_model
from cmbench.recognition.natural_decomposition_decoder_experiment import (
    DecoderConfig,
    calibrate,
    minimum_cut_partition,
    summarize,
    verify_base_run,
)
from cmbench.recognition.natural_decomposition_experiment import examples_from_documents, outputs
from crse_natural_decomposition_verify import (
    independent_decomposable,
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
    if manifest.get("schema") != "crse-natural-decomposition-decoder-artifacts/v1" or manifest.get("status") != "complete":
        raise SystemExit("decoder manifest is not complete")
    actual = {path.name for path in run.iterdir() if path.is_file() and path.name != "manifest.json"}
    if set(manifest["files_sha256"]) != actual:
        raise SystemExit("decoder artifact inventory mismatch")
    for name, digest in manifest["files_sha256"].items():
        if sha(run / name) != digest:
            raise SystemExit(f"decoder artifact hash mismatch: {name}")
    if summary.get("schema") != "crse-natural-decomposition-mincut-decoder/v1" or summary.get("status") != "complete":
        raise SystemExit("decoder summary is not complete")

    config_data = spec["config"]
    config = DecoderConfig(
        max_seconds=config_data["max_seconds"],
        max_variables=config_data["max_variables"],
        model_architecture=config_data["model_architecture"],
        training_seeds=tuple(config_data["training_seeds"]),
    )
    config.validate()
    if spec.get("status") != "planned" or spec.get("selection_split") != "validation only":
        raise SystemExit("decoder finite pre-run specification changed")
    base = Path(spec["base_run"])
    base_manifest, base_summary = verify_base_run(base)
    if sha(base / "manifest.json") != spec["base_manifest_sha256"] or manifest["base_manifest_sha256"] != spec["base_manifest_sha256"]:
        raise SystemExit("decoder base-run seal changed")

    documents = read_json(base / "dataset.json")
    examples = examples_from_documents(documents)
    validation = [example for example in examples if example.split == "validation"]
    evaluation = [example for example in examples if example.split in ("test", "confirmatory")]
    by_id = {example.case_id: example for example in evaluation}
    scalar = {}
    for example in evaluation:
        bits = scalar_bits(example.expr, example.n_vars)
        label, _components = independent_decomposable(bits, example.n_vars)
        if bits != example.bits or int(label) != example.label:
            raise SystemExit(f"decoder independent scalar disagreement: {example.case_id}")
        scalar[example.case_id] = bits

    cards = {(card["architecture"], card["seed"]): card for card in base_summary["model_cards"]}
    reproduced = {}
    calibrations = {}
    model_artifacts = {item["seed"]: item for item in summary["model_artifacts"]}
    for seed in config.training_seeds:
        card = cards[(config.model_architecture, seed)]
        name, model, training, _metadata, digest = load_model(base / card["file"])
        retained_artifact = model_artifacts[seed]
        if (
            name != config.model_architecture
            or training["seed"] != seed
            or digest != card["artifact_sha256"]
            or retained_artifact["payload_sha256"] != digest
            or retained_artifact["sha256"] != sha(base / card["file"])
        ):
            raise SystemExit(f"decoder model provenance mismatch: {seed}")
        calibration = calibrate(validation, outputs(model, name, validation))
        if calibration != summary["calibration"][f"seed-{seed}"]:
            raise SystemExit(f"decoder validation calibration mismatch: {seed}")
        calibrations[seed] = calibration
        for example, model_output in zip(evaluation, outputs(model, name, evaluation)):
            reproduced[(seed, example.case_id)] = model_output

    rows = read_jsonl(run / "decoder_raw.jsonl", 500)
    if len(rows) != len(config.training_seeds) * len(evaluation) or len(rows) != summary["row_count"]:
        raise SystemExit("decoder raw row count mismatch")
    seen, reasons = set(), Counter()
    for row in rows:
        key = (row["seed"], row["case_id"])
        if key in seen or key not in reproduced:
            raise SystemExit("duplicate or unknown decoder row")
        seen.add(key)
        example = by_id[row["case_id"]]
        class_score, edge_scores = reproduced[key]
        partition, cut_score = minimum_cut_partition(edge_scores, example.n_vars)
        calibration = calibrations[row["seed"]]
        proposed = class_score >= calibration["class_threshold"] and cut_score <= calibration["cut_threshold"]
        accepted = proposed and independent_partition_check(scalar[example.case_id], example.n_vars, partition)
        reason = (
            "exact_mincut_partition_witness"
            if accepted
            else "exact_mincut_partition_rejection"
            if proposed
            else "decoder_abstention"
        )
        if (
            abs(row["class_score"] - class_score) > 5e-6
            or abs(row["cut_score"] - cut_score) > 5e-6
            or row["row_variables"] != list(partition)
            or row["proposed"] != proposed
            or row["predicted"] != int(proposed)
            or row["accepted"] != accepted
            or row["fallback_used"] != (not accepted)
            or row["check_reason"] != reason
            or row["label"] != example.label
            or row["semantic_mismatch"]
            or row["original_bits_sha256"] != packed_sha256(scalar[example.case_id], example.n_vars)
            or row["final_bits_sha256"] != row["original_bits_sha256"]
        ):
            raise SystemExit(f"decoder independent replay mismatch: {key}")
        reasons[reason] += 1

    if summarize(rows) != summary["summaries"] or dict(reasons) != summary["proposal_reasons"]:
        raise SystemExit("decoder retained summary mismatch")
    if (
        summary["semantic_mismatches"] != 0
        or not summary["criteria"]["safety"]
        or summary["claims"]["model_retrained"]
        or summary["claims"]["test_or_confirmatory_used_for_calibration"]
    ):
        raise SystemExit("decoder safety or claim mismatch")

    result = {
        "schema": "crse-natural-decomposition-mincut-decoder-independent-verification/v1",
        "status": "pass",
        "run": str(run),
        "manifest_sha256": sha(run / "manifest.json"),
        "base_manifest_sha256": sha(base / "manifest.json"),
        "models_loaded": len(config.training_seeds),
        "validation_rows_replayed": len(validation) * len(config.training_seeds),
        "evaluation_rows_replayed": len(rows),
        "scalar_truth_tables_recomputed": len(evaluation),
        "semantic_mismatches": 0,
        "limits": {"max_variables": config.max_variables, "max_seconds": config.max_seconds},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
