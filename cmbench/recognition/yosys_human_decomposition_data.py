"""Independent bounded decomposition cases derived from Yosys-bench generators.

The source generators were written outside this project and pinned before C7.
This adapter lowers their documented combinational semantics into the existing
Boolean expression DAG.  An arithmetic scalar oracle independently checks every
lowered truth table before a case is admitted.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Expr, Not, Or, Var, Xor

from .decomposition_data import canonical, packed_sha256
from .features import structural_digest
from .natural_decomposition import analyze_decomposition, semantic_variables
from .portfolio import admit, reference_bits

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "docs" / "recognition" / "source_fixtures" / "yosys-bench-human-decomposition-20260830"
SOURCE_MANIFEST = FIXTURE_ROOT / "SOURCE_MANIFEST.json"
SOURCE_COMMIT = "52ff6fa991f2ab509618d8aaad02f307aac78848"
SOURCE_URL = "https://github.com/YosysHQ/yosys-bench.git"
DATASET_SCHEMA = "crse-yosys-human-decomposition-dataset/v1"
SPLITS = ("sealed_a", "sealed_b")
CASES_PER_LABEL_PER_SPLIT = 10


@dataclass(frozen=True)
class Candidate:
    family: str
    source_generator: str
    parameters: dict[str, int | str]
    expression: Expr
    variable_specs: tuple[tuple[str, int], ...]
    scalar: Callable[[dict[tuple[str, int], int]], int]


def _and(left: Expr | None, right: Expr | None) -> Expr | None:
    return None if left is None or right is None else And(left, right)


def _or(left: Expr | None, right: Expr | None) -> Expr | None:
    if left is None:
        return right
    if right is None:
        return left
    return left if left == right else Or(left, right)


def _xor(left: Expr | None, right: Expr | None) -> Expr | None:
    if left is None:
        return right
    if right is None:
        return left
    return None if left == right else Xor(left, right)


def _and_many(values: list[Expr]) -> Expr:
    if not values:
        raise ValueError("empty conjunction is outside the source adapter")
    result = values[0]
    for value in values[1:]:
        result = And(result, value)
    return result


def _or_many(values: list[Expr]) -> Expr:
    if not values:
        raise ValueError("empty disjunction is outside the source adapter")
    result = values[0]
    for value in values[1:]:
        result = Or(result, value)
    return result


def _add_vectors(left: list[Expr | None], right: list[Expr | None]) -> list[Expr | None]:
    width = max(len(left), len(right))
    result: list[Expr | None] = []
    carry: Expr | None = None
    for bit in range(width):
        first = left[bit] if bit < len(left) else None
        second = right[bit] if bit < len(right) else None
        result.append(_xor(_xor(first, second), carry))
        carry = _or(_and(first, second), _or(_and(first, carry), _and(second, carry)))
    result.append(carry)
    while result and result[-1] is None:
        result.pop()
    return result


def _variable_map(specs: tuple[tuple[str, int], ...]):
    return {specification: Var(index) for index, specification in enumerate(specs)}


def _integer(values: dict[tuple[str, int], int], port: str, width: int) -> int:
    return sum(values.get((port, bit), 0) << bit for bit in range(width))


def _add_candidate(first_width: int, second_width: int, output_bit: int) -> Candidate | None:
    specifications = tuple(
        [("A", bit) for bit in range(min(first_width, output_bit + 1))]
        + [("B", bit) for bit in range(min(second_width, output_bit + 1))]
    )
    variables = _variable_map(specifications)
    left = [variables.get(("A", bit)) for bit in range(first_width)]
    right = [variables.get(("B", bit)) for bit in range(second_width)]
    outputs = _add_vectors(left, right)
    if output_bit >= len(outputs) or outputs[output_bit] is None:
        return None
    return Candidate("arith_add", "verilog/benchmarks_small/arith_ops/generate.py",
        {"a_width": first_width, "b_width": second_width, "output_bit": output_bit},
        outputs[output_bit], specifications,
        lambda values: ((_integer(values, "A", first_width) + _integer(values, "B", second_width))
                        >> output_bit) & 1)


def _multiply_candidate(first_width: int, second_width: int, output_bit: int) -> Candidate | None:
    specifications = tuple(
        [("A", bit) for bit in range(first_width)] + [("B", bit) for bit in range(second_width)]
    )
    variables = _variable_map(specifications)
    accumulated: list[Expr | None] = []
    for second in range(second_width):
        partial = [None] * second + [
            And(variables[("A", first)], variables[("B", second)]) for first in range(first_width)
        ]
        accumulated = _add_vectors(accumulated, partial)
    if output_bit >= len(accumulated) or accumulated[output_bit] is None:
        return None
    return Candidate("arith_mul", "verilog/benchmarks_small/arith_ops/generate.py",
        {"a_width": first_width, "b_width": second_width, "output_bit": output_bit},
        accumulated[output_bit], specifications,
        lambda values: ((_integer(values, "A", first_width) * _integer(values, "B", second_width))
                        >> output_bit) & 1)


def _popcount_candidate(width: int, output_bit: int) -> Candidate | None:
    specifications = tuple(("din", bit) for bit in range(width))
    variables = _variable_map(specifications)
    accumulated: list[Expr | None] = []
    for bit in range(width):
        accumulated = _add_vectors(accumulated, [variables[("din", bit)]])
    if output_bit >= len(accumulated) or accumulated[output_bit] is None:
        return None
    return Candidate("popcount", "verilog/benchmarks_small/popcount/generate.py",
        {"width": width, "output_bit": output_bit}, accumulated[output_bit], specifications,
        lambda values: (sum(values[("din", bit)] for bit in range(width)) >> output_bit) & 1)


def _mux_candidate(inputs: int) -> Candidate:
    select_width = int(math.ceil(math.log2(inputs)))
    specifications = tuple([("i", bit) for bit in range(inputs)]
                           + [("s", bit) for bit in range(select_width)])
    variables = _variable_map(specifications)
    terms = []
    for selected in range(inputs):
        match = [variables[("s", bit)] if selected & (1 << bit) else Not(variables[("s", bit)])
                 for bit in range(select_width)]
        terms.append(_and_many([variables[("i", selected)], *match]))
    return Candidate("mux_index", "verilog/benchmarks_small/mux/common.py",
        {"inputs": inputs, "width": 1}, _or_many(terms), specifications,
        lambda values: values[("i", _integer(values, "s", select_width))])


def _onehot_candidate(width: int, output_index: int) -> Candidate:
    specifications = tuple(("din", bit) for bit in range(width))
    variables = _variable_map(specifications)
    terms = [variables[("din", bit)] if output_index & (1 << bit) else Not(variables[("din", bit)])
             for bit in range(width)]
    return Candidate("bin2onehot", "verilog/benchmarks_small/onehot/generate.py",
        {"width": width, "output_index": output_index}, _and_many(terms), specifications,
        lambda values: int(_integer(values, "din", width) == output_index))


def candidates() -> list[Candidate]:
    result: list[Candidate] = []
    for first_width in range(1, 6):
        for second_width in range(first_width, 6):
            if first_width + second_width > 10:
                continue
            for output_bit in range(max(first_width, second_width) + 1):
                candidate = _add_candidate(first_width, second_width, output_bit)
                if candidate is not None:
                    result.append(candidate)
    for first_width in range(2, 5):
        for second_width in range(first_width, 5):
            if first_width + second_width > 8:
                continue
            for output_bit in range(first_width + second_width):
                candidate = _multiply_candidate(first_width, second_width, output_bit)
                if candidate is not None:
                    result.append(candidate)
    for width in range(2, 9):
        for output_bit in range(int(math.ceil(math.log2(width)))):
            candidate = _popcount_candidate(width, output_bit)
            if candidate is not None:
                result.append(candidate)
    result.extend(_mux_candidate(inputs) for inputs in (2, 4))
    for width in range(2, 9):
        for output_index in sorted({0, 1, (1 << width) // 3, (1 << width) - 1}):
            result.append(_onehot_candidate(width, output_index))
    return result


def _scalar_bits(candidate: Candidate) -> int:
    n_vars = len(candidate.variable_specs)
    result = 0
    for assignment in range(1 << n_vars):
        values = {specification: (assignment >> (n_vars - 1 - index)) & 1
                  for index, specification in enumerate(candidate.variable_specs)}
        value = candidate.scalar(values)
        if type(value) is not int or value not in (0, 1):
            raise ValueError("non-Boolean Yosys source oracle")
        result |= value << assignment
    return result


def _identity(candidate: Candidate) -> str:
    return hashlib.sha256(canonical({"family": candidate.family, "parameters": candidate.parameters,
        "variables": candidate.variable_specs})).hexdigest()


def _round_robin(rows: list[dict], label: int):
    by_family: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["label"] == label:
            by_family[row["family"]].append(row)
    for values in by_family.values():
        values.sort(key=lambda row: row["selection_sha256"])
    families = sorted(by_family)
    offset = 0
    while any(offset < len(by_family[family]) for family in families):
        for family in families:
            if offset < len(by_family[family]):
                yield by_family[family][offset]
        offset += 1


def make_yosys_human_documents() -> tuple[list[dict], dict]:
    source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if (source.get("schema") != "crse-yosys-human-source-fixture/v1"
            or source.get("upstream_commit") != SOURCE_COMMIT or source.get("license") != "ISC"):
        raise ValueError("invalid Yosys human source manifest")
    for row in source["files"]:
        path = FIXTURE_ROOT / row["fixture_path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError(f"changed Yosys human source fixture: {row['fixture_path']}")

    admitted = []
    semantic_seen: set[tuple[int, int]] = set()
    alpha_seen: set[str] = set()
    rejection = Counter()
    for candidate in candidates():
        n_vars = len(candidate.variable_specs)
        try:
            if not 2 <= n_vars <= 10:
                raise ValueError("candidate support outside 2..10")
            admit(candidate.expression, n_vars, 1)
            bits = reference_bits(candidate.expression, n_vars)
            scalar = _scalar_bits(candidate)
            if bits != scalar or semantic_variables(bits, n_vars) != tuple(range(n_vars)):
                raise ValueError("source adapter and independent scalar oracle disagree")
            analysis = analyze_decomposition(bits, n_vars)
            document = expr_to_json_dag(candidate.expression)
            alpha = structural_digest(candidate.expression, alpha_rename=True)
            semantic_key = (n_vars, bits)
            if semantic_key in semantic_seen:
                rejection["semantic_duplicate"] += 1
                continue
            if alpha in alpha_seen:
                rejection["alpha_structural_duplicate"] += 1
                continue
            identity = _identity(candidate)
            admitted.append({"schema": DATASET_SCHEMA, "case_id": f"yosys-{candidate.family}-{identity[:16]}",
                "split": None, "natural": True, "training_use": False, "source_repository": SOURCE_URL,
                "source_commit": SOURCE_COMMIT, "source_generator": candidate.source_generator,
                "family": candidate.family, "parameters": candidate.parameters,
                "variable_specs": [[port, bit] for port, bit in candidate.variable_specs],
                "n_vars": n_vars, "label": int(analysis.decomposable),
                "components": [list(component) for component in analysis.components],
                "witness": analysis.witness, "semantic_sha256": packed_sha256(bits, n_vars),
                "structural_sha256": structural_digest(candidate.expression), "alpha_sha256": alpha,
                "expression_v2": document, "selection_sha256": identity})
            semantic_seen.add(semantic_key)
            alpha_seen.add(alpha)
        except (ValueError, TypeError, RecursionError):
            rejection["admission_or_identity"] += 1

    selected = []
    for label in (1, 0):
        ordered = list(_round_robin(admitted, label))
        needed = len(SPLITS) * CASES_PER_LABEL_PER_SPLIT
        if len(ordered) < needed:
            raise ValueError(f"insufficient independent Yosys label-{label} candidates: {len(ordered)}")
        for index, row in enumerate(ordered[:needed]):
            row = dict(row)
            row["split"] = SPLITS[index // CASES_PER_LABEL_PER_SPLIT]
            selected.append(row)
    selected.sort(key=lambda row: (SPLITS.index(row["split"]), row["selection_sha256"]))
    audit = validate_yosys_human_documents(selected)
    provenance = {"schema": "crse-yosys-human-decomposition-provenance/v1",
        "source": "YosysHQ/yosys-bench human-authored generator semantics",
        "upstream_url": SOURCE_URL, "upstream_commit": SOURCE_COMMIT, "license": "ISC",
        "source_manifest": str(SOURCE_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "source_manifest_sha256": hashlib.sha256(SOURCE_MANIFEST.read_bytes()).hexdigest(),
        "selection": "label-balanced deterministic hash order with source-family round robin",
        "splits": list(SPLITS), "cases_per_label_per_split": CASES_PER_LABEL_PER_SPLIT,
        "candidate_count": len(candidates()), "admitted_candidate_count": len(admitted),
        "rejected": dict(rejection), "audit": audit, "network_access_performed": False,
        "source_checkout_modified": False}
    return selected, provenance


def validate_yosys_human_documents(documents: list[dict]) -> dict:
    if type(documents) is not list or len(documents) != 2 * len(SPLITS) * CASES_PER_LABEL_PER_SPLIT:
        raise ValueError("invalid Yosys human decomposition row count")
    counts = Counter()
    families = defaultdict(set)
    semantics, alphas, identities = set(), set(), set()
    for row in documents:
        if (type(row) is not dict or row.get("schema") != DATASET_SCHEMA or row.get("split") not in SPLITS
                or row.get("training_use") is not False or row.get("source_commit") != SOURCE_COMMIT
                or type(row.get("label")) is not int or row["label"] not in (0, 1)
                or type(row.get("n_vars")) is not int or not 2 <= row["n_vars"] <= 10):
            raise ValueError("invalid Yosys human decomposition document")
        if row["case_id"] in identities:
            raise ValueError("duplicate Yosys case identity")
        identities.add(row["case_id"])
        from cm_expr_serde import expr_from_json
        expression = expr_from_json(row["expression_v2"])
        bits = reference_bits(expression, row["n_vars"])
        analysis = analyze_decomposition(bits, row["n_vars"])
        semantic = (row["n_vars"], bits)
        alpha = structural_digest(expression, alpha_rename=True)
        if (int(analysis.decomposable) != row["label"] or analysis.witness != row["witness"]
                or [list(component) for component in analysis.components] != row["components"]
                or packed_sha256(bits, row["n_vars"]) != row["semantic_sha256"]
                or structural_digest(expression) != row["structural_sha256"] or alpha != row["alpha_sha256"]):
            raise ValueError("changed Yosys human decomposition semantics")
        if semantic in semantics or alpha in alphas:
            raise ValueError("duplicate Yosys human semantic or alpha structure")
        semantics.add(semantic)
        alphas.add(alpha)
        counts[(row["split"], row["label"])] += 1
        families[row["split"]].add(row["family"])
    if any(counts[(split, label)] != CASES_PER_LABEL_PER_SPLIT for split in SPLITS for label in (0, 1)):
        raise ValueError("unbalanced Yosys human decomposition split")
    return {"rows": len(documents),
        "split_label_counts": {f"{split}/{label}": counts[(split, label)] for split in SPLITS for label in (0, 1)},
        "families_by_split": {split: sorted(values) for split, values in families.items()},
        "semantic_duplicates": 0, "alpha_structural_duplicates": 0,
        "positive_count": sum(row["label"] for row in documents),
        "size_counts": dict(sorted(Counter(str(row["n_vars"]) for row in documents).items()))}
