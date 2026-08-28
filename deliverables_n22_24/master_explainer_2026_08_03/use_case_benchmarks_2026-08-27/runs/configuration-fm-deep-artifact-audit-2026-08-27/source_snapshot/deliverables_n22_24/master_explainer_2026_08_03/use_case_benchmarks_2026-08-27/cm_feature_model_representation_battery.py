"""Correctness-gated feature-model representation and task crossover battery."""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.util
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, Mapping

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
from bitset_backend import _eval_words, compile_expr_cse, get_flat_program, program_metrics  # noqa: E402
from cm_exprlib import And, Expr, Not, Or, Var  # noqa: E402
from cm_ir import clear_cm_ir_persistent_cache, compile_expr_to_cm_ir  # noqa: E402
from cmbench.backends.robdd_dd import (  # noqa: E402
    _declare_dd_vars,
    bdd_backend_identity,
    bdd_function_value,
    expr_to_dd_bdd,
    robdd_variable_order,
    safe_bdd_node_count,
    select_dd_module,
)

import cm_feature_model_history_pilot as pilot  # noqa: E402


PROTOCOL = "CONFIGURATION-REPRESENTATION-BATTERY-PROTOCOL.md"
PILOT_RUN = HERE / "runs" / "configuration-fm-history-pilot-real3-2026-08-27"
DEFAULT_OUTPUT = HERE / "runs" / "configuration-representation-battery-2026-08-27"
WIDTHS = (8, 12, 16)
CLAUSE_MULTIPLIERS = (1, 8, 64)
DUPLICATE_FRACTIONS = (0.0, 0.5, 0.9)
SYNTHETIC_SEEDS = (2026082711, 2026082712)
PARTIAL_FRACTIONS = (0.25, 0.5, 0.75)
ROUNDS = 7
POINT_QUERIES = 256
PARTIAL_CONTEXTS = 64
BEST_OF_K = 5


@dataclass(frozen=True)
class Case:
    case_id: str
    corpus: str
    model_id: str
    history: str
    slice_kind: str
    k: int
    residual: tuple[tuple[int, ...], ...]
    planted_bits: int
    metadata: dict
    edited_residual: tuple[tuple[int, ...], ...] | None = None


@dataclass
class BDDArtifact:
    manager: object
    root: object
    setup_ns: int
    build_ns: int
    nodes: int
    order: tuple[str, ...]
    backend: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def jsonl_dump(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def median_ns(function: Callable[[], object], rounds: int, batch: int) -> tuple[float, list[float]]:
    function()
    samples = []
    for _ in range(rounds):
        start = time.perf_counter_ns()
        for _item in range(batch):
            function()
        samples.append((time.perf_counter_ns() - start) / batch)
    return statistics.median(samples), samples


def counterbalanced_medians(
    arms: Mapping[str, tuple[Callable[[], object], int]], rounds: int, offset: int
) -> tuple[dict[str, float], dict[str, list[float]]]:
    for function, _batch in arms.values():
        function()
    samples: dict[str, list[float]] = {name: [] for name in arms}
    names = list(arms)
    for round_index in range(rounds):
        shift = (offset + round_index) % len(names)
        for name in names[shift:] + names[:shift]:
            function, batch = arms[name]
            start = time.perf_counter_ns()
            for _ in range(batch):
                function()
            samples[name].append((time.perf_counter_ns() - start) / batch)
    return {name: statistics.median(values) for name, values in samples.items()}, samples


def traced_peak(function: Callable[[], object]) -> tuple[int, int]:
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter_ns()
    value = function()
    elapsed = time.perf_counter_ns() - start
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del value
    return elapsed, peak


def geomean(values: Iterable[float]) -> float:
    vals = [float(value) for value in values]
    if not vals or any(value <= 0 or not math.isfinite(value) for value in vals):
        raise ValueError("geomean requires positive finite values")
    return math.exp(statistics.fmean(math.log(value) for value in vals))


def balanced(nodes: list[Expr], constructor: Callable[[Expr, Expr], Expr]) -> Expr:
    if not nodes:
        raise ValueError("balanced requires a nonempty list")
    level = list(nodes)
    while len(level) > 1:
        next_level = []
        for index in range(0, len(level), 2):
            next_level.append(level[index] if index + 1 == len(level) else constructor(level[index], level[index + 1]))
        level = next_level
    return level[0]


def expression_from_residual(residual: tuple[tuple[int, ...], ...], k: int) -> Expr:
    variables = tuple(Var(index) for index in range(k))
    negatives = tuple(Not(variable) for variable in variables)
    if not residual:
        return Or(variables[0], negatives[0])
    clauses = []
    for clause in residual:
        nodes = [variables[abs(literal) - 1] if literal > 0 else negatives[abs(literal) - 1] for literal in clause]
        clauses.append(balanced(nodes, Or))
    return balanced(clauses, And)


@lru_cache(maxsize=None)
def patterns(k: int) -> tuple[int, ...]:
    width = 1 << k
    return tuple(sum(1 << assignment for assignment in range(width) if (assignment >> index) & 1) for index in range(k))


def cnf_bitset(residual: tuple[tuple[int, ...], ...], k: int) -> int:
    width = 1 << k
    mask = (1 << width) - 1
    pats = patterns(k)
    value = mask
    for clause in residual:
        clause_value = 0
        for literal in clause:
            pat = pats[abs(literal) - 1]
            clause_value |= pat if literal > 0 else (~pat) & mask
        value &= clause_value
    return value


def scalar_residual(residual: tuple[tuple[int, ...], ...], assignment: int) -> bool:
    return all(any(bool((assignment >> (abs(literal) - 1)) & 1) == (literal > 0) for literal in clause) for clause in residual)


def choose_slice(model_id: str, parsed: pilot.ParsedCNF, k: int, kind: str) -> tuple[int, ...]:
    mapped = sorted(parsed.feature_names)
    if len(mapped) < k:
        raise ValueError(f"only {len(mapped)} mapped variables for k={k}")
    if kind == "incidence":
        incidence = Counter(abs(literal) for clause in parsed.clauses for literal in clause)
        return tuple(sorted(mapped, key=lambda variable: (-incidence[variable], variable))[:k])
    if kind == "hash":
        return tuple(sorted(mapped, key=lambda variable: hashlib.sha256(f"{model_id}|{variable}".encode()).digest())[:k])
    raise ValueError(kind)


def decode_witness(row: dict) -> dict[int, bool]:
    raw = bytes.fromhex(row["product_little_endian_hex"])
    value = int.from_bytes(raw, "little")
    return {variable: bool((value >> (variable - 1)) & 1) for variable in range(1, int(row["n_vars"]) + 1)}


def load_real_cases(
    pilot_run: Path = PILOT_RUN,
    source: Path | None = None,
) -> tuple[list[Case], list[dict]]:
    provenance = json.loads((pilot_run / "SOURCE-PROVENANCE.json").read_text(encoding="utf-8"))
    witnesses = {
        row["model_id"]: row
        for row in (json.loads(line) for line in (pilot_run / "witnesses.jsonl").read_text(encoding="utf-8").splitlines())
    }
    by_name = {item["cache_filename"]: item for item in provenance["selected_payloads"]}
    source = (source or pilot.DEFAULT_SOURCE).resolve()
    cases = []
    inputs = []
    for cache_name, item in by_name.items():
        path = source / "selected_payloads" / cache_name
        if not path.is_file() or sha256_file(path) != item["dimacs_sha256"]:
            raise RuntimeError(f"missing or changed official payload: {path}")
        parsed = pilot.parse_dimacs(path)
        product = decode_witness(witnesses[item["model_id"]])
        if not pilot.scalar_cnf(parsed.clauses, product):
            raise AssertionError(f"stored witness no longer satisfies {item['model_id']}")
        inputs.append({"model_id": item["model_id"], "path": str(path), "sha256": item["dimacs_sha256"], "bytes": path.stat().st_size})
        for k in WIDTHS:
            for kind in ("incidence", "hash"):
                slice_variables = choose_slice(item["model_id"], parsed, k, kind)
                residual, stats = pilot.condition_cnf(parsed.clauses, product, slice_variables)
                planted = sum(1 << index for index, variable in enumerate(slice_variables) if product[variable])
                cases.append(Case(
                    case_id=f"real|{item['model_id']}|{kind}|k{k}",
                    corpus="real",
                    model_id=item["model_id"],
                    history=item["history"],
                    slice_kind=kind,
                    k=k,
                    residual=residual,
                    planted_bits=planted,
                    metadata={**stats, "payload_sha256": item["dimacs_sha256"], "slice_variables": slice_variables,
                              "slice_feature_names": [parsed.feature_names[variable] for variable in slice_variables]},
                ))
    return cases, inputs


def planted_clause(rng: random.Random, k: int, planted: int, excluded: set[tuple[int, ...]]) -> tuple[int, ...]:
    for _ in range(10000):
        width = rng.choice((1, 2, 3, 4))
        variables = sorted(rng.sample(range(1, k + 1), width))
        clause = tuple(variable if rng.getrandbits(1) else -variable for variable in variables)
        if not any(bool((planted >> (abs(literal) - 1)) & 1) == (literal > 0) for literal in clause):
            index = rng.randrange(width)
            variable = abs(clause[index])
            clause = clause[:index] + ((variable if (planted >> (variable - 1)) & 1 else -variable),) + clause[index + 1:]
        if clause not in excluded:
            return clause
    raise RuntimeError("could not generate a new planted clause")


def synthetic_case(k: int, multiplier: int, duplicate_fraction: float, seed: int) -> Case:
    rng = random.Random(seed * 1000003 + k * 1009 + multiplier * 31 + int(duplicate_fraction * 10))
    total = k * multiplier
    unique_target = max(1, round(total * (1.0 - duplicate_fraction)))
    planted = rng.getrandbits(k)
    unique: list[tuple[int, ...]] = []
    excluded: set[tuple[int, ...]] = set()
    while len(unique) < unique_target:
        clause = planted_clause(rng, k, planted, excluded)
        unique.append(clause)
        excluded.add(clause)
    residual = list(unique)
    while len(residual) < total:
        residual.append(unique[rng.randrange(len(unique))])
    rng.shuffle(residual)
    edit = planted_clause(rng, k, planted, excluded)
    edited = list(residual)
    edited[rng.randrange(len(edited))] = edit
    actual_unique = len(set(residual))
    return Case(
        case_id=f"synthetic|k{k}|m{multiplier}|d{duplicate_fraction:.1f}|s{seed}",
        corpus="synthetic",
        model_id=f"planted-k{k}-m{multiplier}-d{duplicate_fraction:.1f}-s{seed}",
        history="synthetic",
        slice_kind="planted",
        k=k,
        residual=tuple(residual),
        planted_bits=planted,
        metadata={"clause_multiplier": multiplier, "target_duplicate_fraction": duplicate_fraction,
                  "actual_duplicate_fraction": (total - actual_unique) / total, "unique_clauses": actual_unique,
                  "seed": seed, "residual_clauses": total, "residual_literals": sum(map(len, residual))},
        edited_residual=tuple(edited),
    )


def load_synthetic_cases() -> list[Case]:
    return [synthetic_case(k, multiplier, duplicate, seed)
            for k in WIDTHS for multiplier in CLAUSE_MULTIPLIERS
            for duplicate in DUPLICATE_FRACTIONS for seed in SYNTHETIC_SEEDS]


def build_bdd(expr: Expr, k: int, dd_module, order: list[str]) -> BDDArtifact:
    setup_start = time.perf_counter_ns()
    manager = dd_module.BDD()
    _declare_dd_vars(manager, order)
    setup_ns = time.perf_counter_ns() - setup_start
    build_start = time.perf_counter_ns()
    root = expr_to_dd_bdd(expr, manager, {f"x{index}": f"x{index}" for index in range(k)})
    build_ns = time.perf_counter_ns() - build_start
    ident = bdd_backend_identity(manager)
    backend = "dd.cudd" if ident["is_cudd"] else "dd.autoref" if ident["is_autoref"] else ident["module"]
    return BDDArtifact(manager, root, setup_ns, build_ns, int(safe_bdd_node_count(manager, root) or 0), tuple(order), backend)


def best_bdd(expr: Expr, k: int, dd_module, seed: int) -> tuple[BDDArtifact, list[dict], int]:
    trials = []
    artifacts = []
    search_start = time.perf_counter_ns()
    for sweep in range(BEST_OF_K):
        order = robdd_variable_order(expr, k, "random", seed + sweep)
        artifact = build_bdd(expr, k, dd_module, order)
        artifacts.append(artifact)
        trials.append({"sweep": sweep, "seed": seed + sweep, "nodes": artifact.nodes,
                       "setup_ns": artifact.setup_ns, "build_ns": artifact.build_ns,
                       "order": artifact.order})
    search_ns = time.perf_counter_ns() - search_start
    best_index = min(range(len(artifacts)), key=lambda index: (artifacts[index].nodes, artifacts[index].build_ns, index))
    return artifacts[best_index], trials, search_ns


def bdd_extract_enumerate(artifact: BDDArtifact, k: int) -> int:
    value = 0
    care = {f"x{index}" for index in range(k)}
    for assignment in artifact.manager.pick_iter(artifact.root, care_vars=care):
        index = sum((1 << variable) for variable in range(k) if assignment[f"x{variable}"])
        value |= 1 << index
    return value


def bdd_extract_naive(artifact: BDDArtifact, k: int) -> int:
    value = 0
    for assignment in range(1 << k):
        mapped = {f"x{index}": bool((assignment >> index) & 1) for index in range(k)}
        if bdd_function_value(artifact.manager, artifact.root, mapped):
            value |= 1 << assignment
    return value


def packed_context_mask(k: int, context: Mapping[int, bool]) -> int:
    mask = (1 << (1 << k)) - 1
    pats = patterns(k)
    for variable, selected in context.items():
        mask &= pats[variable] if selected else ~pats[variable]
    return mask & ((1 << (1 << k)) - 1)


def make_point_queries(case: Case) -> tuple[int, ...]:
    rng = random.Random(int.from_bytes(hashlib.sha256((case.case_id + "|point").encode()).digest()[:8], "big"))
    if case.k == 8:
        values = list(range(256))
        rng.shuffle(values)
        return tuple(values)
    return tuple(rng.randrange(1 << case.k) for _ in range(POINT_QUERIES))


def make_contexts(case: Case, fraction: float) -> tuple[dict[int, bool], ...]:
    rng = random.Random(int.from_bytes(hashlib.sha256(f"{case.case_id}|ctx|{fraction}".encode()).digest()[:8], "big"))
    fixed = max(1, round(case.k * fraction))
    result = []
    for _ in range(PARTIAL_CONTEXTS):
        variables = rng.sample(range(case.k), fixed)
        result.append({variable: bool(rng.getrandbits(1)) for variable in variables})
    return tuple(result)


def solver_for(residual: tuple[tuple[int, ...], ...]):
    from pysat.solvers import Solver
    return Solver(name="cadical195", bootstrap_with=residual)


def sat_count(residual: tuple[tuple[int, ...], ...], k: int) -> int:
    solver = solver_for(residual)
    count = 0
    try:
        while solver.solve():
            model = {abs(literal): literal > 0 for literal in (solver.get_model() or [])}
            assignment = {variable: bool(model.get(variable, False)) for variable in range(1, k + 1)}
            count += 1
            solver.add_clause([(-variable if assignment[variable] else variable) for variable in range(1, k + 1)])
    finally:
        solver.delete()
    return count


def flat_program_json(program, packed: int, k: int) -> dict:
    return {"schema": "cm-flat-packed/v1", "k": k, "n_slots": program.n_slots, "root_slot": program.root_slot,
            "loads": program.loads, "ops": program.ops, "packed_hex": packed.to_bytes(1 << max(0, k - 3), "little").hex()}


def serialize_case(case_dir: Path, case: Case, cm_program, packed: int, bdd: BDDArtifact) -> dict:
    case_dir.mkdir(parents=True, exist_ok=False)
    cm_path = case_dir / "cm-flat-packed.json"
    start = time.perf_counter_ns()
    json_dump(cm_path, flat_program_json(cm_program, packed, case.k))
    cm_write_ns = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    cm_loaded = json.loads(cm_path.read_text(encoding="utf-8"))
    cm_read_ns = time.perf_counter_ns() - start
    cm_roundtrip = int.from_bytes(bytes.fromhex(cm_loaded["packed_hex"]), "little") == packed

    cnf_path = case_dir / "residual.dimacs"
    cnf_text = f"p cnf {case.k} {len(case.residual)}\n" + "".join(" ".join(map(str, clause)) + " 0\n" for clause in case.residual)
    start = time.perf_counter_ns()
    cnf_path.write_text(cnf_text, encoding="ascii", newline="\n")
    cnf_write_ns = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    parsed_clauses = tuple(tuple(map(int, line.split()[:-1])) for line in cnf_path.read_text(encoding="ascii").splitlines()[1:])
    cnf_read_ns = time.perf_counter_ns() - start
    cnf_roundtrip = cnf_bitset(parsed_clauses, case.k) == packed

    bdd_path = case_dir / "robdd.json"
    start = time.perf_counter_ns()
    dump_roots = [bdd.root] if bdd.backend == "dd.cudd" else {"f": bdd.root}
    bdd.manager.dump(str(bdd_path), roots=dump_roots, filetype="json")
    bdd_write_ns = time.perf_counter_ns() - start
    dd_module, error = select_dd_module("cudd" if bdd.backend == "dd.cudd" else "autoref")
    if dd_module is None:
        raise RuntimeError(error)
    loaded_manager = dd_module.BDD()
    start = time.perf_counter_ns()
    roots = loaded_manager.load(str(bdd_path))
    bdd_read_ns = time.perf_counter_ns() - start
    loaded_root = roots["f"] if isinstance(roots, dict) else roots[0]
    loaded = BDDArtifact(loaded_manager, loaded_root, 0, 0, int(safe_bdd_node_count(loaded_manager, loaded_root) or 0), bdd.order, bdd.backend)
    bdd_roundtrip = bdd_extract_enumerate(loaded, case.k) == packed
    return {
        "cm_serialized_bytes": cm_path.stat().st_size, "cm_serialize_ns": cm_write_ns, "cm_reload_ns": cm_read_ns,
        "cm_roundtrip_equal": cm_roundtrip, "cnf_serialized_bytes": cnf_path.stat().st_size,
        "cnf_serialize_ns": cnf_write_ns, "cnf_reload_ns": cnf_read_ns, "cnf_roundtrip_equal": cnf_roundtrip,
        "robdd_serialized_bytes": bdd_path.stat().st_size, "robdd_serialize_ns": bdd_write_ns,
        "robdd_reload_ns": bdd_read_ns, "robdd_roundtrip_equal": bdd_roundtrip,
    }


def run_case(case: Case, dd_module, backend_label: str, artifacts_root: Path, rounds: int, case_index: int) -> tuple[dict, list[dict]]:
    expression_start = time.perf_counter_ns()
    expression = expression_from_residual(case.residual, case.k)
    expression_build_ns = time.perf_counter_ns() - expression_start

    cse_start = time.perf_counter_ns()
    cse_program = compile_expr_cse(expression, flatten=True)
    cse_compile_ns = time.perf_counter_ns() - cse_start
    cm_diag: dict = {}
    cm_start = time.perf_counter_ns()
    cm_node = compile_expr_to_cm_ir(expression, diagnostics=cm_diag, reuse_cache=False, persistent_cache=False)
    cm_compile_ns = time.perf_counter_ns() - cm_start
    cm_program = get_flat_program(cm_node)
    evaluator_vars = tuple(f"x{index}" for index in reversed(range(case.k)))
    cm_call = lambda: _eval_words(cm_program, evaluator_vars, {})
    cse_call = lambda: _eval_words(cse_program, evaluator_vars, {})
    cnf_call = lambda: cnf_bitset(case.residual, case.k)
    packed = cnf_call()
    if not ((packed >> case.planted_bits) & 1):
        raise AssertionError(f"planted witness absent: {case.case_id}")
    if cm_call() != packed or cse_call() != packed:
        raise AssertionError(f"CM/CSE packed mismatch: {case.case_id}")

    fixed = build_bdd(expression, case.k, dd_module, [f"x{index}" for index in range(case.k)])
    seed = int.from_bytes(hashlib.sha256((case.case_id + "|order").encode()).digest()[:8], "big") & 0x7FFFFFFF
    best, order_trials, order_search_ns = best_bdd(expression, case.k, dd_module, seed)
    fixed_packed = bdd_extract_enumerate(fixed, case.k)
    best_packed = bdd_extract_enumerate(best, case.k)
    if fixed_packed != packed or best_packed != packed:
        raise AssertionError(f"ROBDD packed mismatch: {case.case_id}")

    warm_batch = 200 if case.k == 8 else 50 if case.k == 12 else 10
    extraction_arms = {"cm": (cm_call, warm_batch), "cse": (cse_call, warm_batch), "cnf": (cnf_call, warm_batch),
                       "robdd_enumerate": (lambda: bdd_extract_enumerate(fixed, case.k), 1)}
    if case.k <= 12:
        extraction_arms["robdd_naive"] = (lambda: bdd_extract_naive(fixed, case.k), 1)
    extraction_medians, extraction_samples = counterbalanced_medians(extraction_arms, rounds, case_index)

    points = make_point_queries(case)
    sat_solver = solver_for(case.residual)
    def packed_points():
        return tuple(bool((packed >> assignment) & 1) for assignment in points)
    def scalar_points():
        return tuple(scalar_residual(case.residual, assignment) for assignment in points)
    def bdd_points():
        return tuple(bool(bdd_function_value(fixed.manager, fixed.root,
            {f"x{index}": bool((assignment >> index) & 1) for index in range(case.k)})) for assignment in points)
    def sat_points():
        return tuple(sat_solver.solve(assumptions=[variable + 1 if (assignment >> variable) & 1 else -(variable + 1)
                                                   for variable in range(case.k)]) for assignment in points)
    point_truth = packed_points()
    if scalar_points() != point_truth or bdd_points() != point_truth or sat_points() != point_truth:
        raise AssertionError(f"point-query mismatch: {case.case_id}")
    point_arms = {"packed": (packed_points, 1), "scalar_cnf": (scalar_points, 1), "robdd": (bdd_points, 1), "cadical": (sat_points, 1)}
    point_medians, point_samples = counterbalanced_medians(point_arms, rounds, case_index + 1)

    partial_rows = []
    for fraction_index, fraction in enumerate(PARTIAL_FRACTIONS):
        contexts = make_contexts(case, fraction)
        def packed_partial():
            return tuple(bool(packed & packed_context_mask(case.k, context)) for context in contexts)
        def bdd_partial():
            return tuple(fixed.manager.let({f"x{variable}": selected for variable, selected in context.items()}, fixed.root) != fixed.manager.false
                         for context in contexts)
        def sat_partial():
            return tuple(sat_solver.solve(assumptions=[variable + 1 if selected else -(variable + 1)
                                                       for variable, selected in context.items()]) for context in contexts)
        truth = packed_partial()
        if bdd_partial() != truth or sat_partial() != truth:
            raise AssertionError(f"partial-query mismatch: {case.case_id} f={fraction}")
        medians, samples = counterbalanced_medians(
            {"packed": (packed_partial, 1), "robdd": (bdd_partial, 1), "cadical": (sat_partial, 1)},
            rounds, case_index + fraction_index,
        )
        partial_rows.append({"case_id": case.case_id, "corpus": case.corpus, "model_id": case.model_id, "k": case.k,
                             "fixed_fraction": fraction, "fixed_variables": len(contexts[0]), "contexts": len(contexts),
                             "decisions_equal": True, "packed_session_ns_median": medians["packed"],
                             "robdd_session_ns_median": medians["robdd"], "cadical_session_ns_median": medians["cadical"],
                             "packed_over_robdd": medians["packed"] / medians["robdd"],
                             "packed_over_cadical": medians["packed"] / medians["cadical"],
                             "samples_json": json.dumps(samples, separators=(",", ":"))})

    packed_count_start = time.perf_counter_ns()
    packed_count = packed.bit_count()
    packed_count_ns = time.perf_counter_ns() - packed_count_start
    bdd_count_start = time.perf_counter_ns()
    bdd_count = int(fixed.manager.count(fixed.root, nvars=case.k))
    bdd_count_ns = time.perf_counter_ns() - bdd_count_start
    sat_model_count = None
    sat_count_ns = None
    if case.k <= 12:
        sat_count_start = time.perf_counter_ns()
        sat_model_count = sat_count(case.residual, case.k)
        sat_count_ns = time.perf_counter_ns() - sat_count_start
    if bdd_count != packed_count or (sat_model_count is not None and sat_model_count != packed_count):
        raise AssertionError(f"count mismatch: {case.case_id}")

    serialization = serialize_case(artifacts_root / hashlib.sha256(case.case_id.encode()).hexdigest()[:16], case, cm_program, packed, fixed)
    if not all(serialization[key] for key in ("cm_roundtrip_equal", "cnf_roundtrip_equal", "robdd_roundtrip_equal")):
        raise AssertionError(f"serialization mismatch: {case.case_id}")

    cm_traced_ns, cm_peak = traced_peak(lambda: _eval_words(get_flat_program(compile_expr_to_cm_ir(expression)), evaluator_vars, {}))
    cse_traced_ns, cse_peak = traced_peak(lambda: _eval_words(compile_expr_cse(expression, flatten=True), evaluator_vars, {}))
    cnf_traced_ns, cnf_peak = traced_peak(cnf_call)
    bdd_traced_ns, bdd_peak = traced_peak(lambda: build_bdd(expression, case.k, dd_module, [f"x{index}" for index in range(case.k)]))
    sat_solver.delete()

    cm_metrics = program_metrics(cm_program)
    cse_metrics = program_metrics(cse_program)
    packed_bytes = 1 << max(0, case.k - 3)
    row = {
        "case_id": case.case_id, "corpus": case.corpus, "model_id": case.model_id, "history": case.history,
        "slice_kind": case.slice_kind, "k": case.k, "residual_clauses": len(case.residual),
        "residual_unique_clauses": len(set(case.residual)), "residual_literals": sum(map(len, case.residual)),
        "duplicate_fraction": 1.0 - len(set(case.residual)) / max(1, len(case.residual)),
        "packed_true_count": packed_count, "solution_density": packed_count / (1 << case.k),
        "packed_sha256": sha256_bytes(packed.to_bytes(packed_bytes, "little")), "all_relation_arms_equal": True,
        "expression_build_ns": expression_build_ns, "cm_compile_ns": cm_compile_ns, "cse_compile_ns": cse_compile_ns,
        "robdd_backend": fixed.backend, "requested_backend": backend_label, "robdd_fixed_setup_ns": fixed.setup_ns,
        "robdd_fixed_build_ns": fixed.build_ns, "robdd_fixed_nodes": fixed.nodes, "robdd_best5_setup_ns": best.setup_ns,
        "robdd_best5_selected_build_ns": best.build_ns, "robdd_best5_nodes": best.nodes,
        "robdd_best5_search_ns": order_search_ns, "robdd_best5_trials_json": json.dumps(order_trials, separators=(",", ":")),
        "cm_flat_instructions": cm_metrics["flat_instructions"], "cse_flat_instructions": cse_metrics["flat_instructions"],
        "cm_executed_word_ops": cm_metrics["executed_word_ops"], "cse_executed_word_ops": cse_metrics["executed_word_ops"],
        "cm_packed_ns_median": extraction_medians["cm"], "cse_packed_ns_median": extraction_medians["cse"],
        "cnf_packed_ns_median": extraction_medians["cnf"], "robdd_extract_enumerate_ns_median": extraction_medians["robdd_enumerate"],
        "robdd_extract_naive_ns_median": extraction_medians.get("robdd_naive"),
        "cm_over_cnf_packed": extraction_medians["cm"] / extraction_medians["cnf"],
        "cm_over_cse_packed": extraction_medians["cm"] / extraction_medians["cse"],
        "cm_over_robdd_enumerate": extraction_medians["cm"] / extraction_medians["robdd_enumerate"],
        "extraction_samples_json": json.dumps(extraction_samples, separators=(",", ":")),
        "point_queries": len(points), "point_equal": True, "packed_point_session_ns_median": point_medians["packed"],
        "scalar_cnf_point_session_ns_median": point_medians["scalar_cnf"], "robdd_point_session_ns_median": point_medians["robdd"],
        "cadical_point_session_ns_median": point_medians["cadical"],
        "packed_point_over_robdd": point_medians["packed"] / point_medians["robdd"],
        "packed_point_over_cadical": point_medians["packed"] / point_medians["cadical"],
        "point_samples_json": json.dumps(point_samples, separators=(",", ":")),
        "packed_count_ns": packed_count_ns, "robdd_count_ns": bdd_count_ns, "cadical_enum_count_ns": sat_count_ns,
        "cadical_enum_count": sat_model_count, "count_equal": True,
        "cm_traced_build_eval_ns": cm_traced_ns, "cm_tracemalloc_peak_bytes": cm_peak,
        "cse_traced_build_eval_ns": cse_traced_ns, "cse_tracemalloc_peak_bytes": cse_peak,
        "cnf_traced_eval_ns": cnf_traced_ns, "cnf_tracemalloc_peak_bytes": cnf_peak,
        "robdd_traced_build_ns": bdd_traced_ns, "robdd_tracemalloc_peak_bytes": bdd_peak,
        **serialization,
        "metadata_json": json.dumps(case.metadata, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
    }
    return row, partial_rows


def run_family(case: Case, dd_module, backend_label: str) -> dict:
    assert case.edited_residual is not None
    base_expr = expression_from_residual(case.residual, case.k)
    edit_expr = expression_from_residual(case.edited_residual, case.k)
    clear_cm_ir_persistent_cache()
    base_diag: dict = {}
    start = time.perf_counter_ns()
    base_cm = compile_expr_to_cm_ir(base_expr, diagnostics=base_diag, persistent_cache=True, reuse_cache=False)
    base_cm_ns = time.perf_counter_ns() - start
    edit_diag: dict = {}
    start = time.perf_counter_ns()
    edit_cm = compile_expr_to_cm_ir(edit_expr, diagnostics=edit_diag, persistent_cache=True, reuse_cache=False)
    edit_cm_reuse_ns = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    compile_expr_to_cm_ir(edit_expr, persistent_cache=False, reuse_cache=False)
    edit_cm_fresh_ns = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    compile_expr_cse(base_expr, flatten=True)
    compile_expr_cse(edit_expr, flatten=True)
    cse_pair_ns = time.perf_counter_ns() - start

    order = [f"x{index}" for index in range(case.k)]
    base_bdd = build_bdd(base_expr, case.k, dd_module, order)
    start = time.perf_counter_ns()
    edit_root_shared = expr_to_dd_bdd(edit_expr, base_bdd.manager, {name: name for name in order})
    edit_bdd_shared_ns = time.perf_counter_ns() - start
    shared_nodes = int(safe_bdd_node_count(base_bdd.manager, edit_root_shared) or 0)
    edit_bdd_fresh = build_bdd(edit_expr, case.k, dd_module, order)

    evaluator_vars = tuple(reversed(order))
    base_packed = _eval_words(get_flat_program(base_cm), evaluator_vars, {})
    edit_packed = _eval_words(get_flat_program(edit_cm), evaluator_vars, {})
    bdd_base_packed = bdd_extract_enumerate(base_bdd, case.k)
    bdd_edit_packed = bdd_extract_enumerate(BDDArtifact(base_bdd.manager, edit_root_shared, 0, 0, shared_nodes, tuple(order), base_bdd.backend), case.k)
    if base_packed != bdd_base_packed or edit_packed != bdd_edit_packed:
        raise AssertionError(f"family relation mismatch: {case.case_id}")
    changed = (base_packed ^ edit_packed).bit_count()
    return {
        "case_id": case.case_id, "corpus": case.corpus, "k": case.k,
        "clause_multiplier": case.metadata["clause_multiplier"], "duplicate_fraction": case.metadata["actual_duplicate_fraction"],
        "robdd_backend": base_bdd.backend, "requested_backend": backend_label,
        "cm_base_compile_ns": base_cm_ns, "cm_edit_reuse_compile_ns": edit_cm_reuse_ns,
        "cm_edit_fresh_compile_ns": edit_cm_fresh_ns, "cm_reuse_over_fresh": edit_cm_reuse_ns / edit_cm_fresh_ns,
        "cm_edit_persistent_hits": int(edit_diag.get("ir_persistent_cache_hits", 0)),
        "cm_edit_persistent_misses": int(edit_diag.get("ir_persistent_cache_misses", 0)),
        "cse_pair_compile_ns": cse_pair_ns, "robdd_base_setup_ns": base_bdd.setup_ns,
        "robdd_base_build_ns": base_bdd.build_ns, "robdd_edit_shared_build_ns": edit_bdd_shared_ns,
        "robdd_edit_fresh_setup_ns": edit_bdd_fresh.setup_ns, "robdd_edit_fresh_build_ns": edit_bdd_fresh.build_ns,
        "robdd_shared_over_fresh_build": edit_bdd_shared_ns / edit_bdd_fresh.build_ns,
        "robdd_base_nodes": base_bdd.nodes, "robdd_edit_shared_nodes": shared_nodes, "robdd_edit_fresh_nodes": edit_bdd_fresh.nodes,
        "changed_assignments": changed, "changed_fraction": changed / (1 << case.k), "relations_equal_across_arms": True,
    }


def summarize(rows: list[dict], partial_rows: list[dict], family_rows: list[dict], backend_label: str) -> dict:
    real = [row for row in rows if row["corpus"] == "real"]
    synthetic = [row for row in rows if row["corpus"] == "synthetic"]
    real_by_k = {}
    real_history_clustered_by_k = {}
    for k in WIDTHS:
        selected = [row for row in real if int(row["k"]) == k]
        real_by_k[str(k)] = {
            "n": len(selected),
            "cm_over_cnf_packed_geomean": geomean(row["cm_over_cnf_packed"] for row in selected) if selected else None,
            "cm_over_cse_packed_geomean": geomean(row["cm_over_cse_packed"] for row in selected) if selected else None,
            "cm_over_robdd_enumerate_geomean": geomean(row["cm_over_robdd_enumerate"] for row in selected) if selected else None,
            "robdd_fixed_nodes_median": statistics.median(row["robdd_fixed_nodes"] for row in selected) if selected else None,
        }
        histories = sorted({row["history"] for row in selected})
        per_history = {
            history: {
                metric: geomean(float(row[metric]) for row in selected if row["history"] == history)
                for metric in ("cm_over_cnf_packed", "cm_over_cse_packed", "cm_over_robdd_enumerate")
            }
            for history in histories
        }
        real_history_clustered_by_k[str(k)] = {
            "history_count": len(histories),
            "per_history_geomean": per_history,
            **{
                f"{metric}_geomean": geomean(values[metric] for values in per_history.values()) if per_history else None
                for metric in ("cm_over_cnf_packed", "cm_over_cse_packed", "cm_over_robdd_enumerate")
            },
        }
    synthetic_cells = []
    for k in WIDTHS:
        for multiplier in CLAUSE_MULTIPLIERS:
            for duplicate in DUPLICATE_FRACTIONS:
                selected = [row for row in synthetic if int(row["k"]) == k
                            and json.loads(row["metadata_json"])["clause_multiplier"] == multiplier
                            and json.loads(row["metadata_json"])["target_duplicate_fraction"] == duplicate]
                synthetic_cells.append({"k": k, "clause_multiplier": multiplier, "duplicate_fraction": duplicate,
                                        "n": len(selected),
                                        "cm_over_cnf_packed_geomean": geomean(row["cm_over_cnf_packed"] for row in selected) if selected else None,
                                        "cm_over_cse_packed_geomean": geomean(row["cm_over_cse_packed"] for row in selected) if selected else None,
                                        "cm_over_robdd_enumerate_geomean": geomean(row["cm_over_robdd_enumerate"] for row in selected) if selected else None})
    return {
        "schema_version": "cm-representation-battery/v1", "status": "completed", "requested_backend": backend_label,
        "actual_backends": sorted({row["robdd_backend"] for row in rows}), "case_count": len(rows),
        "real_case_count": len(real), "synthetic_case_count": len(synthetic), "partial_row_count": len(partial_rows),
        "family_row_count": len(family_rows), "correctness": {"relation_mismatches": 0, "point_mismatches": 0,
            "partial_mismatches": 0, "count_mismatches": 0, "serialization_mismatches": 0, "family_mismatches": 0},
        "real_by_k": real_by_k, "real_history_clustered_by_k": real_history_clustered_by_k,
        "synthetic_cells": synthetic_cells,
        "coverage_gaps": [
            "d4/d-DNNF, CUDD sifting, native RSS, and adjacent-version deltas are separately labeled supplemental arms.",
            "The installed Python CUDD wrapper exposes no native ZDD interface; no substitute is labeled CUDD ZDD.",
            "tracemalloc excludes allocations made inside C extensions.",
        ],
        "claim_boundary": "bounded conditioned feature-model relations and planted CNFs; not whole-model enumeration or natural user sessions",
    }


def write_checksums(output: Path) -> None:
    files = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    text = "".join(f"{sha256_file(path)}  {path.relative_to(output).as_posix()}\n" for path in files)
    (output / "CHECKSUMS.sha256").write_text(text, encoding="ascii")


def current_git_head() -> str:
    supplied = os.environ.get("CM_BATTERY_GIT_HEAD")
    if supplied:
        return supplied
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unavailable"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pilot-run", type=Path, default=PILOT_RUN)
    parser.add_argument("--source-root", type=Path, default=pilot.DEFAULT_SOURCE)
    parser.add_argument("--protocol", default=PROTOCOL)
    parser.add_argument("--bdd-backend", choices=("auto", "autoref", "cudd"), default="autoref")
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    parser.add_argument("--limit-cases", type=int, default=0, help="diagnostic smoke only")
    parser.add_argument("--skip-real", action="store_true", help="diagnostic smoke only")
    parser.add_argument("--skip-synthetic", action="store_true", help="diagnostic smoke only")
    args = parser.parse_args()
    if args.rounds < 1 or args.limit_cases < 0:
        parser.error("rounds must be positive and limit-cases nonnegative")
    output = args.output.resolve()
    pilot_run = args.pilot_run.resolve()
    source_root = args.source_root.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    dd_module, error = select_dd_module(args.bdd_backend)
    if dd_module is None:
        raise SystemExit(f"requested BDD backend unavailable: {error}")
    output.mkdir(parents=True)
    artifacts_root = output / "serialized"
    artifacts_root.mkdir()
    real_cases, inputs = load_real_cases(pilot_run, source_root)
    if args.skip_real:
        real_cases = []
    synthetic_cases = [] if args.skip_synthetic else load_synthetic_cases()
    cases = real_cases + synthetic_cases
    if args.limit_cases:
        cases = cases[:args.limit_cases]
    rows = []
    partial_rows = []
    family_rows = []
    corpus_rows = []
    started = time.perf_counter()
    for index, case in enumerate(cases):
        print(f"[{index + 1}/{len(cases)}] {case.case_id}", flush=True)
        row, partial = run_case(case, dd_module, args.bdd_backend, artifacts_root, args.rounds, index)
        rows.append(row)
        partial_rows.extend(partial)
        if case.edited_residual is not None:
            family_rows.append(run_family(case, dd_module, args.bdd_backend))
        corpus_rows.append({"case_id": case.case_id, "corpus": case.corpus, "model_id": case.model_id,
                            "history": case.history, "slice_kind": case.slice_kind, "k": case.k,
                            "planted_bits": case.planted_bits, "residual": case.residual,
                            "edited_residual": case.edited_residual, "metadata": case.metadata,
                            "packed_sha256": row["packed_sha256"], "packed_true_count": row["packed_true_count"]})
    summary = summarize(rows, partial_rows, family_rows, args.bdd_backend)
    summary["wall_seconds"] = time.perf_counter() - started
    write_csv(output / "cases.csv", rows)
    write_csv(output / "partial-contexts.csv", partial_rows)
    if family_rows:
        write_csv(output / "families.csv", family_rows)
    jsonl_dump(output / "corpus.jsonl", corpus_rows)
    json_dump(output / "summary.json", summary)
    import dd
    import pysat
    manifest = {
        "schema_version": "cm-representation-battery-manifest/v1", "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": args.protocol,
        "pilot_source_run": str(pilot_run.relative_to(REPO)) if pilot_run.is_relative_to(REPO) else str(pilot_run),
        "official_source_root": str(source_root), "official_inputs": inputs,
        "requested_backend": args.bdd_backend, "dd_version": dd.__version__, "pysat_version": pysat.__version__,
        "python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "rounds": args.rounds,
        "widths": WIDTHS, "best_of_k": BEST_OF_K, "point_queries": POINT_QUERIES, "partial_contexts": PARTIAL_CONTEXTS,
        "git_head": current_git_head(),
        "diagnostic_limit_cases": args.limit_cases, "diagnostic_skip_real": args.skip_real,
        "diagnostic_skip_synthetic": args.skip_synthetic,
    }
    json_dump(output / "manifest.json", manifest)
    write_checksums(output)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
