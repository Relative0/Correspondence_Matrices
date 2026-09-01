"""Fresh exact GF(2) cases from previously unused Yosys-bench generators.

The pinned repository was already available locally, but none of the generator
families in this module appeared in the C7 Yosys confirmation table.  Each
adapter has a scalar Boolean oracle that is independent of the expression DAG
lowering used by the timed methods.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Callable

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Expr, Not, Or, Var, Xor

from cmbench.comparative.contracts import canonical_bytes
from cmbench.recognition.gf2_decomposition import truth_sha256
from cmbench.recognition.natural_decomposition import semantic_variables
from cmbench.recognition.portfolio import admit, reference_bits


SOURCE_COMMIT = "52ff6fa991f2ab509618d8aaad02f307aac78848"
SOURCE_URL = "https://github.com/YosysHQ/yosys-bench.git"
SOURCE_GENERATORS = (
    "verilog/benchmarks_small/addertree/generate.py",
    "verilog/benchmarks_small/decoder/generate.py",
    "verilog/benchmarks_small/lfsr/generate.py",
    "verilog/benchmarks_small/mul/common.py",
    "verilog/benchmarks_small/mul/generate.py",
    "verilog/benchmarks_small/muladd/common.py",
    "verilog/benchmarks_small/muladd/generate.py",
)
DATASET_SCHEMA = "crse-c23-yosys-unused-generator-gf2-dataset/v1"


@dataclass(frozen=True)
class Candidate:
    family: str
    source_generator: str
    parameters: dict[str, int | str | bool]
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
        raise ValueError("empty conjunction")
    result = values[0]
    for value in values[1:]:
        result = And(result, value)
    return result


def _or_many(values: list[Expr]) -> Expr:
    if not values:
        raise ValueError("empty disjunction")
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


def _variable_map(specs: tuple[tuple[str, int], ...]) -> dict[tuple[str, int], Expr]:
    return {specification: Var(index) for index, specification in enumerate(specs)}


def _integer(values: dict[tuple[str, int], int], port: str, width: int) -> int:
    return sum(values.get((port, bit), 0) << bit for bit in range(width))


def _match(select: list[Expr], value: int) -> Expr:
    return _and_many([
        variable if value & (1 << bit) else Not(variable)
        for bit, variable in enumerate(select)
    ])


def _select_candidate(inputs: int, reverse: bool) -> Candidate:
    select_width = max(1, (inputs - 1).bit_length())
    specs = tuple([("din", bit) for bit in range(inputs)]
                  + [("sel", bit) for bit in range(select_width)])
    variables = _variable_map(specs)
    select = [variables[("sel", bit)] for bit in range(select_width)]
    terms = []
    for selected in range(inputs):
        source = inputs - 1 - selected if reverse else selected
        terms.append(And(variables[("din", source)], _match(select, selected)))
    family = "decoder_reverse_shift" if reverse else "decoder_index"
    return Candidate(
        family,
        "verilog/benchmarks_small/decoder/generate.py",
        {"inputs": inputs, "reverse": reverse},
        _or_many(terms),
        specs,
        lambda values: values[("din", inputs - 1 - _integer(values, "sel", select_width)
                               if reverse else _integer(values, "sel", select_width))]
        if _integer(values, "sel", select_width) < inputs else 0,
    )


def _setclr_candidate(inputs: int, output_bit: int, set_bit: bool) -> Candidate:
    select_width = max(1, (inputs - 1).bit_length())
    specs = tuple([("din", output_bit)]
                  + [("sel", bit) for bit in range(select_width)])
    variables = _variable_map(specs)
    select = [variables[("sel", bit)] for bit in range(select_width)]
    selected = _match(select, output_bit)
    original = variables[("din", output_bit)]
    expression = Or(original, selected) if set_bit else And(original, Not(selected))
    family = "decoder_set_bit" if set_bit else "decoder_clear_bit"
    return Candidate(
        family,
        "verilog/benchmarks_small/decoder/generate.py",
        {"inputs": inputs, "output_bit": output_bit, "set_bit": set_bit},
        expression,
        specs,
        lambda values: int(
            set_bit if _integer(values, "sel", select_width) == output_bit
            else values[("din", output_bit)]),
    )


def _addertree_candidate(inputs: int, output_bit: int) -> Candidate:
    input_width = 4
    specs = tuple((f"din{word}", bit)
                  for word in range(inputs) for bit in range(output_bit + 1))
    variables = _variable_map(specs)
    accumulated: list[Expr | None] = []
    for word in range(inputs):
        accumulated = _add_vectors(
            accumulated,
            [variables[(f"din{word}", bit)] for bit in range(output_bit + 1)],
        )
    expression = accumulated[output_bit]
    if expression is None:
        raise ValueError("addertree output unexpectedly constant")
    return Candidate(
        "addertree_sum",
        "verilog/benchmarks_small/addertree/generate.py",
        {"inputs": inputs, "input_width": input_width, "output_bit": output_bit},
        expression,
        specs,
        lambda values: (sum(
            _integer(values, f"din{word}", output_bit + 1) for word in range(inputs)
        ) >> output_bit) & 1,
    )


def _product_vector(variables: dict[tuple[str, int], Expr], a_width: int,
                    b_width: int) -> list[Expr | None]:
    accumulated: list[Expr | None] = []
    for second in range(b_width):
        partial = [None] * second + [
            And(variables[("A", first)], variables[("B", second)])
            for first in range(a_width)
        ]
        accumulated = _add_vectors(accumulated, partial)
    return accumulated


def _mul_candidate(b_width: int, output_bit: int) -> Candidate:
    a_used = output_bit + 1
    b_used = min(b_width, output_bit + 1)
    specs = tuple([("A", bit) for bit in range(a_used)]
                  + [("B", bit) for bit in range(b_used)])
    variables = _variable_map(specs)
    product = _product_vector(variables, a_used, b_used)
    expression = product[output_bit]
    if expression is None:
        raise ValueError("multiply output unexpectedly constant")
    return Candidate(
        "multiply_low_cone",
        "verilog/benchmarks_small/mul/common.py",
        {"a_width": 16, "b_width": b_width, "output_bit": output_bit,
         "signed": False, "registered": False},
        expression,
        specs,
        lambda values: ((_integer(values, "A", a_used)
                         * _integer(values, "B", b_used)) >> output_bit) & 1,
    )


def _muladd_candidate(b_width: int, output_bit: int) -> Candidate:
    a_used = output_bit + 1
    b_used = min(b_width, output_bit + 1)
    c_used = output_bit + 1
    specs = tuple([("A", bit) for bit in range(a_used)]
                  + [("B", bit) for bit in range(b_used)]
                  + [("C", bit) for bit in range(c_used)])
    variables = _variable_map(specs)
    product = _product_vector(variables, a_used, b_used)
    result = _add_vectors(product, [variables[("C", bit)] for bit in range(c_used)])
    expression = result[output_bit]
    if expression is None:
        raise ValueError("multiply-add output unexpectedly constant")
    return Candidate(
        "multiply_add_low_cone",
        "verilog/benchmarks_small/muladd/common.py",
        {"a_width": 16, "b_width": b_width, "c_width": 32,
         "output_bit": output_bit, "signed": False, "registered": False},
        expression,
        specs,
        lambda values: ((_integer(values, "A", a_used)
                         * _integer(values, "B", b_used)
                         + _integer(values, "C", c_used)) >> output_bit) & 1,
    )


def _lfsr_candidate(length: int, taps: tuple[int, ...]) -> Candidate:
    specs = tuple(("state", tap) for tap in taps)
    variables = _variable_map(specs)
    expression = variables[specs[0]]
    for specification in specs[1:]:
        expression = Not(Xor(expression, variables[specification]))

    def scalar(values: dict[tuple[str, int], int]) -> int:
        result = values[specs[0]]
        for specification in specs[1:]:
            result = 1 - (result ^ values[specification])
        return result

    return Candidate(
        "lfsr_feedback",
        "verilog/benchmarks_small/lfsr/generate.py",
        {"length": length, "taps": ",".join(str(value) for value in taps)},
        expression,
        specs,
        scalar,
    )


def candidates() -> list[Candidate]:
    result: list[Candidate] = []
    for inputs in (2, 3, 4, 5):
        result.extend((_select_candidate(inputs, False), _select_candidate(inputs, True)))
    for inputs in (3, 4, 5, 6, 7, 8, 10, 15, 24, 32, 55, 64):
        for output_bit in range(inputs):
            result.extend((
                _setclr_candidate(inputs, output_bit, False),
                _setclr_candidate(inputs, output_bit, True),
            ))
    for inputs in (3, 4, 5, 6):
        for output_bit in range(3):
            if inputs * (output_bit + 1) <= 10:
                result.append(_addertree_candidate(inputs, output_bit))
    for b_width in (2, 4, 8, 16):
        for output_bit in range(1, 8):
            if output_bit + 1 + min(b_width, output_bit + 1) <= 10:
                result.append(_mul_candidate(b_width, output_bit))
    for b_width in (8, 16):
        for output_bit in range(3):
            support = 2 * (output_bit + 1) + min(b_width, output_bit + 1)
            if support <= 10:
                result.append(_muladd_candidate(b_width, output_bit))
    result.extend((
        _lfsr_candidate(8, (8, 6, 5, 4)),
        _lfsr_candidate(24, (24, 23, 22, 17)),
        _lfsr_candidate(37, (37, 5, 4, 3, 2, 1)),
    ))
    return result


def scalar_bits(candidate: Candidate) -> int:
    n_vars = len(candidate.variable_specs)
    bits = 0
    for assignment in range(1 << n_vars):
        values = {
            specification: (assignment >> (n_vars - 1 - index)) & 1
            for index, specification in enumerate(candidate.variable_specs)
        }
        value = candidate.scalar(values)
        if type(value) is not int or value not in (0, 1):
            raise ValueError("non-Boolean Yosys scalar oracle")
        bits |= value << assignment
    return bits


def candidate_identity(candidate: Candidate) -> str:
    return hashlib.sha256(canonical_bytes({
        "family": candidate.family,
        "source_generator": candidate.source_generator,
        "parameters": candidate.parameters,
        "variable_specs": candidate.variable_specs,
    })).hexdigest()


def admitted_rows(prior_truth_identities: set[tuple[int, str]]) -> tuple[list[dict], dict]:
    rows = []
    semantic_seen: set[tuple[int, str]] = set()
    rejected = {"prior_truth_overlap": 0, "within_pool_duplicate": 0,
                "support_or_admission": 0, "oracle_mismatch": 0}
    for candidate in candidates():
        n_vars = len(candidate.variable_specs)
        try:
            if not 3 <= n_vars <= 10:
                raise ValueError("support outside 3..10")
            admit(candidate.expression, n_vars, 1)
            expression_bits = reference_bits(candidate.expression, n_vars)
            independent_bits = scalar_bits(candidate)
            if (expression_bits != independent_bits
                    or semantic_variables(expression_bits, n_vars) != tuple(range(n_vars))):
                rejected["oracle_mismatch"] += 1
                continue
        except (TypeError, ValueError, RecursionError):
            rejected["support_or_admission"] += 1
            continue
        truth_digest = truth_sha256(expression_bits, n_vars)
        semantic = (n_vars, truth_digest)
        if semantic in prior_truth_identities:
            rejected["prior_truth_overlap"] += 1
            continue
        if semantic in semantic_seen:
            rejected["within_pool_duplicate"] += 1
            continue
        semantic_seen.add(semantic)
        identity = candidate_identity(candidate)
        document = expr_to_json_dag(candidate.expression)
        rows.append({
            "schema": DATASET_SCHEMA,
            "case_id": f"c23-{candidate.family}-{identity[:16]}",
            "split": "fresh_confirmation",
            "cluster_id": candidate.family,
            "source_kind": "yosys_bench_unused_generator_semantics",
            "source_repository": SOURCE_URL,
            "source_commit": SOURCE_COMMIT,
            "source_generator": candidate.source_generator,
            "family": candidate.family,
            "parameters": candidate.parameters,
            "variable_specs": [[port, bit] for port, bit in candidate.variable_specs],
            "n_vars": n_vars,
            "truth_bits_hex": format(expression_bits, "x"),
            "truth_sha256": truth_digest,
            "expression_v2": document,
            "expression_v2_sha256": hashlib.sha256(canonical_bytes(document)).hexdigest(),
            "selection_sha256": identity,
            "prior_truth_overlap": False,
            "training_use": False,
            "policy_selection_use": False,
            "fresh_confirmation": True,
        })
    return rows, rejected


def select_rows(rows: list[dict], target: int) -> list[dict]:
    if type(target) is not int or not 32 <= target <= 80:
        raise ValueError("invalid C23 target")
    by_family: dict[str, list[dict]] = {}
    for row in rows:
        by_family.setdefault(row["family"], []).append(row)
    for values in by_family.values():
        values.sort(key=lambda row: row["selection_sha256"])
    families = sorted(by_family)
    selected = []
    offset = 0
    while len(selected) < target and any(offset < len(by_family[name]) for name in families):
        for family in families:
            if len(selected) == target:
                break
            if offset < len(by_family[family]):
                selected.append(by_family[family][offset])
        offset += 1
    if len(selected) != target:
        raise ValueError(f"only {len(selected)}/{target} fresh C23 cases available")
    return sorted(selected, key=lambda row: row["case_id"])


def dataset_document(rows: list[dict], rejected: dict, inventory_path: str,
                     inventory_sha256: str, target: int) -> dict:
    selected = select_rows(rows, target)
    return {
        "schema": DATASET_SCHEMA,
        "status": "frozen",
        "cases": selected,
        "counts": {
            "cases": len(selected),
            "families": len({row["family"] for row in selected}),
            "by_family": {family: sum(row["family"] == family for row in selected)
                          for family in sorted({row["family"] for row in selected})},
            "by_n_vars": {str(n_vars): sum(row["n_vars"] == n_vars for row in selected)
                          for n_vars in range(3, 11)},
            "candidate_pool_after_exclusions": len(rows),
            "rejected": rejected,
        },
        "provenance": {
            "source_family": "YosysHQ/yosys-bench previously unused generator families",
            "source_repository": SOURCE_URL,
            "source_commit": SOURCE_COMMIT,
            "source_inventory": inventory_path,
            "source_inventory_sha256": inventory_sha256,
            "selection_contract": "exclude C16/C18/C19/C7 truth identities; stable family round robin/v1",
            "repository_seen_in_prior_work": True,
            "generator_families_seen_in_c7": False,
            "timing_based_selection": False,
            "training_use": False,
            "policy_refit_allowed": False,
            "fresh_confirmation": True,
            "production_promotion": False,
        },
    }


def validate_dataset(document: dict) -> None:
    if (type(document) is not dict or document.get("schema") != DATASET_SCHEMA
            or document.get("status") != "frozen"):
        raise ValueError("invalid C23 dataset envelope")
    cases = document.get("cases")
    if type(cases) is not list or len(cases) != document.get("counts", {}).get("cases"):
        raise ValueError("invalid C23 case count")
    identities: set[str] = set()
    semantics: set[tuple[int, str]] = set()
    for row in cases:
        if (type(row) is not dict or row.get("schema") != DATASET_SCHEMA
                or row.get("split") != "fresh_confirmation"
                or row.get("training_use") is not False
                or row.get("policy_selection_use") is not False
                or row.get("fresh_confirmation") is not True
                or row.get("prior_truth_overlap") is not False
                or row.get("source_commit") != SOURCE_COMMIT
                or type(row.get("n_vars")) is not int or not 3 <= row["n_vars"] <= 10):
            raise ValueError("invalid C23 case")
        if row["case_id"] in identities:
            raise ValueError("duplicate C23 identity")
        identities.add(row["case_id"])
        semantic = (row["n_vars"], row["truth_sha256"])
        if semantic in semantics:
            raise ValueError("duplicate C23 truth identity")
        semantics.add(semantic)
        from cm_expr_serde import expr_from_json
        expression = expr_from_json(row["expression_v2"])
        bits = reference_bits(expression, row["n_vars"])
        if (bits != int(row["truth_bits_hex"], 16)
                or truth_sha256(bits, row["n_vars"]) != row["truth_sha256"]
                or hashlib.sha256(canonical_bytes(row["expression_v2"])).hexdigest()
                != row["expression_v2_sha256"]):
            raise ValueError("changed C23 expression or truth")
    provenance = document.get("provenance", {})
    if (provenance.get("timing_based_selection") is not False
            or provenance.get("policy_refit_allowed") is not False
            or provenance.get("fresh_confirmation") is not True
            or provenance.get("production_promotion") is not False):
        raise ValueError("invalid C23 evidence policy")
