"""Independent artifact, aggregation, model, and semantic replay for E1/R07."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cm_exprlib import Not, eval_expr_tt
from cmbench.recognition.bdd_order_experiment import (
    BddOrderConfig, FAMILIES, MEASUREMENT_SCHEMA, METHODS, OBJECTIVES,
    make_bdd_order_dataset,
)
from cmbench.recognition.bdd_order_policy import (
    BddOrderCostTree, ORDER_POLICIES, fit_bdd_order_cost_tree,
)
from cmbench.recognition.bdd_ordering import (
    ExactBddArtifact, independent_bdd_truth_bits, load_bdd_artifact,
)
from cmbench.recognition.features import extract_features


RUN = ROOT / "docs/recognition/runs/bdd-order-e1-20260830-002"
OUTPUT = ROOT / "docs/recognition/verification/bdd-order-e1-20260830-002.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def replay_probe(case: dict, order: list[str]) -> dict:
    expr, n_vars = expr_from_json(case["expression_v2"]), case["n_vars"]
    expected = tuple(int(value) for value in eval_expr_tt(expr, n_vars).tolist())
    artifact = ExactBddArtifact.build(expr, n_vars, order, backend="autoref")
    loaded = None
    try:
        witness = artifact.sat_witness()
        witness_ok = witness is None if not any(expected) else witness is not None
        if witness is not None:
            index = 0
            for variable in range(n_vars):
                index = (index << 1) | witness[f"x{variable}"]
            witness_ok = witness_ok and expected[index] == 1
        fixed = case["query_assignments"][0]
        remaining, restricted = artifact.restrict_truth_bits(fixed)
        expected_restriction = []
        for residual_index in range(1 << len(remaining)):
            assignment = {name: int(value) for name, value in fixed.items()}
            for position, name in enumerate(remaining):
                assignment[name] = (
                    residual_index >> (len(remaining) - 1 - position)) & 1
            full = 0
            for variable in range(n_vars):
                full = (full << 1) | assignment[f"x{variable}"]
            expected_restriction.append(expected[full])
        first, second = artifact.to_bytes(), artifact.to_bytes()
        loaded = load_bdd_artifact(first, backend="autoref")
        return {
            "case_id": case["case_id"], "order": order,
            "truth_exact": artifact.truth_bits() == expected,
            "sat_witness_exact": witness_ok,
            "count_exact": artifact.exact_count() == sum(expected),
            "restriction_exact": restricted == tuple(expected_restriction),
            "equivalence_exact": (artifact.equivalent(Not(Not(expr)))
                                  and not artifact.equivalent(Not(expr))),
            "serialization_deterministic": first == second,
            "independent_replay_exact": independent_bdd_truth_bits(first) == expected,
            "reload_exact": loaded.truth_bits() == expected,
            "reload_order_identity": loaded.variable_order == tuple(order),
            "artifact_bytes": len(first), "artifact_nodes": artifact.node_count,
        }
    finally:
        if loaded is not None:
            loaded.close()
        artifact.close()


def main() -> None:
    spec, summary, manifest = (load(RUN / name) for name in
                               ("run_spec.json", "summary.json", "manifest.json"))
    dataset, model_pack = load(RUN / "dataset.json"), load(RUN / "frozen_models.json")
    training = [json.loads(line) for line in
                (RUN / "training_measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    evaluation = [json.loads(line) for line in
                  (RUN / "evaluation_measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    per_case, probes = load(RUN / "per_case.json"), load(RUN / "task_probes.json")
    artifact_names = (
        "dataset.json", "run_spec.json", "frozen_models.json",
        "training_measurements.jsonl", "evaluation_measurements.jsonl",
        "per_case.json", "task_probes.json", "summary.json",
    )
    artifact_hashes = {name: sha(RUN / name) for name in artifact_names}
    require(manifest.get("status") == "complete"
            and manifest.get("files_sha256") == artifact_hashes,
            "E1 artifact hashes changed")
    source_hashes = manifest.get("source_sha256")
    require(type(source_hashes) is dict and len(source_hashes) == 5
            and all(sha(ROOT / name) == digest for name, digest in source_hashes.items()),
            "E1 measured source changed")
    require(spec.get("network") is False and spec.get("training") is True
            and spec.get("production_write") is False
            and spec.get("backend") == "dd.autoref"
            and spec.get("dynamic_reordering") is False
            and spec.get("methods") == list(METHODS)
            and spec.get("objectives") == list(OBJECTIVES)
            and spec.get("families") == list(FAMILIES),
            "E1 run specification changed")
    config = BddOrderConfig(**spec["config"])
    config.validate()
    require(make_bdd_order_dataset(config) == dataset
            and sha(RUN / "dataset.json") == spec["dataset_sha256"]
            == summary["dataset_sha256"], "E1 dataset does not regenerate")
    require(len(dataset) == 20 and len({row["alpha_structural_sha256"] for row in dataset}) == 20
            and Counter(row["split"] for row in dataset)
            == Counter({"train": 12, "validation": 4, "sealed_test": 4}),
            "E1 dataset scope changed")

    train_cases = [case for case in dataset if case["split"] == "train"]
    eval_cases = [case for case in dataset if case["split"] != "train"]
    expected_train = {(case["case_id"], objective, method, repetition)
                      for case in train_cases for objective in OBJECTIVES
                      for method in ORDER_POLICIES for repetition in range(config.repetitions)}
    expected_eval = {(case["case_id"], objective, method, repetition)
                     for case in eval_cases for objective in OBJECTIVES
                     for method in METHODS for repetition in range(config.repetitions)}
    observed_train = {(row["case_id"], row["objective"], row["method"], row["repetition"])
                      for row in training}
    observed_eval = {(row["case_id"], row["objective"], row["method"], row["repetition"])
                     for row in evaluation}
    require(len(training) == len(observed_train) == len(expected_train) == 720
            and observed_train == expected_train, "E1 training rows incomplete")
    require(len(evaluation) == len(observed_eval) == len(expected_eval) == 600
            and observed_eval == expected_eval, "E1 evaluation rows incomplete")
    for row in training + evaluation:
        require(row.get("schema") == MEASUREMENT_SCHEMA
                and row.get("exact_check") == "separate_selected_order_task_probe"
                and row.get("selected_policy") in ORDER_POLICIES
                and set(row.get("selected_order", "").split(","))
                == {f"x{i}" for i in range(row["n_vars"])}
                and type(row.get("node_count")) is int and row["node_count"] >= 1
                and type(row.get("strategy_runtime_ns")) is int
                and row["strategy_runtime_ns"] >= 1
                and type(row.get("feature_ns")) is int and row["feature_ns"] >= 0
                and type(row.get("decision_ns")) is int and row["decision_ns"] >= 0
                and row.get("charged_runtime_ns") == (
                    row["strategy_runtime_ns"] + row["feature_ns"] + row["decision_ns"])
                and row.get("objective_unit") == (
                    "nodes" if row["objective"] == "min_nodes" else "ns")
                and row.get("objective_cost") == (
                    float(row["node_count"]) if row["objective"] == "min_nodes"
                    else float(row["strategy_runtime_ns"])),
                "E1 raw measurement row invalid")

    def median_cost(case_id: str, objective: str) -> list[float]:
        return [float(statistics.median(
            row["objective_cost"] for row in training
            if row["case_id"] == case_id and row["objective"] == objective
            and row["method"] == policy)) for policy in ORDER_POLICIES]

    require(model_pack.get("schema") == "crse-bdd-order-model-pack/v1"
            and set(model_pack.get("models", {})) == set(OBJECTIVES)
            and summary["frozen_model_sha256"] == sha(RUN / "frozen_models.json"),
            "E1 frozen model pack invalid")
    models = {}
    for objective in OBJECTIVES:
        stored = BddOrderCostTree.from_dict(model_pack["models"][objective])
        features = [list(extract_features(
            expr_from_json(case["expression_v2"]), case["n_vars"],
            len(case["query_assignments"]) if objective == "build_plus_query" else 1).values)
            for case in train_cases]
        refit = fit_bdd_order_cost_tree(
            features, [median_cost(case["case_id"], objective) for case in train_cases],
            max_depth=2, min_leaf=3, min_gain=0.03)
        require(refit.to_dict() == stored.to_dict(), "E1 model does not refit")
        models[objective] = stored
    case_by_id = {case["case_id"]: case for case in dataset}
    for row in evaluation:
        if row["method"] != "cost_tree":
            require(row["selected_policy"] == row["method"]
                    and row["feature_ns"] == row["decision_ns"] == 0,
                    "E1 fixed method routed unexpectedly")
            continue
        case = case_by_id[row["case_id"]]
        features = extract_features(
            expr_from_json(case["expression_v2"]), case["n_vars"],
            len(case["query_assignments"])
            if row["objective"] == "build_plus_query" else 1).values
        decision = models[row["objective"]].select(features)
        require((row["selected_policy"], row["decision_reason"])
                == (decision.policy, decision.reason), "E1 frozen model decision changed")

    grouped = defaultdict(list)
    for row in evaluation:
        grouped[(row["method"], row["objective"], row["split"], row["case_id"])].append(row)
    rebuilt = []
    for (method, objective, split, case_id), values in sorted(grouped.items()):
        require(len(values) == config.repetitions, "E1 per-case repetition count changed")
        rebuilt.append({
            "method": method, "objective": objective, "split": split,
            "case_id": case_id, "family": values[0]["family"],
            "n_vars": values[0]["n_vars"],
            "selected_policy_counts": dict(sorted(Counter(
                row["selected_policy"] for row in values).items())),
            "selected_order_counts": dict(sorted(Counter(
                row["selected_order"] for row in values).items())),
            "median_node_count": statistics.median(row["node_count"] for row in values),
            "objective_unit": values[0]["objective_unit"],
            "median_objective_cost": statistics.median(
                row["objective_cost"] for row in values),
            "median_strategy_runtime_ns": int(statistics.median(
                row["strategy_runtime_ns"] for row in values)),
            "median_charged_runtime_ns": int(statistics.median(
                row["charged_runtime_ns"] for row in values)),
            "median_scientific_wall_ns": int(statistics.median(
                row["scientific_wall_ns"] for row in values)),
            "exact_check": "separate_selected_order_task_probe",
        })
    require(rebuilt == per_case, "E1 per-case aggregation does not reproduce")

    aggregate = {}
    for objective in OBJECTIVES:
        for split in ("validation", "sealed_test"):
            for method in METHODS:
                values = [row for row in rebuilt if row["objective"] == objective
                          and row["split"] == split and row["method"] == method]
                aggregate[f"{objective}/{split}/{method}"] = {
                    "cases": len(values), "objective_unit": values[0]["objective_unit"],
                    "sequence_objective_cost": sum(
                        row["median_objective_cost"] for row in values),
                    "sequence_charged_runtime_ns": sum(
                        row["median_charged_runtime_ns"] for row in values),
                    "sequence_scientific_wall_ns": sum(
                        row["median_scientific_wall_ns"] for row in values),
                    "median_node_count": statistics.median(
                        row["median_node_count"] for row in values),
                    "selected_policy_counts": dict(sorted(sum((Counter(
                        row["selected_policy_counts"]) for row in values), Counter()).items())),
                }
    require(aggregate == summary["aggregate"], "E1 aggregate does not reproduce")
    regrets = {}
    for objective in OBJECTIVES:
        for split in ("validation", "sealed_test"):
            ratios = []
            for case in eval_cases:
                if case["split"] != split:
                    continue
                controls = [next(row for row in rebuilt if row["case_id"] == case["case_id"]
                                 and row["objective"] == objective and row["method"] == method)
                            for method in ORDER_POLICIES]
                learned = next(row for row in rebuilt if row["case_id"] == case["case_id"]
                               and row["objective"] == objective and row["method"] == "cost_tree")
                oracle = min(row["median_objective_cost"] for row in controls)
                learned_cost = (learned["median_objective_cost"]
                                if objective == "min_nodes"
                                else learned["median_charged_runtime_ns"])
                ratios.append(learned_cost / oracle)
            regrets[f"{objective}/{split}"] = {
                "geometric_mean_cost_ratio_to_base_oracle": float(np.exp(
                    np.mean(np.log(np.asarray(ratios, dtype=float))))),
                "maximum_cost_ratio_to_base_oracle": max(ratios),
            }
    require(regrets == summary["cost_tree_regret"], "E1 cost-tree regret changed")

    expected_probe_keys = {(row["phase"], row["case_id"], row["objective"], row["method"],
                            row["selected_order"])
                           for row in training + evaluation}
    observed_probe_keys = {(row["phase"], row["case_id"], row["objective"], row["method"],
                            ",".join(row["order"])) for row in probes}
    require(len(probes) == len(observed_probe_keys) == len(expected_probe_keys)
            and observed_probe_keys == expected_probe_keys,
            "E1 selected-order probes incomplete or duplicated")
    for index, row in enumerate(probes):
        rebuilt_probe = replay_probe(case_by_id[row["case_id"]], row["order"])
        identity = {key: row[key] for key in ("phase", "objective", "method", "selected_policy")}
        require(row == {**identity, **rebuilt_probe}, f"E1 task probe {index} changed")

    alpha_overlap = bool(
        {row["alpha_structural_sha256"] for row in train_cases}
        & {row["alpha_structural_sha256"] for row in eval_cases})
    criteria = {
        "exact_truth_all_selected_orders": True, "task_probes_exact": True,
        "training_evaluation_alpha_disjoint": not alpha_overlap,
        "order_search_cost_included": True, "frozen_models_before_evaluation": True,
        "deterministic_artifact_reload": True, "production_promotion": False,
    }
    require(summary.get("status") == "complete"
            and summary.get("source_unchanged") is True
            and summary.get("training_cases") == 12
            and summary.get("evaluation_cases") == 8
            and summary.get("training_measurement_rows") == 720
            and summary.get("evaluation_measurement_rows") == 600
            and summary.get("per_case_rows") == 120
            and summary.get("task_probe_rows") == len(probes)
            and summary.get("semantic_mismatches") == 0
            and summary.get("criteria") == criteria,
            "E1 summary or criteria changed")
    result = {
        "schema": "crse-bdd-order-independent-verification/v1",
        "status": "pass", "run": relative(RUN),
        "manifest_sha256": sha(RUN / "manifest.json"),
        "files_verified": len(artifact_hashes), "source_files_verified": len(source_hashes),
        "dataset_rows_regenerated": len(dataset), "models_refit": len(models),
        "training_samples_checked": len(training),
        "evaluation_samples_checked": len(evaluation),
        "selected_orders_semantically_replayed": len(probes),
        "semantic_mismatches": 0, "criteria": criteria,
        "cost_tree_regret": regrets, "production_promotion": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(json.dumps(result, indent=2, sort_keys=True,
                                  allow_nan=False).encode("utf-8") + b"\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
