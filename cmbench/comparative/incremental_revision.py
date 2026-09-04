"""Exact local gate for CM compilation across adjacent feature-model revisions.

This module is experimental. It does not change a production selector or default.
The incremental arm uses a deterministic digest-radix conjunction layout so an edit
rebuilds only the paths above changed canonical clauses.
"""

from __future__ import annotations

from collections import Counter, OrderedDict, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
import csv
import gc
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys
import time
from typing import Any, Iterable, Iterator, Mapping, Sequence

import cm_ir
from bitset_backend import (
    FlatProgram,
    PreparedFlatEvaluation,
    _bind_flat_program,
    _eval_prepared_flat,
    clear_bitset_env_cache,
    compile_expr_cse,
    compile_expr_flat,
    get_flat_program,
    program_metrics,
)
from cm_exprlib import And, Expr, Not, Or, Var
from cm_ir import compile_expr_to_cm_ir


REPO = Path(__file__).resolve().parents[2]
DATA_DIR = (
    REPO
    / "deliverables_n22_24"
    / "master_explainer_2026_08_03"
    / "use_case_benchmarks_2026-08-27"
    / "runs"
    / "configuration-fm-version-delta-full21-2026-08-27"
)
CASES_PATH = DATA_DIR / "cases.jsonl"
ADMISSIONS_PATH = DATA_DIR / "admissions.csv"
CASES_SHA256 = "3a4a394f458e0064994b4339858401e523f8dea836a3a697120f9db83299ef0e"
ADMISSIONS_SHA256 = "9afbf841866b26e6bc0615160d1e64c6f627904a8729fdd9837c809fccbb113a"
SOURCE_COMMIT = "afa60ee2c836e7bdc4068e0f4f128ea31158d2ad"
ARMS = ("cm_cold", "cm_persistent", "cm_incremental_radix", "cse_flat", "raw_flat")
QUERY_COUNTS = (1, 2, 4, 8, 16, 32, 64)
DEFAULT_ROUNDS = 5
DEFAULT_EVALUATION_REPETITIONS = 16
BOOTSTRAP_DRAWS = 4000
BOOTSTRAP_SEED = 2026090401
EXPRESSION_CACHE_MAX_ENTRIES = 4096
CM_CACHE_MAX_ENTRIES = 16384

Clause = tuple[int, ...]
CNF = tuple[Clause, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def packed_sha(value: int, k: int) -> str:
    return hashlib.sha256(value.to_bytes(1 << max(0, k - 3), "little")).hexdigest()


def canonical_json_sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def normalize_cnf(clauses: Iterable[Iterable[int]], k: int) -> CNF:
    """Return a deterministic, semantically equivalent clause set."""
    normalized: set[Clause] = set()
    for source_clause in clauses:
        literals = {int(literal) for literal in source_clause}
        if 0 in literals:
            raise ValueError("literal zero is not valid inside a stored clause")
        if any(abs(literal) > k for literal in literals):
            raise ValueError("literal outside the declared variable range")
        if any(-literal in literals for literal in literals):
            continue
        clause = tuple(sorted(literals, key=lambda literal: (abs(literal), literal < 0)))
        if not clause:
            return ((),)
        normalized.add(clause)
    return tuple(sorted(normalized, key=lambda clause: (len(clause), clause)))


def _balanced(nodes: Sequence[Expr], constructor: type[And] | type[Or]) -> Expr:
    if not nodes:
        raise ValueError("a balanced expression requires at least one node")
    level = list(nodes)
    while len(level) > 1:
        following: list[Expr] = []
        for index in range(0, len(level), 2):
            if index + 1 == len(level):
                following.append(level[index])
            else:
                following.append(constructor(level[index], level[index + 1]))
        level = following
    return level[0]


def expression_from_cnf(clauses: CNF, k: int) -> Expr:
    if k < 1:
        raise ValueError("the frozen natural corpus requires at least one variable")
    variables = tuple(Var(index) for index in range(k))
    if clauses == ((),):
        return And(variables[0], Not(variables[0]))
    if not clauses:
        return Or(variables[0], Not(variables[0]))
    clause_nodes: list[Expr] = []
    for clause in clauses:
        literals = [
            variables[abs(literal) - 1]
            if literal > 0
            else Not(variables[abs(literal) - 1])
            for literal in clause
        ]
        clause_nodes.append(_balanced(literals, Or) if len(literals) > 1 else literals[0])
    return _balanced(clause_nodes, And) if len(clause_nodes) > 1 else clause_nodes[0]


def direct_cnf_bits(clauses: CNF, k: int) -> int:
    """Independent packed CNF evaluator with x0 as the least-significant bit."""
    width = 1 << k
    full = (1 << width) - 1
    if clauses == ((),):
        return 0
    patterns = tuple(
        sum(1 << assignment for assignment in range(width) if (assignment >> index) & 1)
        for index in range(k)
    )
    result = full
    for clause in clauses:
        clause_bits = 0
        for literal in clause:
            value = patterns[abs(literal) - 1]
            clause_bits |= value if literal > 0 else full ^ value
        result &= clause_bits
    return result


def _clause_bytes(clause: Clause) -> bytes:
    return b",".join(str(literal).encode("ascii") for literal in clause)


@dataclass(frozen=True)
class LayoutResult:
    expression: Expr
    identity: str
    normalized_clause_count: int
    clause_hits: int
    clause_misses: int
    branch_hits: int
    branch_misses: int
    evictions: int


class IncrementalRadixLayout:
    """Bounded LRU of clause and unchanged-radix-region expression objects."""

    def __init__(self, max_entries: int = EXPRESSION_CACHE_MAX_ENTRIES) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = int(max_entries)
        self.entries: OrderedDict[tuple[object, ...], Expr] = OrderedDict()
        self.hits = Counter()
        self.misses = Counter()
        self.evictions = 0

    def _get(self, key: tuple[object, ...], kind: str) -> Expr | None:
        value = self.entries.get(key)
        if value is None:
            self.misses[kind] += 1
            return None
        self.entries.move_to_end(key)
        self.hits[kind] += 1
        return value

    def _put(self, key: tuple[object, ...], value: Expr) -> Expr:
        self.entries[key] = value
        self.entries.move_to_end(key)
        while len(self.entries) > self.max_entries:
            self.entries.popitem(last=False)
            self.evictions += 1
        return value

    def _literal(self, literal: int, k: int) -> Expr:
        key = ("literal", k, literal)
        cached = self._get(key, "clause")
        if cached is not None:
            return cached
        variable = Var(abs(literal) - 1)
        return self._put(key, variable if literal > 0 else Not(variable))

    def _clause(self, clause: Clause, k: int) -> Expr:
        key = ("clause", k, clause)
        cached = self._get(key, "clause")
        if cached is not None:
            return cached
        literals = [self._literal(literal, k) for literal in clause]
        expression = _balanced(literals, Or) if len(literals) > 1 else literals[0]
        return self._put(key, expression)

    def _combine(self, left: tuple[Expr, bytes], right: tuple[Expr, bytes]) -> tuple[Expr, bytes]:
        if right[1] < left[1]:
            left, right = right, left
        identity = hashlib.sha256(b"branch:" + left[1] + right[1]).digest()
        key = ("branch", left[1], right[1])
        cached = self._get(key, "branch")
        if cached is None:
            cached = self._put(key, And(left[0], right[0]))
        return cached, identity

    def _radix(self, leaves: Sequence[tuple[bytes, Expr]], bit: int = 0) -> tuple[Expr, bytes]:
        if len(leaves) == 1:
            digest, expression = leaves[0]
            return expression, hashlib.sha256(b"leaf:" + digest).digest()
        if bit >= 256:
            level = [(expression, hashlib.sha256(b"leaf:" + digest).digest()) for digest, expression in leaves]
            while len(level) > 1:
                following = []
                for index in range(0, len(level), 2):
                    following.append(level[index] if index + 1 == len(level) else self._combine(level[index], level[index + 1]))
                level = following
            return level[0]
        byte_index, bit_index = divmod(bit, 8)
        left = [item for item in leaves if not (item[0][byte_index] >> (7 - bit_index)) & 1]
        right = [item for item in leaves if (item[0][byte_index] >> (7 - bit_index)) & 1]
        if not left or not right:
            return self._radix(leaves, bit + 1)
        return self._combine(self._radix(left, bit + 1), self._radix(right, bit + 1))

    def expression(self, clauses: CNF, k: int) -> LayoutResult:
        before_hits = self.hits.copy()
        before_misses = self.misses.copy()
        before_evictions = self.evictions
        identity = canonical_json_sha({"k": k, "clauses": clauses})
        if clauses == ((),):
            key = ("constant", k, False)
            expression = self._get(key, "branch")
            if expression is None:
                variable = Var(0)
                expression = self._put(key, And(variable, Not(variable)))
        elif not clauses:
            key = ("constant", k, True)
            expression = self._get(key, "branch")
            if expression is None:
                variable = Var(0)
                expression = self._put(key, Or(variable, Not(variable)))
        else:
            leaves = []
            for clause in clauses:
                digest = hashlib.sha256(b"clause:" + _clause_bytes(clause)).digest()
                leaves.append((digest, self._clause(clause, k)))
            leaves.sort(key=lambda item: item[0])
            expression = self._radix(leaves)[0]
        return LayoutResult(
            expression=expression,
            identity=identity,
            normalized_clause_count=len(clauses),
            clause_hits=self.hits["clause"] - before_hits["clause"],
            clause_misses=self.misses["clause"] - before_misses["clause"],
            branch_hits=self.hits["branch"] - before_hits["branch"],
            branch_misses=self.misses["branch"] - before_misses["branch"],
            evictions=self.evictions - before_evictions,
        )


@contextmanager
def isolated_persistent_cm_cache(max_entries: int = CM_CACHE_MAX_ENTRIES) -> Iterator[OrderedDict[str, cm_ir.CMNode]]:
    previous_cache = cm_ir._PERSISTENT_IR_CACHE
    previous_limit = cm_ir._PERSISTENT_IR_CACHE_MAXSIZE
    pool: OrderedDict[str, cm_ir.CMNode] = OrderedDict()
    cm_ir._PERSISTENT_IR_CACHE = pool
    cm_ir._PERSISTENT_IR_CACHE_MAXSIZE = int(max_entries)
    try:
        yield pool
    finally:
        cm_ir._PERSISTENT_IR_CACHE = previous_cache
        cm_ir._PERSISTENT_IR_CACHE_MAXSIZE = previous_limit


def evaluate_program(program: FlatProgram, k: int) -> int:
    support = tuple(f"x{index}" for index in range(k - 1, -1, -1))
    template, full_mask = _bind_flat_program(program, support, {})
    return _eval_prepared_flat(PreparedFlatEvaluation(program, template, full_mask, False))


def _deep_size(value: object, seen: set[int] | None = None) -> int:
    """Approximate Python-owned retained bytes without following modules/threads."""
    if seen is None:
        seen = set()
    identity = id(value)
    if identity in seen:
        return 0
    seen.add(identity)
    size = sys.getsizeof(value)
    if isinstance(value, Mapping):
        return size + sum(_deep_size(key, seen) + _deep_size(item, seen) for key, item in value.items())
    if isinstance(value, (tuple, list, set, frozenset, Counter)):
        return size + sum(_deep_size(item, seen) for item in value)
    if isinstance(value, FlatProgram):
        return size + sum(
            _deep_size(getattr(value, name), seen)
            for name in ("loads", "load_vars", "ops", "release_after", "bound_cache", "word_plan")
        )
    attributes = getattr(value, "__dict__", None)
    if isinstance(attributes, dict):
        return size + _deep_size(attributes, seen)
    return size


def _compile_program(expression: Expr, arm: str, diagnostics: dict[str, Any]) -> FlatProgram:
    if arm in {"cm_cold", "cm_persistent", "cm_incremental_radix"}:
        node = compile_expr_to_cm_ir(
            expression,
            diagnostics,
            persistent_cache=arm != "cm_cold",
            reuse_cache=False,
            share_aware_flatten=arm != "cm_incremental_radix",
        )
        return get_flat_program(node)
    if arm == "cse_flat":
        return compile_expr_cse(expression, flatten=True)
    if arm == "raw_flat":
        return compile_expr_flat(expression)
    raise ValueError(f"unknown arm: {arm}")


def _timed_compile(
    clauses: CNF,
    k: int,
    arm: str,
    layout: IncrementalRadixLayout | None,
) -> tuple[FlatProgram, Expr, dict[str, Any]]:
    started = time.perf_counter_ns()
    layout_result = layout.expression(clauses, k) if layout is not None else None
    expression = layout_result.expression if layout_result is not None else expression_from_cnf(clauses, k)
    laid_out = time.perf_counter_ns()
    diagnostics: dict[str, Any] = {}
    before_pool = len(cm_ir._PERSISTENT_IR_CACHE) if arm in {"cm_persistent", "cm_incremental_radix"} else 0
    program = _compile_program(expression, arm, diagnostics)
    finished = time.perf_counter_ns()
    after_pool = len(cm_ir._PERSISTENT_IR_CACHE) if arm in {"cm_persistent", "cm_incremental_radix"} else 0
    misses = int(diagnostics.get("ir_persistent_cache_misses", 0))
    return program, expression, {
        "layout_ns": laid_out - started,
        "compile_lower_ns": finished - laid_out,
        "construction_ns": finished - started,
        "persistent_hits": int(diagnostics.get("ir_persistent_cache_hits", 0)),
        "persistent_misses": misses,
        "persistent_evictions": max(0, before_pool + misses - after_pool),
        "persistent_size": after_pool,
        "layout_identity": layout_result.identity if layout_result is not None else canonical_json_sha({"k": k, "clauses": clauses}),
        "layout_clause_hits": layout_result.clause_hits if layout_result is not None else 0,
        "layout_clause_misses": layout_result.clause_misses if layout_result is not None else 0,
        "layout_branch_hits": layout_result.branch_hits if layout_result is not None else 0,
        "layout_branch_misses": layout_result.branch_misses if layout_result is not None else 0,
        "layout_evictions": layout_result.evictions if layout_result is not None else 0,
    }


def run_arm_pair(
    arm: str,
    earlier: CNF,
    later: CNF,
    k: int,
    oracle: tuple[int, int],
    *,
    evaluation_repetitions: int = DEFAULT_EVALUATION_REPETITIONS,
    expression_cache_max_entries: int = EXPRESSION_CACHE_MAX_ENTRIES,
    cm_cache_max_entries: int = CM_CACHE_MAX_ENTRIES,
) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    if evaluation_repetitions < 1:
        raise ValueError("evaluation_repetitions must be positive")
    clear_bitset_env_cache()
    layout = IncrementalRadixLayout(expression_cache_max_entries) if arm == "cm_incremental_radix" else None

    @contextmanager
    def scope() -> Iterator[OrderedDict[str, cm_ir.CMNode] | None]:
        if arm in {"cm_persistent", "cm_incremental_radix"}:
            with isolated_persistent_cm_cache(cm_cache_max_entries) as pool:
                yield pool
        else:
            yield None

    with scope() as pool:
        earlier_program, earlier_expr, earlier_stats = _timed_compile(earlier, k, arm, layout)
        later_program, later_expr, later_stats = _timed_compile(later, k, arm, layout)
        if earlier_stats["layout_identity"] != later_stats["layout_identity"] and earlier_program is later_program:
            raise AssertionError(f"{arm} returned the earlier program for a changed normalized CNF")
        earlier_bits = evaluate_program(earlier_program, k)
        later_bits = evaluate_program(later_program, k)
        if (earlier_bits, later_bits) != oracle:
            raise AssertionError(f"{arm} did not match the independent CNF evaluator")
        started = time.perf_counter_ns()
        checksum = 0
        for _ in range(evaluation_repetitions):
            checksum ^= evaluate_program(earlier_program, k) ^ evaluate_program(later_program, k)
        evaluation_batch_ns = time.perf_counter_ns() - started
        if arm == "cm_incremental_radix":
            state: object = (layout.entries, pool, earlier_program, later_program)
        elif arm == "cm_persistent":
            state = (pool, earlier_program, later_program)
        else:
            state = (earlier_program, later_program)
        retained_bytes = _deep_size(state)

    changed = earlier_bits ^ later_bits
    earlier_metrics = program_metrics(earlier_program)
    later_metrics = program_metrics(later_program)
    return {
        "arm": arm,
        "earlier_layout_ns": earlier_stats["layout_ns"],
        "earlier_compile_lower_ns": earlier_stats["compile_lower_ns"],
        "earlier_construction_ns": earlier_stats["construction_ns"],
        "later_layout_ns": later_stats["layout_ns"],
        "later_compile_lower_ns": later_stats["compile_lower_ns"],
        "update_construction_ns": later_stats["construction_ns"],
        "resident_pair_construction_ns": earlier_stats["construction_ns"] + later_stats["construction_ns"],
        "evaluation_repetitions": evaluation_repetitions,
        "evaluation_batch_ns": evaluation_batch_ns,
        "evaluation_pair_ns": evaluation_batch_ns / evaluation_repetitions,
        "retained_python_bytes": retained_bytes,
        "persistent_hits_earlier": earlier_stats["persistent_hits"],
        "persistent_hits_update": later_stats["persistent_hits"],
        "persistent_misses_earlier": earlier_stats["persistent_misses"],
        "persistent_misses_update": later_stats["persistent_misses"],
        "persistent_evictions_total": earlier_stats["persistent_evictions"] + later_stats["persistent_evictions"],
        "persistent_size_after_update": later_stats["persistent_size"],
        "layout_clause_hits_update": later_stats["layout_clause_hits"],
        "layout_clause_misses_update": later_stats["layout_clause_misses"],
        "layout_branch_hits_update": later_stats["layout_branch_hits"],
        "layout_branch_misses_update": later_stats["layout_branch_misses"],
        "layout_evictions_total": earlier_stats["layout_evictions"] + later_stats["layout_evictions"],
        "earlier_layout_identity": earlier_stats["layout_identity"],
        "later_layout_identity": later_stats["layout_identity"],
        "invalidation_identity_changed": earlier_stats["layout_identity"] != later_stats["layout_identity"],
        "program_identity_changed": earlier_program is not later_program,
        "earlier_program_slots": earlier_program.n_slots,
        "later_program_slots": later_program.n_slots,
        "earlier_flat_instructions": earlier_metrics["flat_instructions"],
        "later_flat_instructions": later_metrics["flat_instructions"],
        "earlier_executed_bigint_ops": earlier_metrics["executed_bigint_ops"],
        "later_executed_bigint_ops": later_metrics["executed_bigint_ops"],
        "earlier_packed_sha256": packed_sha(earlier_bits, k),
        "later_packed_sha256": packed_sha(later_bits, k),
        "changed_packed_sha256": packed_sha(changed, k),
        "changed_assignments": changed.bit_count(),
        "output_bytes": 3 * (1 << max(0, k - 3)),
        "checksum": checksum,
        "exact": True,
        "_keepalive": (earlier_expr, later_expr),
    }


def load_cases(root: Path = REPO) -> list[dict[str, Any]]:
    cases_path = root / CASES_PATH.relative_to(REPO)
    admissions_path = root / ADMISSIONS_PATH.relative_to(REPO)
    if sha256_file(cases_path) != CASES_SHA256:
        raise ValueError("frozen cases input identity changed")
    if sha256_file(admissions_path) != ADMISSIONS_SHA256:
        raise ValueError("frozen admissions input identity changed")
    with admissions_path.open(encoding="utf-8", newline="") as handle:
        admissions = list(csv.DictReader(handle))
    admitted = {row["transition_id"]: row for row in admissions if row["admitted"] == "True"}
    refused = [row for row in admissions if row["admitted"] == "False"]
    if len(admitted) != 20 or len(refused) != 1:
        raise ValueError("frozen transition admission counts changed")
    cases = []
    with cases_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            transition_id = row["case_id"].split("|", 1)[0]
            admission = admitted.get(transition_id)
            if admission is None:
                raise ValueError(f"case is not tied to an admitted transition: {transition_id}")
            if row["k"] not in {8, 12, 16} or row["slice_kind"] not in {"incidence", "hash"}:
                raise ValueError("case left the frozen width/slice matrix")
            cases.append({
                **row,
                "transition_id": transition_id,
                "history": admission["history"],
                "label": admission["label"],
                "split": "confirmation" if admission["label"] == "last" else "development",
            })
    if len(cases) != 120 or len({row["case_id"] for row in cases}) != 120:
        raise ValueError("frozen case cardinality changed")
    if Counter(row["split"] for row in cases) != {"development": 78, "confirmation": 42}:
        raise ValueError("frozen development/confirmation split changed")
    return cases


def structural_change(earlier_source: Sequence[Sequence[int]], later_source: Sequence[Sequence[int]], k: int) -> dict[str, int]:
    earlier_multiset = Counter(tuple(int(literal) for literal in clause) for clause in earlier_source)
    later_multiset = Counter(tuple(int(literal) for literal in clause) for clause in later_source)
    earlier = set(normalize_cnf(earlier_source, k))
    later = set(normalize_cnf(later_source, k))
    return {
        "source_clause_occurrences_earlier": sum(earlier_multiset.values()),
        "source_clause_occurrences_later": sum(later_multiset.values()),
        "source_occurrences_added": sum((later_multiset - earlier_multiset).values()),
        "source_occurrences_removed": sum((earlier_multiset - later_multiset).values()),
        "normalized_clauses_earlier": len(earlier),
        "normalized_clauses_later": len(later),
        "normalized_clauses_shared": len(earlier & later),
        "normalized_clauses_added": len(later - earlier),
        "normalized_clauses_removed": len(earlier - later),
    }


def run_case(
    case: Mapping[str, Any],
    *,
    rounds: int = DEFAULT_ROUNDS,
    evaluation_repetitions: int = DEFAULT_EVALUATION_REPETITIONS,
) -> list[dict[str, Any]]:
    if rounds < 1:
        raise ValueError("rounds must be positive")
    k = int(case["k"])
    earlier = normalize_cnf(case["earlier_residual"], k)
    later = normalize_cnf(case["later_residual"], k)
    oracle = (direct_cnf_bits(earlier, k), direct_cnf_bits(later, k))
    saved = (case["earlier_packed_sha256"], case["later_packed_sha256"], case["changed_packed_sha256"])
    actual = (packed_sha(oracle[0], k), packed_sha(oracle[1], k), packed_sha(oracle[0] ^ oracle[1], k))
    if actual != saved:
        raise AssertionError(f"independent oracle does not match saved artifact: {case['case_id']}")
    change = structural_change(case["earlier_residual"], case["later_residual"], k)
    rows = []
    rotation = int(hashlib.sha256(case["case_id"].encode()).hexdigest()[:8], 16) % len(ARMS)
    for round_index in range(rounds):
        order = ARMS[rotation:] + ARMS[:rotation]
        if round_index % 2:
            order = tuple(reversed(order))
        rotation = (rotation + 1) % len(ARMS)
        for order_index, arm in enumerate(order):
            gc.collect()
            result = run_arm_pair(
                arm,
                earlier,
                later,
                k,
                oracle,
                evaluation_repetitions=evaluation_repetitions,
            )
            result.pop("_keepalive")
            if (
                result["earlier_packed_sha256"],
                result["later_packed_sha256"],
                result["changed_packed_sha256"],
            ) != saved:
                raise AssertionError(f"{arm} does not match saved artifact: {case['case_id']}")
            rows.append({
                "case_id": case["case_id"],
                "transition_id": case["transition_id"],
                "history": case["history"],
                "label": case["label"],
                "split": case["split"],
                "slice_kind": case["slice_kind"],
                "k": k,
                "round": round_index,
                "order_index": order_index,
                **change,
                **result,
            })
    return rows


def _geomean(values: Sequence[float]) -> float:
    if not values or any(value <= 0 for value in values):
        raise ValueError("geometric mean requires positive values")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def _ratio_summary(case_values: Sequence[tuple[str, str, float]], draws: int = BOOTSTRAP_DRAWS) -> dict[str, Any]:
    by_history: dict[str, list[float]] = defaultdict(list)
    for _case_id, history, ratio in case_values:
        by_history[history].append(ratio)
    per_history = {history: _geomean(values) for history, values in sorted(by_history.items())}
    result = {
        "case_count": len(case_values),
        "history_count": len(per_history),
        "geomean": _geomean(list(per_history.values())),
        "per_history_geomean": per_history,
        "bootstrap_draws": draws,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }
    if draws:
        rng = random.Random(BOOTSTRAP_SEED)
        histories = sorted(per_history)
        samples = sorted(
            _geomean([per_history[rng.choice(histories)] for _ in histories])
            for _ in range(draws)
        )
        result["ci95"] = [samples[int(0.025 * draws)], samples[min(draws - 1, int(0.975 * draws))]]
    return result


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rounds = len({int(row["round"]) for row in rows})
    expected_rows = 120 * len(ARMS) * rounds
    if len(rows) != expected_rows:
        raise ValueError("raw result matrix is incomplete")
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    case_metadata: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if row["arm"] not in ARMS or not row["exact"]:
            raise ValueError("unknown or inexact result row")
        grouped[(row["case_id"], row["arm"])].append(row)
        case_metadata[row["case_id"]] = row

    medians: dict[tuple[str, str], dict[str, float]] = {}
    fields = ("update_construction_ns", "resident_pair_construction_ns", "evaluation_pair_ns", "retained_python_bytes")
    for key, arm_rows in grouped.items():
        medians[key] = {field: statistics.median(float(row[field]) for row in arm_rows) for field in fields}

    confirmation = [case_id for case_id, row in case_metadata.items() if row["split"] == "confirmation"]

    def ratios(numerator: str, denominator: str, field: str) -> list[tuple[str, str, float]]:
        return [
            (
                case_id,
                str(case_metadata[case_id]["history"]),
                medians[(case_id, numerator)][field] / medians[(case_id, denominator)][field],
            )
            for case_id in confirmation
        ]

    update_vs_cold = _ratio_summary(ratios("cm_incremental_radix", "cm_cold", "update_construction_ns"))
    update_vs_persistent = _ratio_summary(ratios("cm_incremental_radix", "cm_persistent", "update_construction_ns"))
    persistent_update_vs_cold = _ratio_summary(ratios("cm_persistent", "cm_cold", "update_construction_ns"))
    retained_ratios = ratios("cm_incremental_radix", "cm_persistent", "retained_python_bytes")
    retained_vs_persistent = _ratio_summary(retained_ratios)
    retained_vs_persistent["max_case_ratio"] = max(value for _case_id, _history, value in retained_ratios)

    q_totals: dict[str, Any] = {}
    persistent_q_totals: dict[str, Any] = {}
    for q in QUERY_COUNTS:
        values = []
        persistent_values = []
        for case_id in confirmation:
            inc = medians[(case_id, "cm_incremental_radix")]
            persistent = medians[(case_id, "cm_persistent")]
            cse = medians[(case_id, "cse_flat")]
            inc_total = inc["resident_pair_construction_ns"] + q * inc["evaluation_pair_ns"]
            persistent_total = persistent["resident_pair_construction_ns"] + q * persistent["evaluation_pair_ns"]
            cse_total = cse["resident_pair_construction_ns"] + q * cse["evaluation_pair_ns"]
            values.append((case_id, str(case_metadata[case_id]["history"]), inc_total / cse_total))
            persistent_values.append((case_id, str(case_metadata[case_id]["history"]), persistent_total / cse_total))
        q_totals[str(q)] = _ratio_summary(values)
        persistent_q_totals[str(q)] = _ratio_summary(persistent_values)

    confirmation_by_history: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for case_id in confirmation:
        confirmation_by_history[str(case_metadata[case_id]["history"])].append(case_metadata[case_id])
    change_coverage = {
        history: {
            "case_count": len(values),
            "cases_with_normalized_change": sum(
                int(row["normalized_clauses_added"]) + int(row["normalized_clauses_removed"]) > 0
                for row in values
            ),
        }
        for history, values in sorted(confirmation_by_history.items())
    }
    incremental_rows = [
        row for row in rows
        if row["split"] == "confirmation" and row["arm"] == "cm_incremental_radix"
    ]
    reuse_by_history = {
        history: sum(
            int(row["layout_clause_hits_update"])
            + int(row["layout_branch_hits_update"])
            + int(row["persistent_hits_update"])
            for row in incremental_rows
            if row["history"] == history
        )
        for history in sorted(confirmation_by_history)
    }
    exact_invalidation = all(
        bool(row["invalidation_identity_changed"])
        == (int(row["normalized_clauses_added"]) + int(row["normalized_clauses_removed"]) > 0)
        and (
            not bool(row["invalidation_identity_changed"])
            or bool(row["program_identity_changed"])
        )
        for row in incremental_rows
    )
    gates = {
        "correctness": all(bool(row["exact"]) for row in rows),
        "confirmation_coverage": len(confirmation) == 42 and len(confirmation_by_history) == 7,
        "real_change_activation": all(item["cases_with_normalized_change"] > 0 for item in change_coverage.values()),
        "incremental_reuse": all(value > 0 for value in reuse_by_history.values()),
        "exact_invalidation_identity": exact_invalidation,
        "update_construction_advantage": update_vs_cold["geomean"] <= 0.90 and update_vs_cold["ci95"][1] < 1.0,
        "current_cache_advantage": update_vs_persistent["geomean"] < 1.0,
        "retained_memory_bound": retained_vs_persistent["max_case_ratio"] <= 1.25,
        "task_control_break_even": any(
            result["geomean"] < 1.0 and result["ci95"][1] < 1.0
            for result in q_totals.values()
        ),
    }
    gates["promotion"] = all(gates.values())
    return {
        "schema": "cm-incremental-revision-local-gate/v1",
        "status": "completed",
        "row_count": len(rows),
        "case_count": len(case_metadata),
        "development_case_count": sum(row["split"] == "development" for row in case_metadata.values()),
        "confirmation_case_count": len(confirmation),
        "arms": list(ARMS),
        "query_counts": list(QUERY_COUNTS),
        "claim_boundary": "local Windows/Python bounded feature-model revision gate; not whole-model, production, neural, or universal performance evidence",
        "confirmation_change_coverage": change_coverage,
        "confirmation_reuse_by_history": reuse_by_history,
        "incremental_update_over_cold_cm": update_vs_cold,
        "incremental_update_over_current_persistent_cm": update_vs_persistent,
        "current_persistent_update_over_cold_cm": persistent_update_vs_cold,
        "incremental_retained_over_current_persistent_cm": retained_vs_persistent,
        "incremental_total_over_cse_flat_by_q": q_totals,
        "current_persistent_total_over_cse_flat_by_q": persistent_q_totals,
        "gates": gates,
    }
