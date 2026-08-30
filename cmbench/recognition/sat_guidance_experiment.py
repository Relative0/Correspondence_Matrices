"""E2/R10 bounded SAT, assumption-session, and equivalence guidance study."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import platform
from pathlib import Path
import random
import statistics
import sys
import time
from typing import Any, Callable, Sequence

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Not, Or, Var, Xor

from .bdd_ordering import ExactBddArtifact
from .portfolio import prepare, reference_bits
from .sat_guidance import (
    EncodedFormula, ExactSatSession, component_phases,
    encode_equivalence_miter, encode_expression_cnf, occurrence_phases,
    reorder_formula, sat_guidance_features, solver_identity,
)
from .sat_guidance_policy import (
    ACTIONS, SatGuidanceCostTree, fit_sat_guidance_cost_tree,
)
from .features import structural_digest


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "crse-sat-guidance-experiment/v1"
MEASUREMENT_SCHEMA = "crse-sat-guidance-measurement/v1"
FAMILIES = ("mux", "adder_carry", "comparator", "independent_components")
SPLITS = ("train", "validation", "sealed_test")
TASK_KINDS = ("single_sat", "assumption_session", "equivalence_true", "equivalence_false")
EVALUATION_METHODS = (*ACTIONS, "cost_tree", "advice_off")
BASELINE_METHODS = ("direct_truth", "cm_truth", "cse_truth", "bdd", "cadical")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class SatGuidanceConfig:
    seed: int = 20260830
    train_per_family: int = 3
    validation_per_family: int = 1
    test_per_family: int = 1
    repetitions: int = 5
    threads: int = 1
    max_seconds: int = 180

    def validate(self) -> None:
        if (type(self.seed) is not int or not 0 <= self.seed <= 2**32 - 1
                or any(type(value) is not int or not 1 <= value <= 6 for value in (
                    self.train_per_family, self.validation_per_family,
                    self.test_per_family))
                or type(self.repetitions) is not int or not 3 <= self.repetitions <= 9
                or self.threads != 1 or type(self.max_seconds) is not int
                or not 1 <= self.max_seconds <= 300):
            raise ValueError("invalid bounded E2 SAT guidance configuration")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True,
                                ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")


def _write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False) + "\n")


def _ite(selector: Expr, when_true: Expr, when_false: Expr) -> Expr:
    return Or(And(selector, when_true), And(Not(selector), when_false))


def _variant_wrap(expr: Expr, rounds: int) -> Expr:
    for _ in range(rounds):
        expr = Not(Not(expr))
    return expr


def _family_expression(family: str, variant: int,
                       rng: random.Random) -> tuple[Expr, int]:
    if family == "mux":
        n_vars = 6 + variant % 3
        order = list(range(n_vars)); rng.shuffle(order)
        variables = [Var(index) for index in order]
        root = _ite(variables[0], _ite(variables[1], variables[2], variables[3]),
                    _ite(variables[1], variables[4], variables[5]))
        for extra in variables[6:]:
            root = Xor(root, And(extra, variables[variant % 6]))
        return _variant_wrap(root, variant // 4), n_vars
    if family == "adder_carry":
        bits = 3 + variant % 2
        n_vars = 2 * bits + 1
        order = list(range(n_vars)); rng.shuffle(order)
        variables = [Var(index) for index in order]
        carry: Expr = variables[-1]
        for bit in range(bits):
            left, right = variables[2 * bit], variables[2 * bit + 1]
            carry = Or(And(left, right), And(carry, Xor(left, right)))
        return _variant_wrap(carry, variant // 3), n_vars
    if family == "comparator":
        bits = 3 + variant % 2
        n_vars = 2 * bits
        order = list(range(n_vars)); rng.shuffle(order)
        variables = [Var(index) for index in order]
        greater: Expr = And(variables[0], Not(variables[bits]))
        equal: Expr = Eqv(variables[0], variables[bits])
        for bit in range(1, bits):
            greater = Or(greater, And(equal, And(
                variables[bit], Not(variables[bits + bit]))))
            equal = And(equal, Eqv(variables[bit], variables[bits + bit]))
        return _variant_wrap(greater, variant // 3), n_vars
    if family != "independent_components":
        raise ValueError("unknown E2 family")
    n_vars = 6 + variant % 4
    order = list(range(n_vars)); rng.shuffle(order)
    midpoint = n_vars // 2
    left: Expr = Var(order[0])
    for index in order[1:midpoint]:
        left = Xor(left, Var(index)) if variant % 2 else Or(left, Var(index))
    right: Expr = Var(order[midpoint])
    for index in order[midpoint + 1:]:
        right = And(right, Var(index)) if variant % 3 else Xor(right, Var(index))
    return _variant_wrap(And(left, right), variant // 4), n_vars


def _compatible(assignment: int, assumptions: Sequence[int], n_vars: int) -> bool:
    return all(bool(assignment & (1 << (n_vars - abs(literal)))) == (literal > 0)
               for literal in assumptions)


def _statuses(bits: int, n_vars: int,
              queries: Sequence[Sequence[int]]) -> tuple[bool, ...]:
    return tuple(any((bits >> assignment) & 1 and
                     _compatible(assignment, assumptions, n_vars)
                     for assignment in range(1 << n_vars))
                 for assumptions in queries)


def _balanced_assumptions(expr: Expr, n_vars: int,
                          rng: random.Random) -> list[list[int]]:
    bits = reference_bits(expr, n_vars)
    candidates = []
    for width in range(1, min(3, n_vars) + 1):
        # Seeded sampling avoids constructing the full combinatorial set.
        for _ in range(128):
            variables = sorted(rng.sample(range(n_vars), width))
            assumptions = tuple(index + 1 if rng.randrange(2) else -(index + 1)
                                for index in variables)
            if assumptions not in candidates:
                candidates.append(assumptions)
    rng.shuffle(candidates)
    groups = {False: [], True: []}
    for assumptions in candidates:
        status = _statuses(bits, n_vars, [assumptions])[0]
        if len(groups[status]) < 4:
            groups[status].append(list(assumptions))
    if min(map(len, groups.values())) < 4:
        assignments = list(range(1 << n_vars)); rng.shuffle(assignments)
        for assignment in assignments:
            status = bool((bits >> assignment) & 1)
            if len(groups[status]) < 4:
                groups[status].append([
                    index + 1 if assignment & (1 << (n_vars - 1 - index))
                    else -(index + 1) for index in range(n_vars)])
    _require(min(map(len, groups.values())) >= 4,
             "E2 assumption control requires a nonconstant base expression")
    output = []
    for index in range(4):
        output.extend((groups[True][index], groups[False][index]))
    return output


def make_sat_guidance_dataset(config: SatGuidanceConfig) -> list[dict[str, Any]]:
    config.validate()
    rows, seen = [], set()
    split_counts = (("train", config.train_per_family),
                    ("validation", config.validation_per_family),
                    ("sealed_test", config.test_per_family))
    for family_index, family in enumerate(FAMILIES):
        variant = 0
        family_position = 0
        for split, count in split_counts:
            for local_index in range(count):
                salt = hashlib.sha256(
                    f"{config.seed}:{family}:{split}:{local_index}".encode()).digest()
                rng = random.Random(int.from_bytes(salt, "big"))
                while True:
                    base, n_vars = _family_expression(family, variant, rng)
                    variant += 1
                    identity = structural_digest(base, alpha_rename=True)
                    if identity not in seen:
                        seen.add(identity)
                        break
                control = ("raw", "unsat", "sat")[family_position % 3]
                family_position += 1
                sat_expr = (base if control == "raw" else
                            And(base, Not(base)) if control == "unsat" else
                            Or(base, Not(base)))
                assumptions = _balanced_assumptions(
                    base, n_vars,
                    random.Random(int.from_bytes(salt[:8], "big") ^ 0xE210))
                rows.append({
                    "schema": "crse-sat-guidance-case/v1",
                    "case_id": f"{split}-{family}-{local_index:02d}",
                    "family": family, "split": split, "n_vars": n_vars,
                    "base_expression_v2": expr_to_json_dag(base),
                    "sat_expression_v2": expr_to_json_dag(sat_expr),
                    "equivalent_expression_v2": expr_to_json_dag(Not(Not(base))),
                    "nonequivalent_expression_v2": expr_to_json_dag(Not(base)),
                    "base_alpha_structural_sha256": identity,
                    "sat_control": control, "assumptions": assumptions,
                    "case_seed": config.seed + family_index * 10_000 + variant,
                })
    return rows


def _task(case: dict[str, Any], kind: str) -> dict[str, Any]:
    _require(kind in TASK_KINDS, "unknown E2 task")
    n_vars = case["n_vars"]
    base = expr_from_json(case["base_expression_v2"])
    if kind == "single_sat":
        expression = expr_from_json(case["sat_expression_v2"])
        right, queries = None, ((),)
    elif kind == "assumption_session":
        expression, right = base, None
        queries = tuple(tuple(row) for row in case["assumptions"])
    else:
        expression = base
        key = ("equivalent_expression_v2" if kind == "equivalence_true"
               else "nonequivalent_expression_v2")
        right, queries = expr_from_json(case[key]), ((),)
    task_expr = Xor(expression, right) if right is not None else expression
    bits = reference_bits(task_expr, n_vars)
    return {
        "task_id": f"{case['case_id']}:{kind}", "case_id": case["case_id"],
        "split": case["split"], "family": case["family"], "kind": kind,
        "n_vars": n_vars, "expression": expression, "right": right,
        "queries": queries, "expected": _statuses(bits, n_vars, queries),
        "reference_bits": bits,
    }


def _encode_task(task: dict[str, Any]) -> EncodedFormula:
    if task["right"] is None:
        return encode_expression_cnf(task["expression"], task["n_vars"])
    return encode_equivalence_miter(
        task["expression"], task["right"], task["n_vars"])


def _execute_formula(formula: EncodedFormula, queries: Sequence[Sequence[int]],
                     action: str) -> dict[str, Any]:
    _require(action in ACTIONS, "unknown E2 SAT action")
    started = time.perf_counter_ns()
    if action == "reused_occurrence":
        formula = reorder_formula(formula, "short_first")
        phases = occurrence_phases(formula)
    elif action == "reused_component":
        phases = component_phases(formula)
    else:
        phases = ()
    statuses, verification_ns = [], 0
    solver_instances = 0
    if action == "fresh_default":
        for assumptions in queries:
            with ExactSatSession(formula) as session:
                solver_instances += 1
                answer = session.solve(assumptions, phases, verify_core=True)
                statuses.append(answer.satisfiable)
                verification_ns += answer.verification_ns
    else:
        with ExactSatSession(formula) as session:
            solver_instances = 1
            for assumptions in queries:
                answer = session.solve(assumptions, phases, verify_core=True)
                statuses.append(answer.satisfiable)
                verification_ns += answer.verification_ns
    wall_ns = time.perf_counter_ns() - started
    return {
        "statuses": tuple(statuses), "formula_sha256": formula.sha256,
        "cnf_variables": formula.max_var, "clauses": len(formula.clauses),
        "solver_instances": solver_instances, "solve_calls": len(queries),
        "scientific_wall_ns": wall_ns,
        "verification_ns": verification_ns,
        "algorithm_ns": max(1, wall_ns - verification_ns),
        "phase_literals": len(phases), "clause_order": formula.clause_order,
        "solver_authoritative": True, "count_task_measured": False,
        "assumption_semantics": "complete replacement per solve call",
    }


def _fixed_measurement(task: dict[str, Any], action: str, repetition: int,
                       phase: str) -> dict[str, Any]:
    started = time.perf_counter_ns()
    formula = _encode_task(task)
    encode_ns = time.perf_counter_ns() - started
    executed = _execute_formula(formula, task["queries"], action)
    executed["algorithm_ns"] += encode_ns
    executed["scientific_wall_ns"] += encode_ns
    _require(executed["statuses"] == task["expected"],
             "E2 SAT action disagrees with independent truth result")
    return {
        "schema": MEASUREMENT_SCHEMA, "phase": phase,
        "task_id": task["task_id"], "case_id": task["case_id"],
        "split": task["split"], "family": task["family"],
        "task_kind": task["kind"], "method": action,
        "selected_action": action, "decision_reason": "fixed_action",
        "repetition": repetition, "n_vars": task["n_vars"],
        "query_count": len(task["queries"]), "feature_ns": 0,
        "decision_ns": 0, "encode_ns": encode_ns,
        "statuses": list(executed.pop("statuses")), **executed,
    }


def _guided_measurement(task: dict[str, Any], model: SatGuidanceCostTree,
                        repetition: int, phase: str, *, advice: bool) -> dict[str, Any]:
    begun = time.perf_counter_ns()
    formula = _encode_task(task)
    encode_ns = time.perf_counter_ns() - begun
    feature_started = time.perf_counter_ns()
    features = sat_guidance_features(formula, len(task["queries"]))
    feature_ns = time.perf_counter_ns() - feature_started
    decision_started = time.perf_counter_ns()
    decision = model.select(features, advice=advice)
    decision_ns = time.perf_counter_ns() - decision_started
    executed = _execute_formula(formula, task["queries"], decision.action)
    executed["algorithm_ns"] += encode_ns + feature_ns + decision_ns
    executed["scientific_wall_ns"] += encode_ns + feature_ns + decision_ns
    _require(executed["statuses"] == task["expected"],
             "E2 guided action disagrees with independent truth result")
    return {
        "schema": MEASUREMENT_SCHEMA, "phase": phase,
        "task_id": task["task_id"], "case_id": task["case_id"],
        "split": task["split"], "family": task["family"],
        "task_kind": task["kind"],
        "method": "cost_tree" if advice else "advice_off",
        "selected_action": decision.action, "decision_reason": decision.reason,
        "repetition": repetition, "n_vars": task["n_vars"],
        "query_count": len(task["queries"]), "feature_ns": feature_ns,
        "decision_ns": decision_ns, "encode_ns": encode_ns,
        "statuses": list(executed.pop("statuses")), **executed,
    }


def _median_action_costs(rows: Sequence[dict[str, Any]], task_id: str) -> list[float]:
    output = []
    for action in ACTIONS:
        values = [row["algorithm_ns"] for row in rows
                  if row["task_id"] == task_id and row["method"] == action]
        _require(bool(values), "incomplete E2 training action matrix")
        output.append(float(statistics.median(values)))
    return output


def _baseline_comparison(task: dict[str, Any], cadical_action: str) -> list[dict[str, Any]]:
    expected = task["expected"]
    n_vars, queries = task["n_vars"], task["queries"]
    task_expr = (Xor(task["expression"], task["right"])
                 if task["right"] is not None else task["expression"])
    rows = []

    started = time.perf_counter_ns()
    direct_bits = reference_bits(task_expr, n_vars)
    direct = _statuses(direct_bits, n_vars, queries)
    rows.append(("direct_truth", time.perf_counter_ns() - started, direct))

    for backend in ("cm", "cse"):
        started = time.perf_counter_ns()
        bits = prepare(backend, task_expr, n_vars)()
        statuses = _statuses(bits, n_vars, queries)
        rows.append((backend + "_truth", time.perf_counter_ns() - started, statuses))
        _require(bits == direct_bits, "packed baseline disagrees with independent truth")

    started = time.perf_counter_ns()
    artifact = ExactBddArtifact.build(
        task["expression"], n_vars, [f"x{index}" for index in range(n_vars)],
        backend="autoref")
    try:
        if task["right"] is not None:
            bdd_status = (not artifact.equivalent(task["right"]),)
        else:
            bits = sum(value << index for index, value in enumerate(artifact.truth_bits()))
            bdd_status = _statuses(bits, n_vars, queries)
    finally:
        artifact.close()
    rows.append(("bdd", time.perf_counter_ns() - started, bdd_status))

    fixed = _fixed_measurement(task, cadical_action, 0, "task_comparison")
    rows.append(("cadical", fixed["scientific_wall_ns"], tuple(fixed["statuses"])))

    output = []
    for method, elapsed_ns, statuses in rows:
        _require(tuple(statuses) == expected, "task-matched E2 baseline mismatch")
        output.append({
            "schema": "crse-sat-guidance-task-comparison/v1",
            "task_id": task["task_id"], "case_id": task["case_id"],
            "split": task["split"], "family": task["family"],
            "task_kind": task["kind"], "method": method,
            "elapsed_ns": elapsed_ns, "statuses": list(statuses),
            "task_equivalent_output": "satisfiability-status vector",
            "count_task_measured": False,
        })
    return output


def _geomean(values: Sequence[float]) -> float:
    _require(bool(values) and all(value > 0 for value in values), "invalid geometric mean")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(percentile * len(ordered)) - 1))
    return float(ordered[index])


def _evaluation_summary(rows: Sequence[dict[str, Any]], split: str) -> dict[str, Any]:
    selected = [row for row in rows if row["split"] == split]
    by_task: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in selected:
        by_task[(row["task_id"], row["method"])].append(row["algorithm_ns"])
    medians = {key: statistics.median(values) for key, values in by_task.items()}
    task_ids = sorted({key[0] for key in medians})
    oracle = {task_id: min(medians[(task_id, action)] for action in ACTIONS)
              for task_id in task_ids}
    ratios = {method: [medians[(task_id, method)] / oracle[task_id]
                       for task_id in task_ids]
              for method in EVALUATION_METHODS}
    fixed_geo = {action: _geomean([medians[(task_id, action)]
                                   for task_id in task_ids]) for action in ACTIONS}
    best_fixed = min(ACTIONS, key=lambda action: (fixed_geo[action], ACTIONS.index(action)))
    guided_to_fixed = [medians[(task_id, "cost_tree")] /
                       medians[(task_id, best_fixed)] for task_id in task_ids]
    return {
        "split": split, "tasks": len(task_ids),
        "best_fixed_action": best_fixed,
        "method_geomean_regret_to_per_task_oracle": {
            method: _geomean(ratios[method]) for method in EVALUATION_METHODS},
        "cost_tree_geomean_ratio_to_best_fixed": _geomean(guided_to_fixed),
        "cost_tree_p95_ratio_to_best_fixed": _percentile(guided_to_fixed, 0.95),
        "cost_tree_selected_actions": dict(Counter(
            row["selected_action"] for row in selected if row["method"] == "cost_tree")),
        "semantic_rows": len(selected),
    }


def _source_fingerprints() -> dict[str, str]:
    paths = (
        ROOT / "cm_exprlib.py",
        ROOT / "cm_expr_serde.py",
        ROOT / "cmbench/recognition/features.py",
        ROOT / "cmbench/recognition/portfolio.py",
        ROOT / "cmbench/recognition/bdd_ordering.py",
        ROOT / "cmbench/backends/robdd_dd.py",
        ROOT / "cmbench/recognition/sat_guidance.py",
        ROOT / "cmbench/recognition/sat_guidance_policy.py",
        ROOT / "cmbench/recognition/sat_guidance_experiment.py",
        ROOT / "scripts/cm_recognition_sat_guidance.py",
    )
    return {_relative(path): _sha(path) for path in paths}


def run_sat_guidance_experiment(config: SatGuidanceConfig, output: Path,
                                *, progress: Callable[[str], None] = print) -> dict[str, Any]:
    config.validate()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    source_before = _source_fingerprints()
    dataset = make_sat_guidance_dataset(config)
    _write_json(output / "dataset.json", dataset)
    tasks = [_task(case, kind) for case in dataset for kind in TASK_KINDS]
    run_spec = {
        "schema": "crse-sat-guidance-run-spec/v1", "config": asdict(config),
        "families": list(FAMILIES), "splits": list(SPLITS),
        "task_kinds": list(TASK_KINDS), "actions": list(ACTIONS),
        "evaluation_methods": list(EVALUATION_METHODS),
        "baseline_methods": list(BASELINE_METHODS),
        "dataset_sha256": _sha(output / "dataset.json"),
        "solver": solver_identity(), "threads": 1, "network": False,
        "training": True, "production_write": False,
        "exact_counting_in_scope": False,
        "unsat_authority": "pysat.solvers.Cadical195 only; model never proposes status",
        "cost_contract": "CNF encode, feature, decision, phase/order, solver build and solve charged; independent witness/core checks reported separately",
    }
    _write_json(output / "run_spec.json", run_spec)

    training_rows = []
    train_tasks = [task for task in tasks if task["split"] == "train"]
    for index, task in enumerate(train_tasks):
        progress(f"E2 train {index + 1}/{len(train_tasks)} {task['task_id']}")
        for repetition in range(config.repetitions):
            offset = repetition % len(ACTIONS)
            for action in ACTIONS[offset:] + ACTIONS[:offset]:
                if time.perf_counter() - started > config.max_seconds:
                    raise TimeoutError("E2 cooperative wall budget exceeded in training")
                training_rows.append(_fixed_measurement(
                    task, action, repetition, "training"))
    _write_jsonl(output / "training_measurements.jsonl", training_rows)

    features, costs = [], []
    for task in train_tasks:
        formula = _encode_task(task)
        features.append(list(sat_guidance_features(formula, len(task["queries"]))))
        costs.append(_median_action_costs(training_rows, task["task_id"]))
    model = fit_sat_guidance_cost_tree(
        features, costs, max_depth=2, min_leaf=6, min_gain=0.03)
    _write_json(output / "model.json", model.to_dict())

    evaluation_rows = []
    eval_tasks = [task for task in tasks if task["split"] != "train"]
    methods = list(EVALUATION_METHODS)
    for index, task in enumerate(eval_tasks):
        progress(f"E2 eval {index + 1}/{len(eval_tasks)} {task['task_id']}")
        for repetition in range(config.repetitions):
            offset = repetition % len(methods)
            for method in methods[offset:] + methods[:offset]:
                if time.perf_counter() - started > config.max_seconds:
                    raise TimeoutError("E2 cooperative wall budget exceeded in evaluation")
                if method in ACTIONS:
                    row = _fixed_measurement(task, method, repetition, "evaluation")
                else:
                    row = _guided_measurement(
                        task, model, repetition, "evaluation",
                        advice=method == "cost_tree")
                evaluation_rows.append(row)
    _write_jsonl(output / "evaluation_measurements.jsonl", evaluation_rows)

    comparisons = []
    for task in eval_tasks:
        comparisons.extend(_baseline_comparison(task, model.fallback))
    _write_jsonl(output / "task_comparisons.jsonl", comparisons)

    validation = _evaluation_summary(evaluation_rows, "validation")
    sealed = _evaluation_summary(evaluation_rows, "sealed_test")
    exact = all(tuple(row["statuses"]) == next(
        task["expected"] for task in tasks if task["task_id"] == row["task_id"])
        and row["solver_authoritative"] and not row["count_task_measured"]
        for row in (*training_rows, *evaluation_rows))
    exact = exact and all(row["statuses"] == next(
        list(task["expected"]) for task in tasks if task["task_id"] == row["task_id"])
        for row in comparisons)
    local_gate = bool(
        exact
        and sealed["cost_tree_geomean_ratio_to_best_fixed"] <= 0.97
        and sealed["cost_tree_p95_ratio_to_best_fixed"] <= 1.10)
    summary = {
        "schema": SCHEMA, "status": "complete", "exact": exact,
        "dataset_cases": len(dataset), "task_instances": len(tasks),
        "training_measurement_rows": len(training_rows),
        "evaluation_measurement_rows": len(evaluation_rows),
        "task_comparison_rows": len(comparisons),
        "solver": solver_identity(), "model_fallback": model.fallback,
        "validation": validation, "sealed_test": sealed,
        "sat_unsat_controls": dict(Counter(case["sat_control"] for case in dataset)),
        "assumption_expected_statuses": dict(Counter(
            str(status).lower() for task in tasks if task["kind"] == "assumption_session"
            for status in task["expected"])),
        "count_task_measured": False,
        "advice_off_exact": all(row["statuses"] == next(
            list(task["expected"]) for task in tasks if task["task_id"] == row["task_id"])
            for row in evaluation_rows if row["method"] == "advice_off"),
        "local_second_machine_gate": local_gate,
        "production_promotion": False,
        "production_reason": ("local timing gate requires independent confirmation"
                              if local_gate else "learned guidance did not clear the frozen local timing gate"),
        "wall_seconds": time.perf_counter() - started,
        "platform": {"python": sys.version, "platform": platform.platform(),
                     "machine": platform.machine(), "processor": platform.processor()},
    }
    _write_json(output / "summary.json", summary)
    _write_json(output / "source_fingerprints.json", source_before)
    _require(_source_fingerprints() == source_before, "E2 sources changed during run")
    artifacts = {}
    for path in sorted(output.iterdir()):
        if path.name != "manifest.json" and path.is_file():
            artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": _sha(path)}
    _write_json(output / "manifest.json", {
        "schema": "crse-sat-guidance-manifest/v1", "artifacts": artifacts})
    return summary


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line]


def verify_sat_guidance_run(output: Path) -> dict[str, Any]:
    """Independently replay frozen semantics and the trusted solver contract."""
    output = output.resolve()
    manifest = _read_json(output / "manifest.json")
    _require(manifest.get("schema") == "crse-sat-guidance-manifest/v1"
             and isinstance(manifest.get("artifacts"), dict), "invalid E2 manifest")
    for name, identity in manifest["artifacts"].items():
        path = output / name
        _require(path.is_file() and path.stat().st_size == identity["bytes"]
                 and _sha(path) == identity["sha256"], "E2 artifact identity mismatch")
    _require(_read_json(output / "source_fingerprints.json") == _source_fingerprints(),
             "E2 source fingerprint mismatch")
    dataset = _read_json(output / "dataset.json")
    run_spec = _read_json(output / "run_spec.json")
    model = SatGuidanceCostTree.from_dict(_read_json(output / "model.json"))
    summary = _read_json(output / "summary.json")
    _require(_sha(output / "dataset.json") == run_spec["dataset_sha256"],
             "E2 dataset identity mismatch")
    tasks = {_task(case, kind)["task_id"]: _task(case, kind)
             for case in dataset for kind in TASK_KINDS}
    training = _read_jsonl(output / "training_measurements.jsonl")
    evaluation = _read_jsonl(output / "evaluation_measurements.jsonl")
    comparisons = _read_jsonl(output / "task_comparisons.jsonl")
    for row in (*training, *evaluation):
        task = tasks[row["task_id"]]
        _require(row["schema"] == MEASUREMENT_SCHEMA
                 and row["statuses"] == list(task["expected"])
                 and row["solver_authoritative"] is True
                 and row["count_task_measured"] is False,
                 "E2 measurement semantic mismatch")
        _require(row["selected_action"] in ACTIONS, "E2 selected invalid action")
        if row["method"] in {"cost_tree", "advice_off"}:
            features = sat_guidance_features(_encode_task(task), len(task["queries"]))
            expected = model.select(features, advice=row["method"] == "cost_tree")
            _require((row["selected_action"], row["decision_reason"])
                     == (expected.action, expected.reason), "E2 decision replay mismatch")
    for task in tasks.values():
        formula = _encode_task(task)
        phases = component_phases(formula)
        with ExactSatSession(formula) as session:
            replayed = tuple(session.solve(query, phases, verify_core=True).satisfiable
                             for query in task["queries"])
        _require(replayed == task["expected"], "trusted E2 solver replay mismatch")
    for row in comparisons:
        _require(row["method"] in BASELINE_METHODS
                 and row["statuses"] == list(tasks[row["task_id"]]["expected"])
                 and row["count_task_measured"] is False,
                 "E2 task-comparison mismatch")
    _require(summary["exact"] is True and summary["count_task_measured"] is False
             and summary["training_measurement_rows"] == len(training)
             and summary["evaluation_measurement_rows"] == len(evaluation)
             and summary["task_comparison_rows"] == len(comparisons),
             "E2 summary mismatch")
    return {
        "schema": "crse-sat-guidance-verification/v1", "status": "passed",
        "exact": True, "dataset_cases": len(dataset), "task_instances": len(tasks),
        "trusted_solver_replays": sum(len(task["queries"]) for task in tasks.values()),
        "measurement_rows": len(training) + len(evaluation),
        "task_comparison_rows": len(comparisons),
        "model_sha256": _sha(output / "model.json"),
        "manifest_sha256": _sha(output / "manifest.json"),
    }
