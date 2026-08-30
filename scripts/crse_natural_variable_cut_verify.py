"""Independent replay verifier for per-variable cut learning and source controls."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.decomposition_data import packed_sha256
from cmbench.recognition.models.natural_variable_cut_torch_models import ARCHITECTURES, load_model, parameter_count
from cmbench.recognition.natural_cut_experiment import (
    choose_threshold,
    cost_ratios,
    cut_examples_from_documents,
    pair_ranking,
    paired_examples,
    summarize,
)
from cmbench.recognition.natural_decomposition_matched_data import make_matched_natural_documents
from cmbench.recognition.natural_variable_cut_experiment import (
    NaturalVariableCutConfig,
    enhanced_exact_controls,
    equivariance_audit,
    outputs,
    source_fingerprints,
    summarize_source_controls,
    verify_c4,
)
from cmbench.recognition.source_interaction import (
    source_anf_monomials,
    source_exact_interaction_edges,
    source_exact_partition,
    source_interaction_edges,
    source_partition_proposal,
)
from crse_natural_cut_ranking_verify import independent_canonical_partition, independent_decode
from crse_natural_decomposition_verify import (
    independent_decomposable,
    independent_partition_check,
    read_json,
    read_jsonl,
    scalar_bits,
    sha,
)


def bits_from_monomials(monomials, n_vars: int):
    result = 0
    for assignment in range(1 << n_vars):
        value = 0
        for monomial in monomials:
            present = all(
                (assignment >> (n_vars - 1 - variable)) & 1
                for variable in range(n_vars)
                if monomial & (1 << variable)
            )
            value ^= int(present)
        result |= value << assignment
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run = args.run.resolve()
    manifest = read_json(run / "manifest.json")
    summary = read_json(run / "summary.json")
    spec = read_json(run / "run_spec.json")
    if manifest.get("schema") != "crse-natural-variable-cut-artifacts/v1" or manifest.get("status") != "complete":
        raise SystemExit("natural variable-cut manifest is incomplete")
    actual = {path.name for path in run.iterdir() if path.is_file() and path.name != "manifest.json"}
    if set(manifest["files_sha256"]) != actual:
        raise SystemExit("natural variable-cut artifact inventory mismatch")
    for name, digest in manifest["files_sha256"].items():
        if sha(run / name) != digest:
            raise SystemExit(f"natural variable-cut artifact hash mismatch: {name}")
    if summary.get("schema") != "crse-natural-variable-cut-experiment/v1" or summary.get("status") != "complete":
        raise SystemExit("natural variable-cut summary is incomplete")

    values = spec["config"]
    config = NaturalVariableCutConfig(
        data_seed=values["data_seed"], training_seeds=tuple(values["training_seeds"]),
        epochs=values["epochs"], batch_pairs=values["batch_pairs"], learning_rate=values["learning_rate"],
        cut_weight=values["cut_weight"], ranking_weight=values["ranking_weight"],
        ranking_margin=values["ranking_margin"], threads=values["threads"],
        max_seconds=values["max_seconds"],
        estimated_working_memory_bytes=values["estimated_working_memory_bytes"])
    config.validate(); scout = Path(spec["scout"]); base = Path(spec["retained_c4_run"])
    _base_manifest, c4 = verify_c4(base)
    if (spec.get("status") != "planned" or config.max_seconds != 120 or config.threads != 2
            or sha(base / "manifest.json") != spec["retained_c4_manifest_sha256"]
            or manifest["retained_c4_manifest_sha256"] != spec["retained_c4_manifest_sha256"]
            or manifest["source_sha256"] != source_fingerprints(scout)):
        raise SystemExit("natural variable-cut source/base/pre-run seal changed")

    documents = read_json(run / "dataset.json")
    regenerated, provenance = make_matched_natural_documents(scout, seed=config.data_seed)
    if documents != regenerated or read_json(run / "dataset_provenance.json") != provenance:
        raise SystemExit("natural variable-cut dataset does not regenerate")
    examples = cut_examples_from_documents(documents); by_id = {item.base.case_id: item for item in examples}
    scalar = {}
    for row, example in zip(documents, examples):
        bits = scalar_bits(example.base.expr, example.base.n_vars)
        decomposable, components = independent_decomposable(bits, example.base.n_vars)
        canonical = independent_canonical_partition(components, example.base.n_vars)
        retained = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
        monomials = source_anf_monomials(example.base.document, example.base.n_vars)
        approximate_edges = set(source_interaction_edges(example.base.document, example.base.n_vars))
        exact_edges = set(source_exact_interaction_edges(example.base.document, example.base.n_vars))
        if (bits != example.base.bits or int(decomposable) != example.base.label or canonical != retained
                or bits_from_monomials(monomials, example.base.n_vars) != bits
                or not exact_edges <= approximate_edges
                or source_exact_partition(example.base.document, example.base.n_vars) != canonical):
            raise SystemExit(f"natural variable-cut scalar/source proof mismatch: {example.base.case_id}")
        scalar[example.base.case_id] = bits

    training_pairs = paired_examples(examples, "train")
    validation = [item for item in examples if item.base.split == "validation"]
    evaluation = [item for item in examples if item.base.split in ("test", "confirmatory")]
    expected_models = {(architecture, seed) for architecture in ARCHITECTURES for seed in config.training_seeds}
    cards = {(card["architecture"], card["seed"]): card for card in summary["model_cards"]}
    if set(cards) != expected_models:
        raise SystemExit("natural variable-cut model inventory mismatch")
    reproduced, thresholds, models = {}, {}, {}
    for key, card in cards.items():
        architecture, seed = key
        name, model, training, _metadata, digest = load_model(run / card["file"])
        if (name != architecture or training["seed"] != seed or training["pairs"] != len(training_pairs)
                or digest != card["artifact_sha256"] or parameter_count(model) != card["parameters"]):
            raise SystemExit(f"natural variable-cut model provenance mismatch: {key}")
        threshold, balanced, false_positives = choose_threshold(validation, outputs(model, validation))
        retained = summary["calibration"][f"{architecture}/seed-{seed}"]
        if (threshold != retained["threshold"] or balanced != retained["balanced_accuracy"]
                or false_positives != retained["false_positives"]):
            raise SystemExit(f"natural variable-cut calibration mismatch: {key}")
        thresholds[key] = threshold; models[key] = model
        for example, model_output in zip(evaluation, outputs(model, evaluation)):
            reproduced[(architecture, seed, example.base.case_id)] = model_output

    rows = read_jsonl(run / "classification_raw.jsonl", 600)
    if len(rows) != len(expected_models) * len(evaluation) or len(rows) != summary["row_count"]:
        raise SystemExit("natural variable-cut row count mismatch")
    seen, reasons = set(), Counter()
    for row in rows:
        key = (row["architecture"], row["seed"], row["case_id"])
        if key in seen or key not in reproduced:
            raise SystemExit("duplicate or unknown natural variable-cut row")
        seen.add(key); example = by_id[row["case_id"]]; score, probabilities = reproduced[key]
        partition, nll, margin = independent_decode(probabilities, example.base.n_vars)
        proposed = score >= thresholds[(row["architecture"], row["seed"])]
        accepted = proposed and independent_partition_check(scalar[row["case_id"]], example.base.n_vars, partition)
        canonical = tuple(i for i, value in enumerate(example.row_target[:example.base.n_vars]) if value)
        canonical_match = bool(example.base.label and partition == canonical)
        reason = "exact_variable_cut_witness" if accepted else "exact_variable_cut_rejection" if proposed else "model_abstention"
        if (abs(row["score"] - score) > 5e-6 or row["predicted"] != int(proposed)
                or row["proposed"] != proposed or row["row_variables"] != list(partition)
                or abs(row["cut_nll"] - nll) > 5e-6 or abs(row["cut_margin"] - margin) > 5e-6
                or row["canonical_partition_match"] != canonical_match or row["accepted"] != accepted
                or row["fallback_used"] != (not accepted) or row["check_reason"] != reason
                or row["label"] != example.base.label or row["semantic_mismatch"]
                or row["original_bits_sha256"] != packed_sha256(scalar[row["case_id"]], example.base.n_vars)
                or row["final_bits_sha256"] != row["original_bits_sha256"]):
            raise SystemExit(f"natural variable-cut decision mismatch: {key}")
        reasons[reason] += 1

    retained_equivariance = read_json(run / "equivariance.json")
    replayed_equivariance = {f"{architecture}/seed-{seed}": equivariance_audit(model, evaluation)
        for (architecture, seed), model in models.items()}
    if (retained_equivariance != {"schema": "crse-natural-variable-cut-equivariance/v1", "rows": replayed_equivariance}
            or replayed_equivariance != summary["equivariance"]
            or max(row["maximum_error"] for group in replayed_equivariance.values() for row in group) > 1e-6):
        raise SystemExit("natural variable-cut equivariance replay mismatch")

    source_rows = read_jsonl(run / "source_controls_raw.jsonl", 300)
    if len(source_rows) != 2 * len(evaluation) or len(source_rows) != summary["source_control_row_count"]:
        raise SystemExit("natural source-control row count mismatch")
    for row in source_rows:
        example = by_id[row["case_id"]]
        proposer = source_partition_proposal if row["control"] == "source_overapprox" else source_exact_partition
        partition = proposer(example.base.document, example.base.n_vars)
        accepted = partition is not None and independent_partition_check(
            scalar[row["case_id"]], example.base.n_vars, partition)
        canonical = tuple(i for i, value in enumerate(example.row_target[:example.base.n_vars]) if value)
        if (row["row_variables"] != (list(partition) if partition is not None else None)
                or row["proposed"] != (partition is not None) or row["predicted"] != int(partition is not None)
                or row["accepted"] != accepted or row["canonical_partition_match"] != bool(example.base.label and partition == canonical)
                or row["semantic_mismatch"] or row["signature_ns"] < 0 or row["exact_check_ns"] < 0
                or row["total_ns"] != row["signature_ns"] + row["exact_check_ns"]
                or row["original_bits_sha256"] != packed_sha256(scalar[row["case_id"]], example.base.n_vars)
                or row["final_bits_sha256"] != row["original_bits_sha256"]):
            raise SystemExit(f"natural source-control replay mismatch: {row['control']}/{row['case_id']}")

    ranking = pair_ranking(rows); retained_ranking = read_json(run / "pair_ranking.json")
    source_summary = summarize_source_controls(source_rows); controls = read_json(run / "controls.json")
    if (ranking != retained_ranking or ranking["summary"] != summary["pair_ranking"]
            or summarize(rows) != summary["classification"] or source_summary != summary["source_controls"]
            or read_json(run / "source_controls.json") != source_summary
            or cost_ratios(summary["classification"], controls["summary"]) != summary["cost_ratios"]
            or len(controls["rows"]) != len(evaluation) or any(not row["correct"] for row in controls["rows"])
            or dict(reasons) != summary["proposal_reasons"] or summary["accepted_semantic_mismatches"] != 0
            or not summary["criteria"]["safety"] or not summary["criteria"]["equivariance"]
            or not summary["criteria"]["source_symbolic"] or not summary["source_unchanged"]):
        raise SystemExit("natural variable-cut retained summary/control mismatch")

    result = {"schema": "crse-natural-variable-cut-independent-verification/v1", "status": "pass",
        "run": str(run), "manifest_sha256": sha(run / "manifest.json"),
        "retained_c4_manifest_sha256": sha(base / "manifest.json"), "models_loaded": len(cards),
        "dataset_rows_regenerated": len(documents), "matched_pairs_regenerated": len(paired_examples(examples)),
        "scalar_truth_tables_recomputed": len(examples), "symbolic_anf_truth_tables_reconstructed": len(examples),
        "validation_predictions_replayed": len(validation) * len(cards),
        "evaluation_predictions_replayed": len(rows), "source_control_rows_replayed": len(source_rows),
        "pair_rankings_replayed": len(ranking["rows"]), "equivariance_rows_replayed": sum(map(len, replayed_equivariance.values())),
        "exact_controls_checked": len(controls["rows"]), "semantic_mismatches": 0,
        "limits": {"max_variables": 10, "threads": config.threads,
            "max_parameters": max(card["parameters"] for card in cards.values()),
            "wall_seconds": summary["wall_seconds"]}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
