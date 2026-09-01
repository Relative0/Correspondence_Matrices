"""C27 confirmation cases from pinned, previously unused Yosys-bench generators."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
from typing import Any, Callable

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Expr, Not, Or, Var, Xor

from cmbench.comparative.contracts import canonical_bytes
from cmbench.recognition.gf2_decomposition import truth_sha256
from cmbench.recognition.natural_decomposition import semantic_variables
from cmbench.recognition.portfolio import admit, reference_bits

SOURCE_COMMIT = "52ff6fa991f2ab509618d8aaad02f307aac78848"
SOURCE_URL = "https://github.com/YosysHQ/yosys-bench.git"
SOURCE_GENERATORS = (
    "verilog/benchmarks_small/dspmac/generate.py",
    "verilog/benchmarks_small/macc/generate.py",
    "verilog/benchmarks_small/priodecode/generate.py",
    "verilog/benchmarks_small/ram/generate.py",
)
SOURCE_FILES = (
    "verilog/benchmarks_small/dspmac/dspmac.template",
    "verilog/benchmarks_small/dspmac/generate.py",
    "verilog/benchmarks_small/macc/common.py",
    "verilog/benchmarks_small/macc/generate.py",
    "verilog/benchmarks_small/priodecode/generate.py",
    "verilog/benchmarks_small/ram/dualport_syncram.template",
    "verilog/benchmarks_small/ram/generate.py",
    "verilog/benchmarks_small/ram/syncram.template",
    "verilog/benchmarks_small/ram/syncram_tw.template",
)
DATASET_SCHEMA = "crse-c27-yosys-unused-generator-gf2-dataset/v1"
Signal = Expr | bool
Spec = tuple[str, int]


@dataclass(frozen=True)
class Candidate:
    family: str
    source_generator: str
    parameters: dict[str, Any]
    expression: Expr
    variable_specs: tuple[Spec, ...]
    scalar: Callable[[dict[Spec, int]], int]


def _not(value: Signal) -> Signal:
    return not value if type(value) is bool else Not(value)


def _and(left: Signal, right: Signal) -> Signal:
    if type(left) is bool:
        return right if left else False
    if type(right) is bool:
        return left if right else False
    return And(left, right)


def _or(left: Signal, right: Signal) -> Signal:
    if type(left) is bool:
        return True if left else right
    if type(right) is bool:
        return True if right else left
    return Or(left, right)


def _xor(left: Signal, right: Signal) -> Signal:
    if type(left) is bool:
        return _not(right) if left else right
    if type(right) is bool:
        return _not(left) if right else left
    return Xor(left, right)


def _mux(select: Signal, when_true: Signal, when_false: Signal) -> Signal:
    if type(select) is bool:
        return when_true if select else when_false
    if when_true == when_false:
        return when_true
    return _or(_and(select, when_true), _and(_not(select), when_false))


def _add(left: list[Signal], right: list[Signal]) -> list[Signal]:
    width = max(len(left), len(right))
    result: list[Signal] = []
    carry: Signal = False
    for bit in range(width):
        first = left[bit] if bit < len(left) else False
        second = right[bit] if bit < len(right) else False
        result.append(_xor(_xor(first, second), carry))
        carry = _or(_and(first, second), _or(_and(first, carry), _and(second, carry)))
    result.append(carry)
    return result


def _product(a: list[Signal], b: list[Signal]) -> list[Signal]:
    result: list[Signal] = []
    for second, second_value in enumerate(b):
        partial = [False] * second + [_and(first, second_value) for first in a]
        result = _add(result, partial)
    return result


def _select(cells: list[Signal], address: list[Signal]) -> Signal:
    values = list(cells)
    for select in address:
        values = [_mux(select, values[index + 1], values[index])
                  for index in range(0, len(values), 2)]
    if len(values) != 1:
        raise ValueError("invalid C27 memory selection")
    return values[0]


def _fixed_bit(label: str, seed: int) -> bool:
    return bool(hashlib.sha256(f"{label}:{seed}".encode()).digest()[0] & 1)


def _restricted_candidate(
    *, family: str, source_generator: str, parameters: dict[str, Any],
    relevant: tuple[Spec, ...], selected: tuple[Spec, ...], fixed: dict[Spec, bool],
    expression_builder: Callable[[dict[Spec, Signal]], Signal],
    scalar_builder: Callable[[dict[Spec, int]], int],
) -> Candidate | None:
    variables = {spec: Var(index) for index, spec in enumerate(selected)}
    environment: dict[Spec, Signal] = {
        spec: variables[spec] if spec in variables else fixed[spec] for spec in relevant}
    expression = expression_builder(environment)
    if type(expression) is bool:
        return None

    def scalar(values: dict[Spec, int]) -> int:
        merged = {spec: values[spec] if spec in values else int(fixed[spec]) for spec in relevant}
        return scalar_builder(merged)

    fixed_document = {f"{port}[{bit}]": int(value) for (port, bit), value in fixed.items()
                      if (port, bit) not in selected}
    return Candidate(
        family=family,
        source_generator=source_generator,
        parameters={**parameters, "fixed_inputs": fixed_document},
        expression=expression,
        variable_specs=selected,
        scalar=scalar,
    )


def _combination_sample(relevant: tuple[Spec, ...], n_vars: int, family: str,
                        limit: int = 64) -> list[tuple[Spec, ...]]:
    rows = list(itertools.combinations(relevant, n_vars))
    rows.sort(key=lambda row: hashlib.sha256(
        canonical_bytes({"family": family, "selected": row})).hexdigest())
    return rows[:limit]


def _priority_candidates() -> list[Candidate]:
    rows = []
    for n_vars in range(3, 7):
        specs = tuple(("din", bit) for bit in range(n_vars))
        variables = {spec: Var(index) for index, spec in enumerate(specs)}
        expression: Signal = variables[specs[-1]]
        for spec in specs[:-1]:
            expression = _and(expression, _not(variables[spec]))
        assert type(expression) is not bool
        rows.append(Candidate(
            "priority_lowest_one",
            "verilog/benchmarks_small/priodecode/generate.py",
            {"generated_width": max(n_vars, 3), "output_bit": n_vars - 1},
            expression,
            specs,
            lambda values, n=n_vars: int(
                bool(values[("din", n - 1)])
                and not any(values[("din", bit)] for bit in range(n - 1))),
        ))
    return rows


def _dspmac_candidates() -> list[Candidate]:
    rows: list[Candidate] = []
    source = "verilog/benchmarks_small/dspmac/generate.py"
    for output_bit in range(3):
        relevant = tuple([("rst_n", 0), ("opcode", 0), ("opcode", 1)]
                         + [(port, bit) for port in ("A", "B", "P")
                            for bit in range(output_bit + 1)])

        def expression(env, bit=output_bit):
            a = [env[("A", index)] for index in range(bit + 1)]
            b = [env[("B", index)] for index in range(bit + 1)]
            p = [env[("P", index)] for index in range(bit + 1)]
            product = _product(a, b)
            multiply = product[bit]
            mac = _add(p, product)[bit]
            op0, op1 = env[("opcode", 0)], env[("opcode", 1)]
            selected = _mux(op1, _mux(op0, p[bit], mac), _mux(op0, multiply, False))
            return _mux(env[("rst_n", 0)], selected, False)

        def scalar(values, bit=output_bit):
            a = sum(values[("A", index)] << index for index in range(bit + 1))
            b = sum(values[("B", index)] << index for index in range(bit + 1))
            p = sum(values[("P", index)] << index for index in range(bit + 1))
            opcode = values[("opcode", 0)] | values[("opcode", 1)] << 1
            if not values[("rst_n", 0)] or opcode == 0:
                value = 0
            elif opcode == 1:
                value = a * b
            elif opcode == 2:
                value = p + a * b
            else:
                value = p
            return (value >> bit) & 1

        for n_vars in range(3, min(6, len(relevant)) + 1):
            for selected in _combination_sample(relevant, n_vars, f"dspmac-{output_bit}"):
                for seed in range(3):
                    opcode = (seed % 3) + 1
                    fixed = {spec: _fixed_bit(f"dspmac:{output_bit}:{spec}", seed)
                             for spec in relevant}
                    fixed[("rst_n", 0)] = True
                    fixed[("opcode", 0)] = bool(opcode & 1)
                    fixed[("opcode", 1)] = bool(opcode & 2)
                    candidate = _restricted_candidate(
                        family="dspmac_next_accumulator", source_generator=source,
                        parameters={"op_bits": 8, "accu_bits": 24,
                                    "output_bit": output_bit, "restriction_seed": seed},
                        relevant=relevant, selected=selected, fixed=fixed,
                        expression_builder=expression, scalar_builder=scalar)
                    if candidate is not None:
                        rows.append(candidate)
    return rows


def _macc_candidates() -> list[Candidate]:
    rows: list[Candidate] = []
    source = "verilog/benchmarks_small/macc/generate.py"
    for output_bit in range(3):
        relevant = tuple([("CEP", 0)] + [(port, bit) for port in ("A", "B", "P")
                                         for bit in range(output_bit + 1)])

        def expression(env, bit=output_bit):
            a = [env[("A", index)] for index in range(bit + 1)]
            b = [env[("B", index)] for index in range(bit + 1)]
            p = [env[("P", index)] for index in range(bit + 1)]
            accumulated = _add(p, _product(a, b))[bit]
            return _mux(env[("CEP", 0)], accumulated, p[bit])

        def scalar(values, bit=output_bit):
            a = sum(values[("A", index)] << index for index in range(bit + 1))
            b = sum(values[("B", index)] << index for index in range(bit + 1))
            p = sum(values[("P", index)] << index for index in range(bit + 1))
            value = p + a * b if values[("CEP", 0)] else p
            return (value >> bit) & 1

        for n_vars in range(3, min(6, len(relevant)) + 1):
            for selected in _combination_sample(relevant, n_vars, f"macc-{output_bit}"):
                for seed in range(3):
                    fixed = {spec: _fixed_bit(f"macc:{output_bit}:{spec}", seed)
                             for spec in relevant}
                    fixed[("CEP", 0)] = True
                    candidate = _restricted_candidate(
                        family="macc_enabled_next_accumulator", source_generator=source,
                        parameters={"a_width": 16, "b_width": 4,
                                    "output_bit": output_bit, "restriction_seed": seed},
                        relevant=relevant, selected=selected, fixed=fixed,
                        expression_builder=expression, scalar_builder=scalar)
                    if candidate is not None:
                        rows.append(candidate)
    return rows


def _ram_candidates() -> list[Candidate]:
    rows: list[Candidate] = []
    source = "verilog/benchmarks_small/ram/generate.py"
    for mode in ("transparent", "synchronous", "dual_port"):
        for address_width in (0, 1, 2):
            cells = 1 << address_width
            controls = ([('cs', 0), ('we', 0), ('din', 0), ('old', 0)]
                        if mode == "transparent" else
                        [('cs', 0), ('we', 0), ('old', 0)]
                        if mode == "synchronous" else [('cs', 0), ('old', 0)])
            relevant = tuple(controls + [("addr", bit) for bit in range(address_width)]
                             + [("mem", cell) for cell in range(cells)])

            def expression(env, selected_mode=mode, width=address_width):
                memory = _select([env[("mem", cell)] for cell in range(1 << width)],
                                 [env[("addr", bit)] for bit in range(width)])
                old = env[("old", 0)]
                if selected_mode == "transparent":
                    active = _mux(env[("we", 0)], env[("din", 0)], memory)
                    return _mux(env[("cs", 0)], active, old)
                if selected_mode == "synchronous":
                    read = _and(env[("cs", 0)], _not(env[("we", 0)]))
                    return _mux(read, memory, old)
                return _mux(env[("cs", 0)], memory, old)

            def scalar(values, selected_mode=mode, width=address_width):
                address = sum(values[("addr", bit)] << bit for bit in range(width))
                memory = values[("mem", address)]
                old = values[("old", 0)]
                if selected_mode == "transparent":
                    return (values[("din", 0)] if values[("we", 0)] else memory
                            ) if values[("cs", 0)] else old
                if selected_mode == "synchronous":
                    return memory if values[("cs", 0)] and not values[("we", 0)] else old
                return memory if values[("cs", 0)] else old

            for n_vars in range(3, min(6, len(relevant)) + 1):
                for selected in _combination_sample(relevant, n_vars, f"ram-{mode}-{address_width}"):
                    for seed in range(3):
                        fixed = {spec: _fixed_bit(f"ram:{mode}:{address_width}:{spec}", seed)
                                 for spec in relevant}
                        fixed[("cs", 0)] = True
                        if ("we", 0) in fixed:
                            fixed[("we", 0)] = bool(seed & 1)
                        candidate = _restricted_candidate(
                            family=f"ram_{mode}_next_output", source_generator=source,
                            parameters={"address_width": max(4, address_width), "io_width": 4,
                                        "mode": mode, "restriction_seed": seed},
                            relevant=relevant, selected=selected, fixed=fixed,
                            expression_builder=expression, scalar_builder=scalar)
                        if candidate is not None:
                            rows.append(candidate)
    return rows


def candidates() -> list[Candidate]:
    return _priority_candidates() + _dspmac_candidates() + _macc_candidates() + _ram_candidates()


def scalar_bits(candidate: Candidate) -> int:
    n_vars = len(candidate.variable_specs)
    bits = 0
    for assignment in range(1 << n_vars):
        values = {spec: (assignment >> (n_vars - 1 - index)) & 1
                  for index, spec in enumerate(candidate.variable_specs)}
        value = candidate.scalar(values)
        if type(value) is not int or value not in (0, 1):
            raise ValueError("non-Boolean C27 scalar oracle")
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
            if not 3 <= n_vars <= 6:
                raise ValueError("support outside C27 task")
            admit(candidate.expression, n_vars, 1)
            expression_bits = reference_bits(candidate.expression, n_vars)
            independent_bits = scalar_bits(candidate)
            if expression_bits != independent_bits:
                rejected["oracle_mismatch"] += 1
                continue
            if semantic_variables(expression_bits, n_vars) != tuple(range(n_vars)):
                rejected["support_or_admission"] += 1
                continue
        except (TypeError, ValueError, RecursionError):
            rejected["support_or_admission"] += 1
            continue
        digest = truth_sha256(expression_bits, n_vars)
        semantic = (n_vars, digest)
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
            "case_id": f"c27-{candidate.family}-{identity[:16]}",
            "split": "fresh_confirmation",
            "cluster_id": candidate.family,
            "source_kind": "yosys_bench_unused_generator_restricted_semantics",
            "source_repository": SOURCE_URL,
            "source_commit": SOURCE_COMMIT,
            "source_generator": candidate.source_generator,
            "family": candidate.family,
            "parameters": candidate.parameters,
            "variable_specs": [[port, bit] for port, bit in candidate.variable_specs],
            "n_vars": n_vars,
            "truth_bits_hex": format(expression_bits, "x"),
            "truth_sha256": digest,
            "expression_v2": document,
            "expression_v2_sha256": hashlib.sha256(canonical_bytes(document)).hexdigest(),
            "selection_sha256": identity,
            "prior_truth_overlap": False,
            "training_use": False,
            "policy_selection_use": False,
            "fresh_confirmation": True,
        })
    return rows, rejected


def select_rows(rows: list[dict], per_width: int = 12) -> list[dict]:
    if per_width != 12:
        raise ValueError("C27 selection contract requires twelve cases per width")
    selected = []
    for n_vars in range(3, 7):
        by_family: dict[str, list[dict]] = {}
        for row in rows:
            if row["n_vars"] == n_vars:
                by_family.setdefault(row["family"], []).append(row)
        for values in by_family.values():
            values.sort(key=lambda row: row["selection_sha256"])
        families = sorted(by_family)
        width_rows, offset = [], 0
        while len(width_rows) < per_width and any(
                offset < len(by_family[name]) for name in families):
            for family in families:
                if len(width_rows) == per_width:
                    break
                if offset < len(by_family[family]):
                    width_rows.append(by_family[family][offset])
            offset += 1
        if len(width_rows) != per_width:
            raise ValueError(f"only {len(width_rows)}/{per_width} C27 cases for n={n_vars}")
        selected.extend(width_rows)
    return sorted(selected, key=lambda row: row["case_id"])


def dataset_document(rows: list[dict], rejected: dict, *, inventory_path: str,
                     inventory_sha256: str, policy_path: str,
                     policy_file_sha256: str, policy_sha256: str) -> dict:
    selected = select_rows(rows)
    return {
        "schema": DATASET_SCHEMA,
        "status": "frozen",
        "cases": selected,
        "counts": {
            "cases": len(selected),
            "families": len({row["family"] for row in selected}),
            "by_family": {family: sum(row["family"] == family for row in selected)
                          for family in sorted({row["family"] for row in selected})},
            "by_n_vars": {str(n): sum(row["n_vars"] == n for row in selected)
                          for n in range(3, 7)},
            "candidate_pool_after_exclusions": len(rows),
            "rejected": rejected,
        },
        "provenance": {
            "source_family": "YosysHQ/yosys-bench previously unused C27 generator groups",
            "source_repository": SOURCE_URL,
            "source_commit": SOURCE_COMMIT,
            "source_inventory": inventory_path,
            "source_inventory_sha256": inventory_sha256,
            "selection_contract": "exclude all prior truths; 12 per width stable family round robin/v1",
            "support_policy_path": policy_path,
            "support_policy_file_sha256": policy_file_sha256,
            "support_policy_sha256": policy_sha256,
            "policy_frozen_before_dataset": True,
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
        raise ValueError("invalid C27 dataset envelope")
    cases = document.get("cases")
    if type(cases) is not list or len(cases) != 48:
        raise ValueError("invalid C27 case count")
    identities, semantics = set(), set()
    for row in cases:
        if (
            type(row) is not dict or row.get("schema") != DATASET_SCHEMA
            or row.get("split") != "fresh_confirmation"
            or row.get("training_use") is not False
            or row.get("policy_selection_use") is not False
            or row.get("fresh_confirmation") is not True
            or row.get("prior_truth_overlap") is not False
            or row.get("source_commit") != SOURCE_COMMIT
            or row.get("source_generator") not in SOURCE_GENERATORS
            or type(row.get("n_vars")) is not int or not 3 <= row["n_vars"] <= 6
        ):
            raise ValueError("invalid C27 case")
        semantic = (row["n_vars"], row["truth_sha256"])
        if row["case_id"] in identities or semantic in semantics:
            raise ValueError("duplicate C27 identity")
        identities.add(row["case_id"])
        semantics.add(semantic)
        from cm_expr_serde import expr_from_json
        expression = expr_from_json(row["expression_v2"])
        bits = reference_bits(expression, row["n_vars"])
        if (
            bits != int(row["truth_bits_hex"], 16)
            or truth_sha256(bits, row["n_vars"]) != row["truth_sha256"]
            or hashlib.sha256(canonical_bytes(row["expression_v2"])).hexdigest()
            != row["expression_v2_sha256"]
        ):
            raise ValueError("changed C27 expression or truth")
    if document["counts"].get("by_n_vars") != {str(n): 12 for n in range(3, 7)}:
        raise ValueError("C27 support balance changed")
    provenance = document.get("provenance", {})
    if (
        provenance.get("policy_frozen_before_dataset") is not True
        or provenance.get("timing_based_selection") is not False
        or provenance.get("policy_refit_allowed") is not False
        or provenance.get("fresh_confirmation") is not True
        or provenance.get("production_promotion") is not False
    ):
        raise ValueError("invalid C27 evidence policy")
