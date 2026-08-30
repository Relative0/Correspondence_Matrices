"""Independent artifact and semantic verifier for natural direct-cut ranking."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.decomposition_data import packed_sha256
from cmbench.recognition.models.natural_cut_torch_models import (
    ARCHITECTURES,
    load_model,
    parameter_count,
)
from cmbench.recognition.natural_cut_experiment import (
    NaturalCutConfig,
    choose_threshold,
    cost_ratios,
    cut_examples_from_documents,
    outputs,
    pair_ranking,
    paired_examples,
    source_fingerprints,
    summarize,
)
from cmbench.recognition.natural_decomposition_matched_data import make_matched_natural_documents
from crse_natural_decomposition_verify import (
    independent_decomposable,
    independent_partition_check,
    read_json,
    read_jsonl,
    scalar_bits,
    sha,
)


def independent_canonical_partition(components, n_vars: int):
    if len(components) < 2:
        return None
    candidates = []
    for count in range(1, len(components)):
        for selected_rest in combinations(range(1, len(components)), count - 1):
            selected = (0,) + selected_rest
            row = tuple(sorted(variable for index in selected for variable in components[index]))
            if len(row) == n_vars:
                continue
            column = tuple(variable for variable in range(n_vars) if variable not in row)
            candidates.append((abs(len(row) - len(column)), max(len(row), len(column)), row))
    return min(candidates)[2] if candidates else None


def independent_decode(probabilities, n_vars: int):
    if len(probabilities) != 10:
        raise ValueError("invalid independent cut probability length")
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
    candidates.sort()
    nll, _imbalance, _largest, row = candidates[0]
    return row, nll, candidates[1][0] - nll


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run = args.run.resolve()
    manifest = read_json(run / "manifest.json")
    summary = read_json(run / "summary.json")
    spec = read_json(run / "run_spec.json")
    if manifest.get("schema") != "crse-natural-cut-ranking-artifacts/v1" or manifest.get("status") != "complete":
        raise SystemExit("natural cut manifest is not complete")
    actual = {path.name for path in run.iterdir() if path.is_file() and path.name != "manifest.json"}
    if set(manifest["files_sha256"]) != actual:
        raise SystemExit("natural cut artifact inventory mismatch")
    for name, digest in manifest["files_sha256"].items():
        if sha(run / name) != digest:
            raise SystemExit(f"natural cut artifact hash mismatch: {name}")
    if summary.get("schema") != "crse-natural-cut-ranking-experiment/v1" or summary.get("status") != "complete":
        raise SystemExit("natural cut summary is not complete")

    values = spec["config"]
    config = NaturalCutConfig(
        data_seed=values["data_seed"],
        training_seeds=tuple(values["training_seeds"]),
        epochs=values["epochs"],
        batch_pairs=values["batch_pairs"],
        learning_rate=values["learning_rate"],
        cut_weight=values["cut_weight"],
        ranking_weight=values["ranking_weight"],
        ranking_margin=values["ranking_margin"],
        threads=values["threads"],
        max_seconds=values["max_seconds"],
        estimated_working_memory_bytes=values["estimated_working_memory_bytes"],
    )
    config.validate()
    scout = Path(spec["scout"])
    if spec.get("status") != "planned" or config.max_seconds != 120 or config.threads != 2:
        raise SystemExit("natural cut finite pre-run specification changed")
    if manifest["source_sha256"] != source_fingerprints(scout):
        raise SystemExit("natural cut implementation/source seal changed")

    documents = read_json(run / "dataset.json")
    regenerated, provenance = make_matched_natural_documents(scout, seed=config.data_seed)
    if documents != regenerated or read_json(run / "dataset_provenance.json") != provenance:
        raise SystemExit("natural cut dataset or provenance does not regenerate")
    examples = cut_examples_from_documents(documents)
    by_id = {example.base.case_id: example for example in examples}
    scalar = {}
    for row, example in zip(documents, examples):
        bits = scalar_bits(example.base.expr, example.base.n_vars)
        decomposable, components = independent_decomposable(bits, example.base.n_vars)
        partition = independent_canonical_partition(components, example.base.n_vars)
        retained = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
        if (
            bits != example.base.bits
            or int(decomposable) != example.base.label
            or packed_sha256(bits, example.base.n_vars) != row["semantic_sha256"]
            or partition != retained
        ):
            raise SystemExit(f"natural cut independent scalar/partition mismatch: {example.base.case_id}")
        scalar[example.base.case_id] = bits

    training_pairs = paired_examples(examples, "train")
    validation = [example for example in examples if example.base.split == "validation"]
    evaluation = [example for example in examples if example.base.split in ("test", "confirmatory")]
    expected_models = {(architecture, seed) for architecture in ARCHITECTURES for seed in config.training_seeds}
    cards = {(card["architecture"], card["seed"]): card for card in summary["model_cards"]}
    if set(cards) != expected_models:
        raise SystemExit("natural cut model inventory mismatch")

    reproduced = {}
    thresholds = {}
    for key, card in cards.items():
        architecture, seed = key
        name, model, training, _metadata, digest = load_model(run / card["file"])
        if (
            name != architecture
            or training["seed"] != seed
            or training["pairs"] != len(training_pairs)
            or digest != card["artifact_sha256"]
            or parameter_count(model) != card["parameters"]
        ):
            raise SystemExit(f"natural cut model provenance mismatch: {key}")
        threshold, balanced, false_positives = choose_threshold(
            validation, outputs(model, architecture, validation)
        )
        retained = summary["calibration"][f"{architecture}/seed-{seed}"]
        if (
            threshold != retained["threshold"]
            or balanced != retained["balanced_accuracy"]
            or false_positives != retained["false_positives"]
        ):
            raise SystemExit(f"natural cut validation calibration mismatch: {key}")
        thresholds[key] = threshold
        for example, model_output in zip(evaluation, outputs(model, architecture, evaluation)):
            reproduced[(architecture, seed, example.base.case_id)] = model_output

    rows = read_jsonl(run / "classification_raw.jsonl", 1_000)
    if len(rows) != len(expected_models) * len(evaluation) or summary["row_count"] != len(rows):
        raise SystemExit("natural cut classification row count mismatch")
    seen, reasons = set(), Counter()
    for row in rows:
        key = (row["architecture"], row["seed"], row["case_id"])
        if key in seen or key not in reproduced:
            raise SystemExit("duplicate or unknown natural cut classification row")
        seen.add(key)
        example = by_id[row["case_id"]]
        score, probabilities = reproduced[key]
        partition = None
        nll = margin = None
        if probabilities is not None:
            partition, nll, margin = independent_decode(probabilities, example.base.n_vars)
        proposed = score >= thresholds[(row["architecture"], row["seed"])]
        accepted = (
            independent_decomposable(scalar[row["case_id"]], example.base.n_vars)[0]
            if proposed and partition is None
            else independent_partition_check(scalar[row["case_id"]], example.base.n_vars, partition)
            if proposed
            else False
        )
        canonical = tuple(index for index, value in enumerate(example.row_target[:example.base.n_vars]) if value)
        canonical_match = bool(example.base.label and partition is not None and partition == canonical)
        reason = (
            "full_exact_anf_witness" if accepted and partition is None
            else "exact_direct_cut_witness" if accepted
            else "exact_direct_cut_rejection" if proposed and partition is not None
            else "exact_anf_rejection" if proposed
            else "model_abstention"
        )
        if (
            abs(row["score"] - score) > 5e-6
            or row["predicted"] != int(proposed)
            or row["proposed"] != proposed
            or row["row_variables"] != (list(partition) if partition is not None else None)
            or (nll is not None and abs(row["cut_nll"] - nll) > 5e-6)
            or (margin is not None and abs(row["cut_margin"] - margin) > 5e-6)
            or row["canonical_partition_match"] != canonical_match
            or row["accepted"] != accepted
            or row["fallback_used"] != (not accepted)
            or row["check_reason"] != reason
            or row["label"] != example.base.label
            or row["semantic_mismatch"]
            or row["original_bits_sha256"] != packed_sha256(scalar[row["case_id"]], example.base.n_vars)
            or row["final_bits_sha256"] != row["original_bits_sha256"]
        ):
            raise SystemExit(f"natural cut independent decision mismatch: {key}")
        reasons[reason] += 1

    retained_ranking = read_json(run / "pair_ranking.json")
    replayed_ranking = pair_ranking(rows)
    controls = read_json(run / "controls.json")
    if retained_ranking != replayed_ranking or replayed_ranking["summary"] != summary["pair_ranking"]:
        raise SystemExit("natural cut pair-ranking summary mismatch")
    if summarize(rows) != summary["classification"]:
        raise SystemExit("natural cut classification summary mismatch")
    if cost_ratios(summary["classification"], controls["summary"]) != summary["cost_ratios"]:
        raise SystemExit("natural cut retained cost ratio mismatch")
    if (
        len(controls["rows"]) != len(evaluation)
        or any(not row["correct"] for row in controls["rows"])
        or any(row["truth_sha256"] != packed_sha256(scalar[row["case_id"]], by_id[row["case_id"]].base.n_vars)
               for row in controls["rows"])
        or dict(reasons) != summary["proposal_reasons"]
        or summary["accepted_semantic_mismatches"] != 0
        or not summary["criteria"]["safety"]
        or not summary["source_unchanged"]
    ):
        raise SystemExit("natural cut exact-control or summary consistency mismatch")

    result = {
        "schema": "crse-natural-cut-ranking-independent-verification/v1",
        "status": "pass",
        "run": str(run),
        "manifest_sha256": sha(run / "manifest.json"),
        "models_loaded": len(cards),
        "dataset_rows_regenerated": len(documents),
        "matched_pairs_regenerated": len(paired_examples(examples)),
        "scalar_truth_tables_recomputed": len(examples),
        "validation_predictions_replayed": len(validation) * len(cards),
        "evaluation_predictions_replayed": len(rows),
        "pair_rankings_replayed": len(replayed_ranking["rows"]),
        "exact_controls_checked": len(controls["rows"]),
        "semantic_mismatches": 0,
        "limits": {
            "max_variables": 10,
            "threads": config.threads,
            "max_parameters": max(card["parameters"] for card in cards.values()),
            "wall_seconds": summary["wall_seconds"],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
