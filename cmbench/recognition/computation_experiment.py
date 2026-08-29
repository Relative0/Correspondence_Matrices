"""Milestone D: task-matched exact CM/CSE computation and rewrite benchmark.

The benchmark starts from an expression, charges construction and execution,
and keeps complete-vector, point, restriction, and repeated-vector contracts
separate.  Learned advice selects an exact backend only; a rewrite is accepted
only after an independent complete truth-function check.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import platform
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from bitset_backend import PreparedFlatEvaluation, build_bitset_env, compile_expr_cse, compile_flat
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Expr, Not, Or, Var
from cm_ir import compile_expr_to_cm_ir, expr_structural_hash
from cmbench.expr.eval import eval_expr_assignment

from .contracts import Proposal, RequestBudget, Task, check_proposal
from .experiment import Budget, BudgetExhausted
from .features import IneligibleExpression, structural_digest
from .motif_data import case_from_document, make_motif_documents, validate_documents
from .portfolio import admit, reference_bits
from .teacher import ExactCM, affine_candidate, is_affine, teach

ROOT = Path(__file__).resolve().parents[2]
EPFL_CORPUS = ROOT / "deliverables_n22_24" / "CM_gap_epfl_corpus_2026_08_03.jsonl"
EPFL_PROVENANCE = ROOT / "deliverables_n22_24" / "cm_gap_epfl_provenance_2026_08_03.json"
EPFL_CORPUS_SHA256 = "bb98f14a5525a2d869a7ad80e25e879fd176e78ad6d01c51385edc947f2806ac"
EPFL_COMMIT = "0060e156826e733d69bf5b3322d1bdd0d03a1f9a"

RUN_SCHEMA = "crse-task-computation-experiment/v1"
TASK_KINDS = ("complete_vector", "single_assignment", "partial_restriction", "repeated_vector")
EXACT_BACKENDS = ("direct", "cse", "cm_ir", "explicit_cm")
EVALUATION_ARMS = (*EXACT_BACKENDS, "task_rule", "learned_router", "answer_cache", "rewrite_once")
QUERY_PLANS = {
    "complete_vector": (1,),
    "single_assignment": (1, 8, 32),
    "partial_restriction": (1, 8, 32),
    "repeated_vector": (2, 8, 32),
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


@dataclass(frozen=True)
class ComputationTask:
    kind: str
    queries: int
    fixed_variables: int = 4

    def __post_init__(self) -> None:
        if (self.kind not in TASK_KINDS or type(self.queries) is not int
                or not 1 <= self.queries <= 32 or type(self.fixed_variables) is not int
                or not 1 <= self.fixed_variables <= 7):
            raise ValueError("invalid bounded computation task")
        if self.kind == "complete_vector" and self.queries != 1:
            raise ValueError("complete-vector task has exactly one output")
        if self.kind == "repeated_vector" and self.queries < 2:
            raise ValueError("repeated-vector task requires at least two requests")

    @property
    def task_id(self) -> str:
        suffix = f"/fixed-{self.fixed_variables}" if self.kind == "partial_restriction" else ""
        return f"{self.kind}/q-{self.queries}{suffix}"


def task_specs(fixed_variables: int = 4) -> tuple[ComputationTask, ...]:
    return tuple(ComputationTask(kind, queries, fixed_variables)
                 for kind in TASK_KINDS for queries in QUERY_PLANS[kind])


@dataclass(frozen=True)
class Workload:
    assignments: tuple[tuple[int, ...], ...] = ()
    contexts: tuple[tuple[tuple[int, int], ...], ...] = ()


@dataclass(frozen=True)
class ComputationCase:
    case_id: str
    split: str
    family: str
    source_id: str
    expr: Expr
    document: dict[str, Any]

    @property
    def digest(self) -> str:
        return structural_digest(self.expr)


@dataclass(frozen=True)
class ComputationConfig:
    data_seed: int = 20260829
    parent_counts: tuple[int, ...] = (12, 4, 4, 2)
    rounds: int = 2
    epfl_limit: int = 12
    fixed_variables: int = 4
    max_seconds: float = 120.0
    request_seconds: float = 1.0
    learned_enabled: bool = True

    def validate(self) -> None:
        if type(self.data_seed) is not int or not 0 <= self.data_seed <= 2**32 - 1:
            raise ValueError("invalid data seed")
        if (type(self.parent_counts) is not tuple or len(self.parent_counts) != 4
                or any(type(n) is not int or not 1 <= n <= cap
                       for n, cap in zip(self.parent_counts, (32, 16, 16, 8)))):
            raise ValueError("invalid finite parent counts")
        if type(self.rounds) is not int or not 1 <= self.rounds <= 3:
            raise ValueError("invalid timing rounds")
        if type(self.epfl_limit) is not int or not 1 <= self.epfl_limit <= 16:
            raise ValueError("invalid EPFL evaluation bound")
        if type(self.fixed_variables) is not int or not 1 <= self.fixed_variables <= 7:
            raise ValueError("invalid restriction width")
        if type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 120:
            raise ValueError("wall budget must be in (0,120]")
        Task(8, 32, self.request_seconds, self.learned_enabled)

    def manifest(self, output: Path) -> dict[str, Any]:
        self.validate()
        generated = 2 * sum(self.parent_counts)
        tasks = len(task_specs(self.fixed_variables))
        return {
            "schema": "crse-task-computation-run-spec/v1",
            "status": "planned",
            "config": asdict(self),
            "task_contracts": list(TASK_KINDS),
            "query_plans": {key: list(value) for key, value in QUERY_PLANS.items()},
            "exact_backends": list(EXACT_BACKENDS),
            "evaluation_arms": list(EVALUATION_ARMS),
            "planned_generated_cases": generated,
            "planned_training_rows": self.parent_counts[0] * 2 * tasks * len(EXACT_BACKENDS) * self.rounds,
            "planned_evaluation_row_cap": (generated - self.parent_counts[0] * 2 + self.epfl_limit)
                                              * tasks * len(EVALUATION_ARMS) * self.rounds,
            "resource_limits": {"variables": 8, "cpu_threads": 1,
                "cooperative_wall_seconds": float(self.max_seconds), "memory_estimate_bytes": 256 * 1024 * 1024,
                "memory_limit_is_hard": False, "network": False},
            "timing_contract": "expression-to-task-result/build-plus-query-execution/v1",
            "audit_contract": "independent-scalar-enumeration-outside-every-arm-timer/v1",
            "learned_contract": "task-and-query-cell-cost-policy-selects-exact-backend-only/v1",
            "rewrite_contract": "stop-versus-one-bounded-root-motif-candidate-with-exact-instance-proof/v1",
            "output": str(output.resolve()),
            "source": "generated exact fixtures plus a new nonoverlapping slice of the frozen local EPFL corpus",
        }


def _query_bucket(queries: int) -> str:
    return "1" if queries == 1 else "2-8" if queries <= 8 else "9-32"


def policy_cell(task: ComputationTask) -> str:
    return f"{task.kind}/{_query_bucket(task.queries)}"


def task_rule(task: ComputationTask) -> str:
    if task.kind in ("complete_vector", "single_assignment"):
        return "direct"
    return "cse"


@dataclass(frozen=True)
class TaskCostPolicy:
    cells: dict[str, dict[str, Any]]
    min_gain: float
    training_sha256: str

    def select(self, task: ComputationTask) -> tuple[str, str]:
        cell = self.cells.get(policy_cell(task))
        fallback = task_rule(task)
        if cell is None:
            return fallback, "unseen_task_cell"
        selected = cell["selected"]
        costs = cell["mean_relative_costs"]
        if costs[selected] >= costs[fallback] * (1 - self.min_gain):
            return fallback, "insufficient_predicted_gain"
        return selected, "fitted_task_cost_cell"

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema": "crse-task-cost-policy/v1", "backends": list(EXACT_BACKENDS),
                   "min_gain": self.min_gain, "training_sha256": self.training_sha256,
                   "cells": self.cells}
        return {**payload, "payload_sha256": hashlib.sha256(canonical(payload)).hexdigest()}

    @classmethod
    def from_dict(cls, data: Any) -> "TaskCostPolicy":
        keys = {"schema", "backends", "min_gain", "training_sha256", "cells", "payload_sha256"}
        if type(data) is not dict or set(data) != keys:
            raise ValueError("invalid task policy fields")
        payload = {key: data[key] for key in keys - {"payload_sha256"}}
        if (data["schema"] != "crse-task-cost-policy/v1" or data["backends"] != list(EXACT_BACKENDS)
                or hashlib.sha256(canonical(payload)).hexdigest() != data["payload_sha256"]
                or type(data["training_sha256"]) is not str or len(data["training_sha256"]) != 64
                or type(data["min_gain"]) not in (int, float) or not math.isfinite(data["min_gain"])
                or not 0 <= data["min_gain"] <= 1 or type(data["cells"]) is not dict
                or not 1 <= len(data["cells"]) <= 16):
            raise ValueError("invalid task policy identity")
        cells: dict[str, dict[str, Any]] = {}
        for key, cell in data["cells"].items():
            if (type(key) is not str or type(cell) is not dict
                    or set(cell) != {"samples", "selected", "fallback", "mean_relative_costs"}
                    or type(cell["samples"]) is not int or not 1 <= cell["samples"] <= 512
                    or cell["selected"] not in EXACT_BACKENDS or cell["fallback"] not in EXACT_BACKENDS
                    or type(cell["mean_relative_costs"]) is not dict
                    or set(cell["mean_relative_costs"]) != set(EXACT_BACKENDS)):
                raise ValueError("invalid task policy cell")
            costs = cell["mean_relative_costs"]
            if any(type(v) not in (int, float) or not math.isfinite(v) or not 1 <= v <= 1e9
                   for v in costs.values()):
                raise ValueError("invalid task policy costs")
            cells[key] = json.loads(json.dumps(cell, allow_nan=False))
        return cls(cells, float(data["min_gain"]), data["training_sha256"])

    def save(self, path: Path) -> None:
        _write_json(path, self.to_dict())

    @classmethod
    def load(cls, path: Path) -> "TaskCostPolicy":
        raw = path.read_bytes()
        if len(raw) > 65_536:
            raise ValueError("task policy exceeds 64 KiB")
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate task policy key")
                result[key] = value
            return result
        return cls.from_dict(json.loads(raw, object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite task policy"))))


def fit_task_policy(rows: list[dict[str, Any]], *, min_gain: float = 0.05) -> TaskCostPolicy:
    if not rows or type(min_gain) not in (int, float) or not 0 <= min_gain <= 1:
        raise ValueError("invalid task policy training input")
    grouped: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for row in rows:
        if row.get("status") != "ok" or row.get("arm") not in EXACT_BACKENDS:
            raise ValueError("policy training requires complete exact backend rows")
        grouped[(row["case_id"], row["task_id"], row["arm"])].append(int(row["total_ns"]))
    by_cell: dict[str, list[dict[str, float]]] = defaultdict(list)
    case_tasks = sorted({(case_id, task_id) for case_id, task_id, _ in grouped})
    for case_id, task_id in case_tasks:
        costs = {backend: statistics.median(grouped[(case_id, task_id, backend)])
                 for backend in EXACT_BACKENDS if (case_id, task_id, backend) in grouped}
        if set(costs) != set(EXACT_BACKENDS) or any(cost <= 0 for cost in costs.values()):
            raise ValueError("incomplete policy training cell")
        best = min(costs.values())
        kind = task_id.split("/", 1)[0]
        queries = int(task_id.split("/q-", 1)[1].split("/", 1)[0])
        by_cell[policy_cell(ComputationTask(kind, queries))].append(
            {backend: float(cost / best) for backend, cost in costs.items()})
    cells = {}
    for key, values in sorted(by_cell.items()):
        means = {backend: statistics.fmean(value[backend] for value in values) for backend in EXACT_BACKENDS}
        kind, bucket = key.split("/", 1)
        representative = 1 if bucket == "1" else 8 if bucket == "2-8" else 32
        if kind == "repeated_vector" and representative == 1:
            representative = 2
        fallback = task_rule(ComputationTask(kind, representative))
        selected = min(EXACT_BACKENDS, key=lambda backend: (means[backend], EXACT_BACKENDS.index(backend)))
        cells[key] = {"samples": len(values), "selected": selected, "fallback": fallback,
                      "mean_relative_costs": means}
    policy = TaskCostPolicy(cells, float(min_gain), hashlib.sha256(canonical(rows)).hexdigest())
    return TaskCostPolicy.from_dict(policy.to_dict())


def make_workload(case_id: str, task: ComputationTask, n_vars: int = 8) -> Workload:
    seed = int.from_bytes(hashlib.sha256(f"{case_id}:{task.task_id}:workload/v1".encode()).digest()[:8], "big")
    rng = random.Random(seed)
    if task.kind == "single_assignment":
        indices = rng.sample(range(1 << n_vars), task.queries)
        assignments = tuple(tuple((index >> (n_vars - 1 - i)) & 1 for i in range(n_vars)) for index in indices)
        return Workload(assignments=assignments)
    if task.kind == "partial_restriction":
        choices = []
        for variables in itertools.combinations(range(n_vars), task.fixed_variables):
            for values in range(1 << task.fixed_variables):
                choices.append(tuple((variable, (values >> (task.fixed_variables - 1 - j)) & 1)
                                     for j, variable in enumerate(variables)))
        rng.shuffle(choices)
        return Workload(contexts=tuple(choices[:task.queries]))
    return Workload()


def _assignment_map(values: tuple[int, ...]) -> dict[str, int]:
    return {f"x{i}": int(value) for i, value in enumerate(values)}


def reference_task(expr: Expr, task: ComputationTask, workload: Workload, n_vars: int = 8) -> tuple[int, ...]:
    if task.kind in ("complete_vector", "repeated_vector"):
        bits = 0
        for index in range(1 << n_vars):
            values = tuple((index >> (n_vars - 1 - i)) & 1 for i in range(n_vars))
            bits |= eval_expr_assignment(expr, _assignment_map(values)) << index
        return (bits,) if task.kind == "complete_vector" else (bits,) * task.queries
    if task.kind == "single_assignment":
        return tuple(eval_expr_assignment(expr, _assignment_map(values)) for values in workload.assignments)
    results = []
    for context_tuple in workload.contexts:
        fixed = dict(context_tuple)
        remaining = [i for i in range(n_vars) if i not in fixed]
        bits = 0
        for index in range(1 << len(remaining)):
            assignment = {f"x{i}": fixed.get(i, 0) for i in range(n_vars)}
            for j, variable in enumerate(remaining):
                assignment[f"x{variable}"] = (index >> (len(remaining) - 1 - j)) & 1
            bits |= eval_expr_assignment(expr, assignment) << index
        results.append(bits)
    return tuple(results)


def output_sha256(values: tuple[int, ...]) -> str:
    return hashlib.sha256(canonical(list(values))).hexdigest()


def _direct_packed(expr: Expr, live_variables: tuple[int, ...], fixed: Mapping[int, int]) -> int:
    names = tuple(f"x{i}" for i in live_variables)
    env = build_bitset_env(names)
    full_mask = (1 << (1 << len(live_variables))) - 1
    def rec(node: Expr) -> int:
        if isinstance(node, Var):
            if node.i in fixed:
                return full_mask if fixed[node.i] else 0
            return env[f"x{node.i}"]
        if isinstance(node, Not):
            return (~rec(node.a)) & full_mask
        a = rec(node.a)
        b = rec(node.b)
        name = type(node).__name__
        if name == "And":
            return a & b
        if name == "Or":
            return a | b
        if name == "Xor":
            return a ^ b
        if name == "Imp":
            return ((~a) | b) & full_mask
        if name == "Eqv":
            return (~(a ^ b)) & full_mask
        raise TypeError(node)
    return int(rec(expr))


def _bind(program, live_variables: tuple[int, ...], fixed: Mapping[int, int]) -> PreparedFlatEvaluation:
    names = tuple(f"x{i}" for i in live_variables)
    env = build_bitset_env(names)
    full_mask = (1 << (1 << len(names))) - 1
    template = [0] * program.n_slots
    for slot, kind, payload in program.loads:
        if kind == "const":
            template[slot] = full_mask if payload else 0
        elif payload in env:
            template[slot] = env[payload]
        else:
            variable = int(payload[1:])
            if variable not in fixed:
                raise KeyError(f"missing value for {payload}")
            template[slot] = full_mask if fixed[variable] else 0
    return PreparedFlatEvaluation(program, template, full_mask, False)


def _run_program(program, task: ComputationTask, workload: Workload, n_vars: int) -> tuple[int, ...]:
    all_variables = tuple(range(n_vars))
    if task.kind in ("complete_vector", "repeated_vector"):
        prepared = _bind(program, all_variables, {})
        return tuple(prepared.evaluate() for _ in range(task.queries))
    if task.kind == "single_assignment":
        return tuple(_bind(program, (), dict(enumerate(values))).evaluate() for values in workload.assignments)
    results = []
    for context_tuple in workload.contexts:
        fixed = dict(context_tuple)
        remaining = tuple(i for i in all_variables if i not in fixed)
        results.append(_bind(program, remaining, fixed).evaluate())
    return tuple(results)


def _run_direct(expr: Expr, task: ComputationTask, workload: Workload, n_vars: int) -> tuple[int, ...]:
    all_variables = tuple(range(n_vars))
    if task.kind in ("complete_vector", "repeated_vector"):
        return tuple(_direct_packed(expr, all_variables, {}) for _ in range(task.queries))
    if task.kind == "single_assignment":
        return tuple(_direct_packed(expr, (), dict(enumerate(values))) for values in workload.assignments)
    results = []
    for context_tuple in workload.contexts:
        fixed = dict(context_tuple)
        remaining = tuple(i for i in all_variables if i not in fixed)
        results.append(_direct_packed(expr, remaining, fixed))
    return tuple(results)


def _run_explicit_cm(cm: ExactCM, task: ComputationTask, workload: Workload) -> tuple[int, ...]:
    if task.kind in ("complete_vector", "repeated_vector"):
        return (cm.bits,) * task.queries
    if task.kind == "single_assignment":
        results = []
        for values in workload.assignments:
            index = 0
            for variable in cm.layout.variables:
                index = (index << 1) | values[variable]
            results.append((cm.bits >> index) & 1)
        return tuple(results)
    return tuple(cm.cofactor(dict(context)).bits for context in workload.contexts)


def prepare_task(backend: str, expr: Expr, task: ComputationTask, workload: Workload,
                 n_vars: int = 8) -> tuple[int, Callable[[], tuple[int, ...]]]:
    if backend not in EXACT_BACKENDS:
        raise ValueError("unknown exact computation backend")
    started = time.perf_counter_ns()
    if backend == "direct":
        if task.kind in ("complete_vector", "repeated_vector"):
            build_bitset_env(tuple(f"x{i}" for i in range(n_vars)))
        runner = lambda: _run_direct(expr, task, workload, n_vars)
    elif backend == "cse":
        program = compile_expr_cse(expr, flatten=True)
        runner = lambda: _run_program(program, task, workload, n_vars)
    elif backend == "cm_ir":
        node = compile_expr_to_cm_ir(expr, reuse_cache=False, persistent_cache=False,
                                     share_aware_flatten=True)
        program = compile_flat(node)
        runner = lambda: _run_program(program, task, workload, n_vars)
    else:
        cm = teach(expr, n_vars)
        runner = lambda: _run_explicit_cm(cm, task, workload)
    return max(1, time.perf_counter_ns() - started), runner


def exact_motif_candidate(cm: ExactCM) -> tuple[Expr | None, str]:
    """Return one bounded canonical candidate without treating detection as proof."""
    if is_affine(cm):
        return affine_candidate(cm), "affine"
    n_vars = len(cm.layout.variables)
    full_mask = (1 << (1 << n_vars)) - 1
    columns = [reference_bits(Var(i), n_vars) for i in range(n_vars)]
    for variables in itertools.combinations(range(n_vars), 3):
        a, b, c = variables
        bits = (columns[a] & columns[b]) | (columns[a] & columns[c]) | (columns[b] & columns[c])
        if bits == cm.bits:
            return Or(Or(And(Var(a), Var(b)), And(Var(a), Var(c))), And(Var(b), Var(c))), "majority3"
    for selector in range(n_vars):
        for when_true in range(n_vars):
            if when_true == selector:
                continue
            for when_false in range(n_vars):
                if when_false in (selector, when_true):
                    continue
                bits = ((columns[selector] & columns[when_true])
                        | (((~columns[selector]) & full_mask) & columns[when_false]))
                if bits == cm.bits:
                    return Or(And(Var(selector), Var(when_true)),
                              And(Not(Var(selector)), Var(when_false))), "mux3"
    return None, "none"


def measure_task(case: ComputationCase, task: ComputationTask, workload: Workload,
                 expected: tuple[int, ...], arm: str, config: ComputationConfig,
                 policy: TaskCostPolicy | None, round_index: int) -> dict[str, Any]:
    if arm not in EVALUATION_ARMS and arm not in EXACT_BACKENDS:
        raise ValueError("unknown computation arm")
    admit(case.expr, 8, task.queries)
    row = {"case_id": case.case_id, "split": case.split, "family": case.family,
        "source_id": case.source_id, "task_id": task.task_id, "task_kind": task.kind,
        "queries": task.queries, "fixed_variables": task.fixed_variables,
        "round": round_index, "arm": arm, "selected_backend": arm, "selection_reason": "fixed",
        "status": "ok", "model_calls": 0, "feature_ns": 0, "inference_ns": 0,
        "candidate_ns": 0, "verification_ns": 0, "build_ns": 0, "kernel_ns": 0,
        "total_ns": 0, "audit_ns": 0, "mismatches": 0, "output_sha256": "",
        "expected_sha256": output_sha256(expected), "proposed": False, "accepted": False,
        "proposal_kind": "none", "check_reason": "not_applicable", "cache_hits": 0,
        "error_type": ""}
    started = time.perf_counter_ns()
    expr = case.expr
    backend = arm
    try:
        if arm == "task_rule":
            t = time.perf_counter_ns()
            backend = task_rule(task)
            row["inference_ns"] = time.perf_counter_ns() - t
            row["selection_reason"] = "predeclared_task_rule"
        elif arm == "learned_router":
            if not config.learned_enabled:
                backend, reason = task_rule(task), "learned_disabled"
            elif policy is None:
                backend, reason = task_rule(task), "missing_policy"
            else:
                t = time.perf_counter_ns()
                backend, reason = policy.select(task)
                row["inference_ns"] = time.perf_counter_ns() - t
                row["model_calls"] = 1
            row["selection_reason"] = reason
        elif arm in ("answer_cache", "rewrite_once"):
            backend = task_rule(task)
            row["selection_reason"] = ("exact_per-request-answer-cache"
                                       if arm == "answer_cache" else "one_exact_checked_root_candidate")
        if arm == "rewrite_once":
            request_task = Task(8, task.queries, config.request_seconds, config.learned_enabled)
            budget = RequestBudget(request_task)
            t = time.perf_counter_ns()
            cm = teach(expr, 8)
            row["feature_ns"] = time.perf_counter_ns() - t
            t = time.perf_counter_ns()
            candidate, kind = exact_motif_candidate(cm)
            row["candidate_ns"] = time.perf_counter_ns() - t
            row["proposal_kind"] = kind
            if candidate is not None:
                row["proposed"] = True
                proposal = Proposal(case.digest, candidate, "handwritten", "exact-motif-candidates/v1", 1.0,
                                    schema="crse-region-instance-proposal/v1")
                checked = check_proposal(expr, proposal, request_task, budget)
                row["verification_ns"] = checked.check_ns
                row["accepted"], row["check_reason"] = checked.accepted, checked.reason
                if checked.accepted:
                    expr = candidate
            else:
                row["check_reason"] = "no_bounded_candidate"
        row["selected_backend"] = backend
        if arm == "answer_cache" and task.kind == "repeated_vector":
            one = ComputationTask("complete_vector", 1, task.fixed_variables)
            build_ns, runner = prepare_task(backend, expr, one, Workload(), 8)
            row["build_ns"] = build_ns
            t = time.perf_counter_ns()
            first = runner()[0]
            outputs = (first,) * task.queries
            row["cache_hits"] = task.queries - 1
            row["kernel_ns"] = time.perf_counter_ns() - t
        else:
            build_ns, runner = prepare_task(backend, expr, task, workload, 8)
            row["build_ns"] = build_ns
            t = time.perf_counter_ns()
            outputs = runner()
            row["kernel_ns"] = time.perf_counter_ns() - t
        row["total_ns"] = max(1, time.perf_counter_ns() - started)
        t = time.perf_counter_ns()
        row["output_sha256"] = output_sha256(outputs)
        row["mismatches"] = int(outputs != expected)
        row["audit_ns"] = time.perf_counter_ns() - t
        if row["mismatches"]:
            row["status"] = "mismatch"
    except Exception as exc:
        row["total_ns"] = max(1, time.perf_counter_ns() - started)
        row["status"] = "timeout" if isinstance(exc, TimeoutError) else "error"
        row["error_type"] = type(exc).__name__
    return row


def _to_epfl_axis_order(bits: int, n_vars: int = 8) -> int:
    result = 0
    for epfl_index in range(1 << n_vars):
        crse_index = int(f"{epfl_index:0{n_vars}b}"[::-1], 2)
        result |= ((bits >> crse_index) & 1) << epfl_index
    return result


def _select_per_circuit(items: list[tuple[dict[str, Any], Expr, ExactCM]], limit: int):
    selected, circuits = [], set()
    for item in items:
        circuit = item[0]["circuit"]
        if circuit not in circuits:
            selected.append(item)
            circuits.add(circuit)
        if len(selected) == limit:
            return selected
    selected_ids = {item[0]["id"] for item in selected}
    selected.extend(item for item in items if item[0]["id"] not in selected_ids)
    return selected[:limit]


def load_epfl_d_cases(limit: int) -> tuple[list[ComputationCase], dict[str, Any]]:
    if sha256_file(EPFL_CORPUS) != EPFL_CORPUS_SHA256:
        raise ValueError("frozen EPFL corpus hash mismatch")
    provenance = json.loads(EPFL_PROVENANCE.read_text(encoding="utf-8"))
    if (provenance.get("clone_commit_sha") != EPFL_COMMIT or provenance.get("license_name") != "MIT License"
            or provenance.get("remote_url") != "https://github.com/lsils/benchmarks.git"):
        raise ValueError("EPFL provenance identity mismatch")
    file_hashes = {Path(item["relpath"]).name: item["sha256"] for item in provenance["aig_files"]}
    records = [json.loads(line) for line in EPFL_CORPUS.read_text(encoding="utf-8").splitlines()[1:] if line]
    eligible = []
    rejected = Counter()
    for record in records:
        if record.get("status") != "admitted" or record.get("synt_support_size") != 8:
            continue
        try:
            expr = expr_from_json(record["expression_v2"])
            admit(expr, 8, 32)
            cm = teach(expr, 8)
        except (IneligibleExpression, ValueError, TypeError, RecursionError):
            rejected["current_admission"] += 1
            continue
        truth_sha = hashlib.sha256(_to_epfl_axis_order(cm.bits).to_bytes(32, "little")).hexdigest()
        if (truth_sha != record["truth_sha256"] or expr_structural_hash(expr) != record["structural_hash"]
                or file_hashes.get(record["circuit"]) != record["circuit_sha256"]):
            raise ValueError("EPFL record identity disagreement")
        eligible.append((record, expr, cm))
    prior = _select_per_circuit(eligible, 16)
    prior_ids = {item[0]["id"] for item in prior}
    remaining = [item for item in eligible if item[0]["id"] not in prior_ids]
    selected = _select_per_circuit(remaining, limit)
    if len(selected) != limit:
        raise ValueError("insufficient nonoverlapping EPFL D cases")
    cases = [ComputationCase(record["id"], "epfl_d", f"epfl_{record['category']}",
                             f"epfl:{record['circuit']}", expr, record["expression_v2"])
             for record, expr, _cm in selected]
    motif_counts = Counter(exact_motif_candidate(cm)[1] for _record, _expr, cm in selected)
    manifest = {"schema": "crse-epfl-milestone-d-selection/v1", "training_use": False,
        "corpus_path": str(EPFL_CORPUS.relative_to(ROOT)).replace("\\", "/"),
        "corpus_sha256": EPFL_CORPUS_SHA256, "upstream_commit": EPFL_COMMIT,
        "upstream_url": provenance["remote_url"], "license": provenance["license_name"],
        "eligible_count": len(eligible), "rejected": dict(rejected),
        "prior_milestone_c_ids_excluded": sorted(prior_ids),
        "selected_ids": [case.case_id for case in cases],
        "selected_circuits": [case.source_id.removeprefix("epfl:") for case in cases],
        "selection": "exclude the frozen Milestone-C selection, then first remaining record per corpus-ordered circuit, then corpus-order fill",
        "motif_labels": dict(motif_counts)}
    return cases, manifest


def source_fingerprints() -> dict[str, str]:
    paths = [Path(__file__), ROOT / "cmbench" / "recognition" / "contracts.py",
             ROOT / "cmbench" / "recognition" / "teacher.py", ROOT / "bitset_backend.py",
             ROOT / "cm_ir.py", EPFL_CORPUS, EPFL_PROVENANCE]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path) for path in paths}


def summarize(rows: list[dict[str, Any]], rounds: int) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["case_id"], row["task_id"], row["arm"])].append(row)
    medians = {key: statistics.median(value["total_ns"] for value in values)
               for key, values in grouped.items()
               if len(values) == rounds and all(value["status"] == "ok" for value in values)}
    summaries = {}
    splits = sorted({row["split"] for row in rows})
    for split in splits:
        for kind in TASK_KINDS:
            case_tasks = sorted({(row["case_id"], row["task_id"]) for row in rows
                                 if row["split"] == split and row["task_kind"] == kind})
            for arm in EVALUATION_ARMS:
                selected = [(case_id, task_id) for case_id, task_id in case_tasks
                            if all((case_id, task_id, comparator) in medians
                                   for comparator in (arm, "cse", "task_rule", *EXACT_BACKENDS))]
                if not selected:
                    continue
                arm_costs = [medians[(case_id, task_id, arm)] for case_id, task_id in selected]
                ratios_cse = [cost / medians[(case_id, task_id, "cse")]
                               for cost, (case_id, task_id) in zip(arm_costs, selected)]
                ratios_rule = [cost / medians[(case_id, task_id, "task_rule")]
                               for cost, (case_id, task_id) in zip(arm_costs, selected)]
                ratios_best = [cost / min(medians[(case_id, task_id, backend)] for backend in EXACT_BACKENDS)
                               for cost, (case_id, task_id) in zip(arm_costs, selected)]
                summaries[f"{split}/{kind}/{arm}"] = {"workloads": len(selected),
                    "geomean_speedup_over_cse": math.exp(-statistics.fmean(math.log(r) for r in ratios_cse)),
                    "geomean_speedup_over_task_rule": math.exp(-statistics.fmean(math.log(r) for r in ratios_rule)),
                    "geomean_speedup_over_virtual_best_fixed": math.exp(-statistics.fmean(math.log(r) for r in ratios_best)),
                    "virtual_best_is_unavailable_oracle": True,
                    "median_total_ns": statistics.median(arm_costs),
                    "max_slowdown_over_task_rule": max(ratios_rule)}
    return summaries


def render_report(result: dict[str, Any]) -> str:
    lines = ["# CRSE Milestone D: task-matched exact computation", "",
        f"Status: **{result['status']}**", f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Exact output mismatches: {result['semantic_mismatches']}", "",
        "## End-to-end task results", "",
        "| Split / task / arm | Workloads | Speedup vs CSE | Speedup vs task rule | Speedup vs virtual best fixed | Median ns |",
        "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for key, value in result["summaries"].items():
        lines.append(f"| {key} | {value['workloads']} | {value['geomean_speedup_over_cse']:.3f} | "
                     f"{value['geomean_speedup_over_task_rule']:.3f} | "
                     f"{value['geomean_speedup_over_virtual_best_fixed']:.3f} | {value['median_total_ns']:.0f} |")
    lines += ["", "The virtual-best column is an unavailable per-workload oracle. Explicit CM means the bounded dense exact truth function, while `cm_ir` means CM-IR simplification followed by the common flat executor.",
        "Construction, task/query execution, routing, candidate generation, and rewrite verification are charged inside each arm. The independent scalar audit is outside every arm timer.", "",
        "## Routing and rewrite", "",
        f"Fitted task-router selections: `{json.dumps(result['router_selections'], sort_keys=True)}`.",
        f"Rewrite proposals: {result['rewrite']['proposed']}; accepted: {result['rewrite']['accepted']}; reasons: `{json.dumps(result['rewrite']['reasons'], sort_keys=True)}`.",
        f"Learned bypass model calls: {result['learned_bypass']['model_calls']}; bypass mismatches: {result['learned_bypass']['output_mismatches']}.", "",
        "This is one bounded local smoke on generated functions and a new nonoverlapping EPFL slice. It does not promote a router, prove cross-machine timing, or complete the broader transformation/reuse agenda.", ""]
    return "\n".join(lines)


def run_computation_experiment(config: ComputationConfig, output: Path, progress=print) -> dict[str, Any]:
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    before = source_fingerprints()
    spec = config.manifest(output)
    _write_json(output / "run_spec.json", {**spec, "source_sha256": before})
    budget = Budget(config.max_seconds)
    training_rows: list[dict[str, Any]] = []
    evaluation_rows: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    epfl_manifest: dict[str, Any] = {}
    policy: TaskCostPolicy | None = None
    status, error_type = "incomplete", ""
    leakage: dict[str, Any] = {}
    try:
        progress("Dataset: exact generated groups and nonoverlapping frozen EPFL D slice")
        documents = make_motif_documents(config.data_seed, config.parent_counts, budget.check)
        leakage = validate_documents(documents, budget.check)
        _write_json(output / "generated_corpus.json", documents)
        generated = []
        for document in documents:
            case = case_from_document(document)
            generated.append(ComputationCase(case.case_id, case.split, case.family,
                                              document["source_id"], case.expr, document["expression"]))
        epfl, epfl_manifest = load_epfl_d_cases(config.epfl_limit)
        _write_json(output / "epfl_evaluation_manifest.json", epfl_manifest)
        build_bitset_env(tuple(f"x{i}" for i in range(8)))
        tasks = task_specs(config.fixed_variables)
        progress("Training: measure fixed exact paths and freeze the task/query cost policy")
        rng = random.Random(f"{config.data_seed}:milestone-d-training-order/v1")
        for case in [case for case in generated if case.split == "train"]:
            for task in tasks:
                budget.check()
                workload = make_workload(case.case_id, task)
                expected = reference_task(case.expr, task, workload)
                for round_index in range(config.rounds):
                    arms = list(EXACT_BACKENDS)
                    rng.shuffle(arms)
                    for arm in arms:
                        budget.check()
                        training_rows.append(measure_task(case, task, workload, expected, arm,
                                                          config, None, round_index))
        policy = fit_task_policy(training_rows)
        policy_path = output / "task_router.json"
        policy.save(policy_path)
        loaded = TaskCostPolicy.load(policy_path)
        if loaded.to_dict() != policy.to_dict() or any(loaded.select(task) != policy.select(task) for task in tasks):
            raise RuntimeError("task policy save/reload disagreement")
        policy = loaded
        progress("Evaluation: direct, CSE, CM-IR, explicit CM, routing, cache, and one rewrite")
        evaluation = [case for case in generated if case.split != "train"] + epfl
        rng = random.Random(f"{config.data_seed}:milestone-d-evaluation-order/v1")
        for case in evaluation:
            for task in tasks:
                budget.check()
                workload = make_workload(case.case_id, task)
                expected = reference_task(case.expr, task, workload)
                for round_index in range(config.rounds):
                    arms = list(EVALUATION_ARMS)
                    rng.shuffle(arms)
                    for arm in arms:
                        budget.check()
                        evaluation_rows.append(measure_task(case, task, workload, expected, arm,
                                                            config, policy, round_index))
        if any(row["status"] != "ok" for row in training_rows + evaluation_rows):
            raise RuntimeError("an exact computation cell failed or mismatched")
        status = "complete"
    except (KeyboardInterrupt, Exception) as exc:
        status = ("interrupted" if isinstance(exc, KeyboardInterrupt) else
                  "budget_exhausted" if isinstance(exc, BudgetExhausted) else "failed")
        error_type = type(exc).__name__
        progress(f"Incomplete Milestone D run retained: {error_type}: {exc}")
    _write_jsonl(output / "training_raw.jsonl", training_rows)
    _write_jsonl(output / "evaluation_raw.jsonl", evaluation_rows)
    after = source_fingerprints()
    summaries = summarize(evaluation_rows, config.rounds)
    rewrite_rows = [row for row in evaluation_rows if row["arm"] == "rewrite_once" and row["round"] == 0]
    router_rows = [row for row in evaluation_rows if row["arm"] == "learned_router" and row["round"] == 0]
    bypass_rows = [row for row in evaluation_rows if row["arm"] == "task_rule" and row["round"] == 0]
    bypass_mismatches = sum(row["mismatches"] for row in bypass_rows)
    bypass_cases = len(bypass_rows)
    bypass = {"switch": "learned_enabled=false", "workloads": bypass_cases, "model_calls": 0,
              "output_mismatches": bypass_mismatches, "fallback": "predeclared task rule"}
    _write_json(output / "learned_bypass_audit.json", bypass)
    result = {"schema": RUN_SCHEMA, "status": status, "error_type": error_type,
        "config": asdict(config), "source_sha256": before, "source_unchanged": before == after,
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "cpu_threads_requested": 1, "thread_environment": {name: os.environ.get(name)
                        for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
        "dataset": {"generated_cases": len(documents), "leakage_checks": leakage,
                    "epfl": epfl_manifest},
        "row_counts": {"training": len(training_rows), "evaluation": len(evaluation_rows)},
        "task_router": policy.to_dict() if policy else None,
        "router_selections": dict(Counter(row["selected_backend"] for row in router_rows)),
        "rewrite": {"proposed": sum(row["proposed"] for row in rewrite_rows),
                    "accepted": sum(row["accepted"] for row in rewrite_rows),
                    "kinds": dict(Counter(row["proposal_kind"] for row in rewrite_rows)),
                    "reasons": dict(Counter(row["check_reason"] for row in rewrite_rows))},
        "summaries": summaries, "learned_bypass": bypass,
        "semantic_mismatches": sum(row["mismatches"] for row in training_rows + evaluation_rows),
        "failed_rows": sum(row["status"] != "ok" for row in training_rows + evaluation_rows),
        "criteria": {"safety_met": not any(row["mismatches"] for row in training_rows + evaluation_rows)
                                    and bypass_mismatches == 0,
                     "router_promotion": False, "rewrite_promotion": False,
                     "interpretation": "bounded smoke thresholds require later independent replication"},
        "wall_seconds": time.perf_counter() - budget.started,
        "scientific_claim": "bounded end-to-end task computation smoke; no backend or rewrite promotion"}
    _write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-task-computation-artifacts/v1",
        "status": status, "files_sha256": {path.name: sha256_file(path) for path in files},
        "source_sha256": before})
    return result
