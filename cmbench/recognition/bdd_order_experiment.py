"""E1/R07 bounded exact ROBDD order and compilation study."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import random
import statistics
import sys
import time
from typing import Any

import numpy as np

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Not, Or, Var, Xor, eval_expr_tt
from cmbench.backends.robdd_dd import robdd_variable_order, run_robdd_dd_backend

from .bdd_order_policy import ORDER_POLICIES, BddOrderCostTree, fit_bdd_order_cost_tree
from .bdd_ordering import (
    ExactBddArtifact, independent_bdd_truth_bits, load_bdd_artifact,
)
from .features import FEATURE_NAMES, extract_features, structural_digest


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "crse-bdd-order-experiment/v1"
MEASUREMENT_SCHEMA = "crse-bdd-order-measurement/v1"
OBJECTIVES = ("min_nodes", "min_build_time", "build_plus_query")
METHODS = (*ORDER_POLICIES, "cost_tree")
SPLITS = ("train", "validation", "sealed_test")
FAMILIES = ("mux", "adder_carry", "comparator", "hidden_component")


@dataclass(frozen=True)
class BddOrderConfig:
    seed: int = 20260830
    train_per_family: int = 3
    validation_per_family: int = 1
    test_per_family: int = 1
    repetitions: int = 5
    best_of_k: int = 4
    threads: int = 1
    max_seconds: int = 120

    def validate(self) -> None:
        if (type(self.seed) is not int or not 0 <= self.seed <= 2**32 - 1
                or any(type(value) is not int or not 1 <= value <= 8 for value in (
                    self.train_per_family, self.validation_per_family, self.test_per_family))
                or type(self.repetitions) is not int or not 3 <= self.repetitions <= 9
                or type(self.best_of_k) is not int or not 2 <= self.best_of_k <= 8
                or self.threads != 1 or type(self.max_seconds) is not int
                or not 1 <= self.max_seconds <= 120):
            raise ValueError("invalid bounded E1 BDD order configuration")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def _ite(selector: Expr, when_true: Expr, when_false: Expr) -> Expr:
    return Or(And(selector, when_true), And(Not(selector), when_false))


def _variant_wrap(expr: Expr, rounds: int) -> Expr:
    for _ in range(rounds):
        expr = Not(Not(expr))
    return expr


def _family_expression(family: str, variant: int, rng: random.Random) -> tuple[Expr, int]:
    if family == "mux":
        n_vars = 6 + variant % 3
        order = list(range(n_vars))
        rng.shuffle(order)
        variables = [Var(order[index]) for index in range(n_vars)]
        root = _ite(variables[0], _ite(variables[1], variables[2], variables[3]),
                    _ite(variables[1], variables[4], variables[5]))
        for extra in variables[6:]:
            root = Xor(root, And(extra, _ite(variables[0], variables[2], variables[5])))
        return _variant_wrap(root, variant // 3), n_vars
    if family == "adder_carry":
        bits = 3 + variant % 2
        n_vars = 2 * bits + 1
        order = list(range(n_vars))
        rng.shuffle(order)
        variables = [Var(order[index]) for index in range(n_vars)]
        carry = variables[-1]
        for bit in range(bits):
            a, b = variables[2 * bit], variables[2 * bit + 1]
            carry = Or(And(a, b), And(carry, Xor(a, b)))
        return _variant_wrap(carry, variant // 2), n_vars
    if family == "comparator":
        bits = 3 + variant % 2
        n_vars = 2 * bits
        order = list(range(n_vars))
        rng.shuffle(order)
        variables = [Var(order[index]) for index in range(n_vars)]
        greater: Expr = And(variables[0], Not(variables[bits]))
        equal: Expr = Eqv(variables[0], variables[bits])
        for bit in range(1, bits):
            local_greater = And(variables[bit], Not(variables[bits + bit]))
            greater = Or(greater, And(equal, local_greater))
            equal = And(equal, Eqv(variables[bit], variables[bits + bit]))
        return _variant_wrap(greater, variant // 2), n_vars
    if family != "hidden_component":
        raise ValueError("unknown E1 BDD family")
    n_vars = 6 + variant % 4
    order = list(range(n_vars))
    rng.shuffle(order)
    midpoint = n_vars // 2
    left: Expr = Var(order[0])
    for index in order[1:midpoint]:
        left = Xor(left, Var(index)) if variant % 2 else Or(left, Var(index))
    right: Expr = Var(order[midpoint])
    for index in order[midpoint + 1:]:
        right = And(right, Var(index)) if variant % 3 else Xor(right, Var(index))
    return _variant_wrap(Xor(left, right), variant // 4), n_vars


def make_bdd_order_dataset(config: BddOrderConfig) -> list[dict[str, Any]]:
    config.validate()
    rows = []
    seen = set()
    split_counts = (("train", config.train_per_family),
                    ("validation", config.validation_per_family),
                    ("sealed_test", config.test_per_family))
    for family_index, family in enumerate(FAMILIES):
        variant = 0
        for split, count in split_counts:
            for local_index in range(count):
                salt = hashlib.sha256(
                    f"{config.seed}:{family}:{split}:{local_index}".encode()).digest()
                rng = random.Random(int.from_bytes(salt, "big"))
                while True:
                    expr, n_vars = _family_expression(family, variant, rng)
                    variant += 1
                    digest = structural_digest(expr, alpha_rename=True)
                    if digest not in seen:
                        seen.add(digest)
                        break
                query_rng = random.Random(int.from_bytes(salt[:8], "big") ^ 0xBDD0E1)
                query_assignments = []
                for _ in range(8):
                    selected = sorted(query_rng.sample(range(n_vars), 2))
                    query_assignments.append({f"x{index}": query_rng.randrange(2)
                                              for index in selected})
                features = extract_features(expr, n_vars, len(query_assignments)).values
                rows.append({
                    "schema": "crse-bdd-order-case/v1",
                    "case_id": f"{split}-{family}-{local_index:02d}",
                    "family": family, "split": split, "n_vars": n_vars,
                    "expression_v2": expr_to_json_dag(expr),
                    "alpha_structural_sha256": digest,
                    "query_assignments": query_assignments,
                    "features": list(features),
                    "order_seed": config.seed + family_index * 10_000 + variant,
                })
    return rows


def _source_fingerprints() -> dict[str, str]:
    paths = (
        ROOT / "cmbench/backends/robdd_dd.py",
        ROOT / "cmbench/recognition/bdd_ordering.py",
        ROOT / "cmbench/recognition/bdd_order_policy.py",
        ROOT / "cmbench/recognition/bdd_order_experiment.py",
        ROOT / "scripts/cm_recognition_bdd_order.py",
    )
    return {_relative(path): _sha(path) for path in paths}


def _strategy_runtime_ns(result: dict[str, Any], objective: str) -> int:
    trials = json.loads(result["robdd_order_trials_json"])
    seconds = 0.0
    for trial in trials:
        seconds += float(trial["order_generation_time_s"])
        seconds += float(trial["build_time_s"])
        seconds += float(trial["reorder_time_s"] or 0.0)
        if objective == "build_plus_query":
            seconds += float(trial["query_time_s"])
    return max(1, int(round(seconds * 1_000_000_000)))


def _run_policy(case: dict[str, Any], objective: str, policy: str,
                config: BddOrderConfig) -> tuple[dict[str, Any], float, int]:
    query_assignments = (case["query_assignments"]
                         if objective == "build_plus_query" else ())
    result = run_robdd_dd_backend(
        expr_from_json(case["expression_v2"]), case["n_vars"],
        backend_preference="autoref", order_policy=policy,
        order_sweeps=config.best_of_k if policy == "best-of-k" else 1,
        order_seed=case["order_seed"], selection_objective=objective,
        query_assignments=query_assignments, tt_ref=None,
        correctness_rng=np.random.default_rng(config.seed), correctness_samples=0,
        dynamic_reordering=False, measure_tt_extract=False)
    if result["robdd_status"] != "ok":
        raise ValueError("E1 BDD arm failed to build")
    runtime_ns = _strategy_runtime_ns(result, objective)
    objective_cost = (float(result["robdd_node_count"])
                      if objective == "min_nodes" else float(runtime_ns))
    return result, objective_cost, runtime_ns


def _median_training_costs(measurements: list[dict[str, Any]], case_id: str,
                           objective: str) -> list[float]:
    costs = []
    for policy in ORDER_POLICIES:
        values = [row["objective_cost"] for row in measurements
                  if row["case_id"] == case_id and row["objective"] == objective
                  and row["method"] == policy]
        if not values:
            raise ValueError("incomplete E1 training matrix")
        costs.append(float(statistics.median(values)))
    return costs


def _probe_tasks(case: dict[str, Any], order: list[str]) -> dict[str, Any]:
    expr, n_vars = expr_from_json(case["expression_v2"]), case["n_vars"]
    expected = tuple(int(value) for value in eval_expr_tt(expr, n_vars).tolist())
    artifact = ExactBddArtifact.build(expr, n_vars, order, backend="autoref")
    loaded = None
    try:
        witness = artifact.sat_witness()
        witness_ok = witness is None if not any(expected) else witness is not None
        if witness is not None:
            witness_index = 0
            for variable in range(n_vars):
                witness_index = (witness_index << 1) | witness[f"x{variable}"]
            witness_ok = witness_ok and expected[witness_index] == 1
        fixed = case["query_assignments"][0]
        remaining, restricted = artifact.restrict_truth_bits(fixed)
        restriction_expected = []
        for residual_index in range(1 << len(remaining)):
            assignment = {name: int(value) for name, value in fixed.items()}
            for position, name in enumerate(remaining):
                assignment[name] = (residual_index >> (len(remaining) - 1 - position)) & 1
            full_index = 0
            for variable in range(n_vars):
                full_index = (full_index << 1) | assignment[f"x{variable}"]
            restriction_expected.append(expected[full_index])
        first, second = artifact.to_bytes(), artifact.to_bytes()
        loaded = load_bdd_artifact(first, backend="autoref")
        return {
            "case_id": case["case_id"], "order": order,
            "truth_exact": artifact.truth_bits() == expected,
            "sat_witness_exact": witness_ok,
            "count_exact": artifact.exact_count() == sum(expected),
            "restriction_exact": restricted == tuple(restriction_expected),
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


def run_bdd_order_experiment(
    config: BddOrderConfig, output: Path, *, progress=print,
) -> dict[str, Any]:
    config.validate()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = _source_fingerprints()
    dataset = make_bdd_order_dataset(config)
    _write_json(output / "dataset.json", dataset)
    dataset_sha256 = _sha(output / "dataset.json")
    run_spec = {
        "schema": "crse-bdd-order-run-spec/v1", "config": asdict(config),
        "families": list(FAMILIES), "splits": list(SPLITS),
        "objectives": list(OBJECTIVES), "methods": list(METHODS),
        "feature_names": list(FEATURE_NAMES), "dataset_sha256": dataset_sha256,
        "backend": "dd.autoref", "dynamic_reordering": False,
        "estimated_memory_mib": 512, "network": False, "training": True,
        "production_write": False,
        "cost_contract": "all candidate order generation/build/query costs charged; exact checks separate",
    }
    _write_json(output / "run_spec.json", run_spec)
    started = time.perf_counter()

    training_measurements = []
    training_cases = [case for case in dataset if case["split"] == "train"]
    for case_index, case in enumerate(training_cases):
        progress(f"E1 train {case_index + 1}/{len(training_cases)} {case['case_id']}")
        for repetition in range(config.repetitions):
            order = list(ORDER_POLICIES[repetition % len(ORDER_POLICIES):]
                         + ORDER_POLICIES[:repetition % len(ORDER_POLICIES)])
            for objective in OBJECTIVES:
                for method in order:
                    if time.perf_counter() - started > config.max_seconds:
                        raise TimeoutError("E1 cooperative wall budget exceeded during training")
                    wall_started = time.perf_counter_ns()
                    result, objective_cost, runtime_ns = _run_policy(
                        case, objective, method, config)
                    wall_ns = time.perf_counter_ns() - wall_started
                    training_measurements.append({
                        "schema": MEASUREMENT_SCHEMA, "phase": "training",
                        "case_id": case["case_id"], "split": "train",
                        "family": case["family"], "objective": objective,
                        "method": method, "selected_policy": method,
                        "decision_reason": "fixed_training_arm",
                        "repetition": repetition, "n_vars": case["n_vars"],
                        "node_count": result["robdd_node_count"],
                        "selected_order": result["robdd_order_used"],
                        "objective_cost": objective_cost,
                        "objective_unit": "nodes" if objective == "min_nodes" else "ns",
                        "strategy_runtime_ns": runtime_ns,
                        "feature_ns": 0, "decision_ns": 0,
                        "charged_runtime_ns": runtime_ns,
                        "scientific_wall_ns": wall_ns,
                        "search_time_ns": int(round(
                            result["robdd_order_search_time_s"] * 1_000_000_000)),
                        "exact_check": "separate_selected_order_task_probe",
                    })

    models: dict[str, BddOrderCostTree] = {}
    model_document = {"schema": "crse-bdd-order-model-pack/v1", "models": {}}
    for objective in OBJECTIVES:
        features = [list(extract_features(
            expr_from_json(case["expression_v2"]), case["n_vars"],
            len(case["query_assignments"]) if objective == "build_plus_query" else 1).values)
            for case in training_cases]
        costs = [_median_training_costs(training_measurements, case["case_id"], objective)
                 for case in training_cases]
        model = fit_bdd_order_cost_tree(
            features, costs, max_depth=2, min_leaf=3, min_gain=0.03)
        models[objective] = model
        model_document["models"][objective] = model.to_dict()
    _write_json(output / "frozen_models.json", model_document)
    frozen_model_sha256 = _sha(output / "frozen_models.json")

    evaluation_measurements = []
    evaluation_cases = [case for case in dataset if case["split"] != "train"]
    for case_index, case in enumerate(evaluation_cases):
        progress(f"E1 eval {case_index + 1}/{len(evaluation_cases)} {case['case_id']}")
        expr = expr_from_json(case["expression_v2"])
        for repetition in range(config.repetitions):
            order = list(METHODS[repetition % len(METHODS):]
                         + METHODS[:repetition % len(METHODS)])
            for objective in OBJECTIVES:
                for method in order:
                    if time.perf_counter() - started > config.max_seconds:
                        raise TimeoutError("E1 cooperative wall budget exceeded during evaluation")
                    feature_ns = decision_ns = 0
                    selected_policy, reason = method, "fixed_evaluation_arm"
                    if method == "cost_tree":
                        feature_started = time.perf_counter_ns()
                        features = extract_features(
                            expr, case["n_vars"],
                            len(case["query_assignments"])
                            if objective == "build_plus_query" else 1).values
                        feature_ns = time.perf_counter_ns() - feature_started
                        decision_started = time.perf_counter_ns()
                        decision = models[objective].select(features)
                        decision_ns = time.perf_counter_ns() - decision_started
                        selected_policy, reason = decision.policy, decision.reason
                    wall_started = time.perf_counter_ns()
                    result, objective_cost, runtime_ns = _run_policy(
                        case, objective, selected_policy, config)
                    wall_ns = time.perf_counter_ns() - wall_started
                    evaluation_measurements.append({
                        "schema": MEASUREMENT_SCHEMA, "phase": "evaluation",
                        "case_id": case["case_id"], "split": case["split"],
                        "family": case["family"], "objective": objective,
                        "method": method, "selected_policy": selected_policy,
                        "decision_reason": reason, "repetition": repetition,
                        "n_vars": case["n_vars"], "node_count": result["robdd_node_count"],
                        "selected_order": result["robdd_order_used"],
                        "objective_cost": objective_cost,
                        "objective_unit": "nodes" if objective == "min_nodes" else "ns",
                        "strategy_runtime_ns": runtime_ns, "feature_ns": feature_ns,
                        "decision_ns": decision_ns,
                        "charged_runtime_ns": feature_ns + decision_ns + runtime_ns,
                        "scientific_wall_ns": wall_ns + feature_ns + decision_ns,
                        "search_time_ns": int(round(
                            result["robdd_order_search_time_s"] * 1_000_000_000)),
                        "exact_check": "separate_selected_order_task_probe",
                    })

    grouped = defaultdict(list)
    for row in evaluation_measurements:
        grouped[(row["method"], row["objective"], row["split"], row["case_id"])].append(row)
    per_case = []
    for (method, objective, split, case_id), values in sorted(grouped.items()):
        if len(values) != config.repetitions:
            raise ValueError("incomplete E1 evaluation group")
        per_case.append({
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

    aggregate = {}
    for objective in OBJECTIVES:
        for split in ("validation", "sealed_test"):
            for method in METHODS:
                values = [row for row in per_case if row["objective"] == objective
                          and row["split"] == split and row["method"] == method]
                aggregate[f"{objective}/{split}/{method}"] = {
                    "cases": len(values),
                    "objective_unit": values[0]["objective_unit"],
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

    regrets = {}
    for objective in OBJECTIVES:
        for split in ("validation", "sealed_test"):
            cases = [case for case in evaluation_cases if case["split"] == split]
            ratios = []
            for case in cases:
                controls = [next(row for row in per_case if row["case_id"] == case["case_id"]
                                 and row["objective"] == objective and row["method"] == method)
                            for method in ORDER_POLICIES]
                learned = next(row for row in per_case if row["case_id"] == case["case_id"]
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

    task_probes = []
    case_by_id = {case["case_id"]: case for case in dataset}
    observed_probe_keys = set()
    for row in training_measurements + evaluation_measurements:
        key = (row["phase"], row["case_id"], row["objective"], row["method"],
               row["selected_order"])
        if key in observed_probe_keys:
            continue
        observed_probe_keys.add(key)
        task_probes.append({
            "phase": row["phase"], "objective": row["objective"],
            "method": row["method"], "selected_policy": row["selected_policy"],
            **_probe_tasks(case_by_id[row["case_id"]],
                           row["selected_order"].split(",")),
        })
    probe_fields = ("truth_exact", "sat_witness_exact", "count_exact",
                    "restriction_exact", "equivalence_exact",
                    "serialization_deterministic", "independent_replay_exact",
                    "reload_exact", "reload_order_identity")
    task_exact = all(all(row[field] for field in probe_fields) for row in task_probes)
    alpha_overlap = bool(
        {row["alpha_structural_sha256"] for row in dataset if row["split"] == "train"}
        & {row["alpha_structural_sha256"] for row in dataset if row["split"] != "train"})
    criteria = {
        "exact_truth_all_selected_orders": task_exact,
        "task_probes_exact": task_exact,
        "training_evaluation_alpha_disjoint": not alpha_overlap,
        "order_search_cost_included": True,
        "frozen_models_before_evaluation": True,
        "deterministic_artifact_reload": all(
            row["serialization_deterministic"] and row["reload_order_identity"]
            for row in task_probes),
        "production_promotion": False,
    }
    result = {
        "schema": SCHEMA, "status": "complete",
        "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0],
        "dd_version": importlib.metadata.version("dd"), "config": asdict(config),
        "dataset": _relative(output / "dataset.json"),
        "dataset_sha256": dataset_sha256, "frozen_model_sha256": frozen_model_sha256,
        "training_cases": len(training_cases), "evaluation_cases": len(evaluation_cases),
        "training_measurement_rows": len(training_measurements),
        "evaluation_measurement_rows": len(evaluation_measurements),
        "per_case_rows": len(per_case), "task_probe_rows": len(task_probes),
        "aggregate": aggregate, "cost_tree_regret": regrets, "criteria": criteria,
        "semantic_mismatches": 0 if task_exact else 1,
        "source_unchanged": before == _source_fingerprints(),
    }
    (output / "training_measurements.jsonl").write_text("".join(
        json.dumps(row, sort_keys=True) + "\n" for row in training_measurements),
        encoding="utf-8")
    (output / "evaluation_measurements.jsonl").write_text("".join(
        json.dumps(row, sort_keys=True) + "\n" for row in evaluation_measurements),
        encoding="utf-8")
    _write_json(output / "per_case.json", per_case)
    _write_json(output / "task_probes.json", task_probes)
    _write_json(output / "summary.json", result)
    files = ("dataset.json", "run_spec.json", "frozen_models.json",
             "training_measurements.jsonl", "evaluation_measurements.jsonl",
             "per_case.json", "task_probes.json", "summary.json")
    _write_json(output / "manifest.json", {
        "schema": "crse-bdd-order-artifacts/v1", "status": "complete",
        "files_sha256": {name: _sha(output / name) for name in files},
        "source_sha256": before,
    })
    return result
