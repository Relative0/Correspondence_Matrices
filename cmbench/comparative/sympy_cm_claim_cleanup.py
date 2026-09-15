"""Bounded, task-matched SymPy/CM claim-cleanup benchmark support.

The historical benchmark timed SymPy expression simplification against CM
construction.  This module deliberately keeps those unlike tasks out of the
same scoreboard.  It supplies exact, canonical artifacts for Y02--Y04 and a
separate expression-quality contract for Y05.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Mapping, Sequence
from typing import Any, Callable


SCHEMA = "cm-sympy-claim-cleanup/v1"
CONTRACT_SCHEMA = "cm-sympy-task-contract/v1"
RESULT_SCHEMA = "cm-sympy-task-result/v1"
ASSIGNMENT_GENERATOR = "affine_xorshift_rows/v1"
PACKING = "assignment_msb_first_values_little_bit_packed/v1"
MAX_VARIABLES = 8
MAX_BATCH_ROWS = 4096


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def parse_expression(spec: Mapping[str, Any]) -> Any:
    """Build the repository Boolean AST from a bounded JSON expression."""
    from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor

    if not isinstance(spec, Mapping) or set(spec) - {"op", "index", "args"}:
        raise ValueError("invalid expression object")
    op = spec.get("op")
    if op == "var":
        if set(spec) != {"op", "index"} or type(spec["index"]) is not int:
            raise ValueError("invalid variable expression")
        return Var(spec["index"])
    args = spec.get("args")
    if not isinstance(args, list):
        raise ValueError("expression arguments must be a list")
    if op == "not":
        if set(spec) != {"op", "args"} or len(args) != 1:
            raise ValueError("invalid not expression")
        return Not(parse_expression(args[0]))
    constructors = {
        "and": And,
        "or": Or,
        "xor": Xor,
        "imp": Imp,
        "eqv": Eqv,
    }
    if op not in constructors or set(spec) != {"op", "args"} or len(args) != 2:
        raise ValueError("invalid binary expression")
    return constructors[op](parse_expression(args[0]), parse_expression(args[1]))


def validate_expression(spec: Mapping[str, Any], n_vars: int) -> None:
    expr = parse_expression(spec)
    from cm_ir import expr_vars

    names = expr_vars(expr)
    allowed = {f"x{i}" for i in range(n_vars)}
    if not set(names).issubset(allowed):
        raise ValueError("expression references a variable outside its universe")


def scalar_truth_values(expr: Any, n_vars: int) -> list[int]:
    """Independent exhaustive evaluator in assignment-MSB-first row order."""
    from cmbench.expr.eval import eval_expr_assignment

    names = tuple(f"x{i}" for i in range(n_vars))
    output: list[int] = []
    for row in range(1 << n_vars):
        assignment = {
            name: (row >> (n_vars - 1 - index)) & 1
            for index, name in enumerate(names)
        }
        output.append(int(eval_expr_assignment(expr, assignment)))
    return output


def pack_values(values: Sequence[int]) -> bytes:
    """Pack row zero into bit zero; reject anything other than Boolean bits."""
    result = bytearray((len(values) + 7) // 8)
    for index, value in enumerate(values):
        if type(value) is not int or value not in (0, 1):
            raise ValueError("non-Boolean output value")
        result[index // 8] |= value << (index % 8)
    return bytes(result)


def packed_digest(values: Sequence[int]) -> str:
    return sha256_bytes(pack_values(values))


def assignment_rows(spec: Mapping[str, Any], n_vars: int) -> bytes:
    """Generate exact row-major uint8 assignments without NumPy RNG state."""
    required = {"algorithm", "rows", "multiplier", "offset", "shift"}
    if not isinstance(spec, Mapping) or set(spec) != required:
        raise ValueError("invalid assignment generator")
    if spec["algorithm"] != ASSIGNMENT_GENERATOR:
        raise ValueError("unknown assignment generator")
    rows = spec["rows"]
    multiplier = spec["multiplier"]
    offset = spec["offset"]
    shift = spec["shift"]
    if (
        type(rows) is not int
        or not 1 <= rows <= MAX_BATCH_ROWS
        or type(multiplier) is not int
        or multiplier <= 0
        or multiplier % 2 == 0
        or type(offset) is not int
        or offset < 0
        or type(shift) is not int
        or not 1 <= shift <= 31
    ):
        raise ValueError("assignment generator is outside bounds")
    mask = (1 << n_vars) - 1
    output = bytearray(rows * n_vars)
    for row in range(rows):
        word = ((row * multiplier + offset) ^ (row >> shift)) & mask
        for index in range(n_vars):
            output[row * n_vars + index] = (word >> (n_vars - 1 - index)) & 1
    return bytes(output)


def assignment_output(expr: Any, n_vars: int, raw_rows: bytes) -> list[int]:
    from cmbench.expr.eval import eval_expr_assignment

    if len(raw_rows) % n_vars:
        raise ValueError("assignment byte count does not match width")
    names = tuple(f"x{i}" for i in range(n_vars))
    values: list[int] = []
    for start in range(0, len(raw_rows), n_vars):
        assignment = {
            name: raw_rows[start + index] for index, name in enumerate(names)
        }
        values.append(int(eval_expr_assignment(expr, assignment)))
    return values


def make_contract(
    *,
    family: str,
    task: str,
    case_id: str,
    n_vars: int,
    artifact_kind: str,
    expected_sha256: str,
    batch_rows: int | None = None,
    form: str | None = None,
) -> dict[str, Any]:
    contract = {
        "schema": CONTRACT_SCHEMA,
        "contract_id": f"{family.lower()}-{task}-{case_id}" + (f"-{form}" if form else ""),
        "family": family,
        "task": task,
        "case_id": case_id,
        "variables": [f"x{i}" for i in range(n_vars)],
        "artifact": {
            "kind": artifact_kind,
            "packing": PACKING if artifact_kind.startswith("packed_") else None,
            "semantic_sha256": expected_sha256,
            "form": form,
        },
        "batch_rows": batch_rows,
        "validation": {
            "oracle": "independent_scalar_exhaustive/v1",
            "included_in_timing": False,
        },
    }
    validate_contract(contract)
    return contract


def validate_contract(contract: Mapping[str, Any]) -> None:
    required = {
        "schema", "contract_id", "family", "task", "case_id", "variables",
        "artifact", "batch_rows", "validation",
    }
    if not isinstance(contract, Mapping) or set(contract) != required:
        raise ValueError("contract fields")
    if contract["schema"] != CONTRACT_SCHEMA or contract["family"] not in {"Y02", "Y03", "Y04", "Y05"}:
        raise ValueError("contract schema/family")
    variables = contract["variables"]
    if (
        not isinstance(variables, list)
        or not 1 <= len(variables) <= MAX_VARIABLES
        or variables != [f"x{i}" for i in range(len(variables))]
    ):
        raise ValueError("contract variables")
    artifact = contract["artifact"]
    if not isinstance(artifact, Mapping) or set(artifact) != {"kind", "packing", "semantic_sha256", "form"}:
        raise ValueError("contract artifact")
    if not isinstance(artifact["semantic_sha256"], str) or len(artifact["semantic_sha256"]) != 64:
        raise ValueError("contract semantic digest")
    if contract["validation"] != {"oracle": "independent_scalar_exhaustive/v1", "included_in_timing": False}:
        raise ValueError("contract validation")


def _stage(function: Callable[[], Any]) -> tuple[Any, int]:
    started = time.perf_counter_ns()
    value = function()
    return value, time.perf_counter_ns() - started


def _sympy_expression(expr: Any, n_vars: int) -> Any:
    from expr_simplify import _to_sympy

    return _to_sympy(expr, n_vars)


def _normalize_vector(value: Any, rows: int) -> list[int]:
    import numpy as np

    array = np.asarray(value)
    if array.ndim == 0:
        array = np.full(rows, bool(array), dtype=np.bool_)
    else:
        array = np.broadcast_to(array, (rows,))
    return [int(item) for item in np.asarray(array, dtype=np.uint8).reshape(-1)]


def _cm_batch_values(node: Any, raw_rows: bytes, n_vars: int) -> list[int]:
    import numpy as np

    rows = len(raw_rows) // n_vars
    assignments = np.frombuffer(raw_rows, dtype=np.uint8).reshape(rows, n_vars).astype(bool, copy=False)
    memo: dict[int, Any] = {}

    def evaluate(cur: Any) -> Any:
        cached = memo.get(id(cur))
        if cached is not None:
            return cached
        if cur.kind == "const":
            value = np.full(rows, bool(cur.const_value), dtype=np.bool_)
        elif cur.kind == "var":
            value = assignments[:, int(cur.var_name[1:])]
        elif cur.kind == "not":
            value = np.logical_not(evaluate(cur.args[0]))
        else:
            args = [evaluate(arg) for arg in cur.args]
            if cur.op == "AND":
                value = np.logical_and.reduce(args)
            elif cur.op == "OR":
                value = np.logical_or.reduce(args)
            elif cur.op == "XOR":
                value = np.logical_xor.reduce(args)
            elif cur.op == "IMP":
                value = np.logical_or(np.logical_not(args[0]), args[1])
            elif cur.op == "EQV":
                value = np.logical_not(np.logical_xor(args[0], args[1]))
            else:
                raise ValueError(f"unsupported CM operation {cur.op!r}")
        memo[id(cur)] = value
        return value

    return [int(item) for item in np.asarray(evaluate(node), dtype=np.uint8).reshape(-1)]


def _cm_truth(expr: Any, n_vars: int) -> tuple[list[int], dict[str, int]]:
    from bitset_backend import eval_cm_node_flat
    from cm_ir import compile_expr_to_cm_ir

    node, prepare_ns = _stage(
        lambda: compile_expr_to_cm_ir(
            expr,
            reuse_cache=False,
            persistent_cache=False,
            share_aware_flatten=True,
        )
    )
    bits, evaluate_ns = _stage(
        lambda: int(eval_cm_node_flat(node, tuple(f"x{i}" for i in range(n_vars))))
    )
    values, deliver_ns = _stage(
        lambda: [(bits >> row) & 1 for row in range(1 << n_vars)]
    )
    return values, {"prepare_ns": prepare_ns, "evaluate_ns": evaluate_ns, "deliver_ns": deliver_ns}


def _sympy_truth(expr: Any, n_vars: int) -> tuple[list[int], dict[str, int]]:
    import sympy as sp
    from sympy.logic.boolalg import truth_table

    sp_expr, convert_ns = _stage(lambda: _sympy_expression(expr, n_vars))
    symbols = [sp.Symbol(f"x{i}") for i in range(n_vars)]
    generator, create_generator_ns = _stage(
        lambda: truth_table(sp_expr, symbols, input=False)
    )
    values, consume_generator_ns = _stage(lambda: [int(bool(value)) for value in generator])
    return values, {
        "convert_ns": convert_ns,
        "create_generator_ns": create_generator_ns,
        "consume_generator_ns": consume_generator_ns,
    }


def _sympy_batch(expr: Any, n_vars: int, raw_rows: bytes, *, cse: bool) -> tuple[list[int], dict[str, int]]:
    import numpy as np
    import sympy as sp

    rows = len(raw_rows) // n_vars
    sp_expr, convert_ns = _stage(lambda: _sympy_expression(expr, n_vars))
    symbols = [sp.Symbol(f"x{i}") for i in range(n_vars)]
    function, compile_ns = _stage(
        lambda: sp.lambdify(symbols, sp_expr, modules="numpy", cse=cse)
    )
    assignments = np.frombuffer(raw_rows, dtype=np.uint8).reshape(rows, n_vars).astype(bool, copy=False)
    native, evaluate_ns = _stage(
        lambda: function(*[assignments[:, index] for index in range(n_vars)])
    )
    values, deliver_ns = _stage(lambda: _normalize_vector(native, rows))
    return values, {
        "convert_ns": convert_ns,
        "compile_callable_ns": compile_ns,
        "evaluate_ns": evaluate_ns,
        "deliver_ns": deliver_ns,
    }


def _cm_batch(expr: Any, n_vars: int, raw_rows: bytes) -> tuple[list[int], dict[str, int]]:
    from cm_ir import compile_expr_to_cm_ir

    node, prepare_ns = _stage(
        lambda: compile_expr_to_cm_ir(
            expr,
            reuse_cache=False,
            persistent_cache=False,
            share_aware_flatten=True,
        )
    )
    values, evaluate_ns = _stage(lambda: _cm_batch_values(node, raw_rows, n_vars))
    delivered, deliver_ns = _stage(lambda: list(values))
    return delivered, {"prepare_ns": prepare_ns, "evaluate_ns": evaluate_ns, "deliver_ns": deliver_ns}


def _sympy_sat(expr: Any, n_vars: int) -> tuple[bool, list[int] | None, dict[str, int]]:
    import sympy as sp
    from sympy.logic.inference import satisfiable

    sp_expr, convert_ns = _stage(lambda: _sympy_expression(expr, n_vars))
    model, solve_ns = _stage(lambda: satisfiable(sp_expr, algorithm="dpll2"))
    if model is False:
        return False, None, {"convert_ns": convert_ns, "solve_ns": solve_ns}
    witness = [int(bool(model.get(sp.Symbol(f"x{i}"), False))) for i in range(n_vars)]
    return True, witness, {"convert_ns": convert_ns, "solve_ns": solve_ns}


def _cm_sat(expr: Any, n_vars: int) -> tuple[bool, list[int] | None, dict[str, int]]:
    values, timings = _cm_truth(expr, n_vars)
    try:
        row = values.index(1)
    except ValueError:
        return False, None, timings
    witness = [(row >> (n_vars - 1 - index)) & 1 for index in range(n_vars)]
    return True, witness, timings


def _pysat_sat(expr: Any, n_vars: int) -> tuple[bool, list[int] | None, dict[str, int]]:
    from cm_exprlib import tseitin_cnf
    from pysat.solvers import Solver

    encoded, encode_ns = _stage(lambda: tseitin_cnf(expr, n_vars))
    output, clauses = encoded

    def solve() -> tuple[bool, list[int] | None]:
        with Solver(name="m22", bootstrap_with=[*clauses, [output]]) as solver:
            status = bool(solver.solve())
            model = solver.get_model() if status else None
        return status, model

    (status, model), solve_ns = _stage(solve)
    witness = None
    if status and model is not None:
        positive = {literal for literal in model if literal > 0}
        witness = [int(index + 1 in positive) for index in range(n_vars)]
    return status, witness, {"encode_ns": encode_ns, "solve_ns": solve_ns}


def _sympy_equivalence(left: Any, right: Any, n_vars: int) -> tuple[bool, dict[str, int]]:
    import sympy as sp
    from sympy.logic.inference import satisfiable

    converted, convert_ns = _stage(
        lambda: (_sympy_expression(left, n_vars), _sympy_expression(right, n_vars))
    )
    different, solve_ns = _stage(
        lambda: satisfiable(sp.Xor(converted[0], converted[1], evaluate=False), algorithm="dpll2")
    )
    return different is False, {"convert_ns": convert_ns, "solve_difference_miter_ns": solve_ns}


def _cm_equivalence(left: Any, right: Any, n_vars: int) -> tuple[bool, dict[str, int]]:
    left_values, left_timings = _cm_truth(left, n_vars)
    right_values, right_timings = _cm_truth(right, n_vars)
    equivalent, compare_ns = _stage(lambda: left_values == right_values)
    timings = {f"left_{key}": value for key, value in left_timings.items()}
    timings.update({f"right_{key}": value for key, value in right_timings.items()})
    timings["compare_ns"] = compare_ns
    return bool(equivalent), timings


def _pysat_equivalence(left: Any, right: Any, n_vars: int) -> tuple[bool, dict[str, int]]:
    from cm_exprlib import miter_equiv
    from pysat.solvers import Solver

    encoded, encode_ns = _stage(lambda: miter_equiv(left, right, n_vars))
    _, clauses = encoded

    def solve() -> bool:
        with Solver(name="m22", bootstrap_with=clauses) as solver:
            return bool(solver.solve())

    difference_sat, solve_ns = _stage(solve)
    return not difference_sat, {"encode_difference_miter_ns": encode_ns, "solve_ns": solve_ns}


def expression_quality(expression: Any) -> dict[str, int]:
    import sympy as sp
    from sympy.logic.boolalg import BooleanFunction

    literals = 0
    for node in sp.preorder_traversal(expression):
        if isinstance(node, sp.Symbol):
            literals += 1
    operations = sum(
        1 for node in sp.preorder_traversal(expression) if isinstance(node, BooleanFunction)
    )
    text = sp.srepr(expression)
    return {
        "literal_occurrences": literals,
        "boolean_operations": operations,
        "srepr_bytes": len(text.encode("utf-8")),
    }


def _sympy_simplify(expr: Any, n_vars: int, form: str, *, force: bool) -> tuple[Any, dict[str, int]]:
    import sympy as sp

    converted, convert_ns = _stage(lambda: _sympy_expression(expr, n_vars))
    simplified, simplify_ns = _stage(
        lambda: sp.simplify_logic(converted, form=form, force=force)
    )
    return simplified, {"convert_ns": convert_ns, "simplify_ns": simplify_ns}


def _cm_truth_simplify(expr: Any, n_vars: int, form: str) -> tuple[Any, dict[str, int]]:
    import sympy as sp

    values, timings = _cm_truth(expr, n_vars)
    symbols = [sp.Symbol(f"x{i}") for i in range(n_vars)]
    minterms = [
        [(row >> (n_vars - 1 - index)) & 1 for index in range(n_vars)]
        for row, value in enumerate(values)
        if value
    ]
    constructor = sp.SOPform if form == "dnf" else sp.POSform
    simplified, simplify_ns = _stage(lambda: constructor(symbols, minterms))
    timings["sympy_minimizer_ns"] = simplify_ns
    return simplified, timings


def _sympy_values(expression: Any, n_vars: int) -> list[int]:
    from sympy.logic.boolalg import truth_table
    import sympy as sp

    symbols = [sp.Symbol(f"x{i}") for i in range(n_vars)]
    return [int(bool(value)) for value in truth_table(expression, symbols, input=False)]


def _result(
    *,
    contract: Mapping[str, Any],
    arm: str,
    repetition: int,
    timings: Mapping[str, int],
    task_started_ns: int,
    artifact: Mapping[str, Any],
    validation: Mapping[str, Any],
    quality: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    total = time.perf_counter_ns() - task_started_ns
    row = {
        "schema": RESULT_SCHEMA,
        "contract_sha256": sha256_json(contract),
        "family": contract["family"],
        "task": contract["task"],
        "case_id": contract["case_id"],
        "arm": arm,
        "repetition": repetition,
        "status": "ok" if validation.get("matches_oracle") else "mismatch",
        "reason": "completed" if validation.get("matches_oracle") else "oracle mismatch",
        "timings_ns": {**timings, "task_total_ns": total},
        "artifact": dict(artifact),
        "validation": dict(validation),
        "quality": dict(quality) if quality is not None else None,
    }
    return row


def _preload_compared_runtimes() -> None:
    """Load every arm's runtime before task timing; caller timing retains it."""
    import numpy  # noqa: F401
    import sympy  # noqa: F401
    from bitset_backend import eval_cm_node_flat  # noqa: F401
    from cm_ir import compile_expr_to_cm_ir  # noqa: F401
    from expr_simplify import _to_sympy  # noqa: F401
    from pysat.solvers import Solver  # noqa: F401


def execute_worker(request: Mapping[str, Any]) -> dict[str, Any]:
    """Execute one isolated comparison cell and validate outside its timer."""
    required = {"contract", "case", "arm", "repetition", "assignment_generator"}
    if not isinstance(request, Mapping) or set(request) != required:
        raise ValueError("worker request fields")
    contract = request["contract"]
    validate_contract(contract)
    case = request["case"]
    n_vars = len(contract["variables"])
    expr = parse_expression(case["expression"])
    arm = request["arm"]
    repetition = request["repetition"]
    _preload_compared_runtimes()
    started = time.perf_counter_ns()

    if contract["task"] == "complete_relation":
        if arm == "sympy_truth_table":
            values, timings = _sympy_truth(expr, n_vars)
        elif arm == "cm_packed":
            values, timings = _cm_truth(expr, n_vars)
        else:
            raise ValueError("unknown complete-relation arm")
        artifact_bytes = pack_values(values)
        digest = sha256_bytes(artifact_bytes)
        return _result(
            contract=contract,
            arm=arm,
            repetition=repetition,
            timings=timings,
            task_started_ns=started,
            artifact={"kind": "packed_truth_bits", "bytes": len(artifact_bytes), "sha256": digest},
            validation={"matches_oracle": digest == contract["artifact"]["semantic_sha256"]},
        )

    if contract["task"] == "assignment_batch":
        raw_rows = assignment_rows(request["assignment_generator"], n_vars)
        if arm == "sympy_lambdify_cse_off":
            values, timings = _sympy_batch(expr, n_vars, raw_rows, cse=False)
        elif arm == "sympy_lambdify_cse_on":
            values, timings = _sympy_batch(expr, n_vars, raw_rows, cse=True)
        elif arm == "cm_ir_batch":
            values, timings = _cm_batch(expr, n_vars, raw_rows)
        else:
            raise ValueError("unknown assignment arm")
        artifact_bytes = pack_values(values)
        digest = sha256_bytes(artifact_bytes)
        return _result(
            contract=contract,
            arm=arm,
            repetition=repetition,
            timings=timings,
            task_started_ns=started,
            artifact={"kind": "packed_assignment_bits", "bytes": len(artifact_bytes), "sha256": digest},
            validation={
                "assignment_sha256": sha256_bytes(raw_rows),
                "matches_oracle": digest == contract["artifact"]["semantic_sha256"],
            },
        )

    if contract["task"] == "sat_status":
        functions = {
            "sympy_satisfiable": _sympy_sat,
            "cm_packed_sat": _cm_sat,
            "pysat_tseitin": _pysat_sat,
        }
        if arm not in functions:
            raise ValueError("unknown SAT arm")
        status, witness, timings = functions[arm](expr, n_vars)
        truth = scalar_truth_values(expr, n_vars)
        witness_valid = witness is None
        if witness is not None:
            row = sum(bit << (n_vars - 1 - index) for index, bit in enumerate(witness))
            witness_valid = bool(truth[row])
        digest = sha256_json({"value": status})
        return _result(
            contract=contract,
            arm=arm,
            repetition=repetition,
            timings=timings,
            task_started_ns=started,
            artifact={"kind": "boolean_status", "bytes": len(canonical_bytes({"value": status})), "sha256": digest, "value": status},
            validation={
                "witness_present": witness is not None,
                "witness_valid": witness_valid,
                "matches_oracle": digest == contract["artifact"]["semantic_sha256"] and witness_valid,
            },
        )

    if contract["task"] == "equivalence_status":
        right = parse_expression(case["comparison_expression"])
        functions = {
            "sympy_difference_sat": _sympy_equivalence,
            "cm_packed_equivalence": _cm_equivalence,
            "pysat_tseitin_miter": _pysat_equivalence,
        }
        if arm not in functions:
            raise ValueError("unknown equivalence arm")
        status, timings = functions[arm](expr, right, n_vars)
        digest = sha256_json({"value": status})
        return _result(
            contract=contract,
            arm=arm,
            repetition=repetition,
            timings=timings,
            task_started_ns=started,
            artifact={"kind": "boolean_status", "bytes": len(canonical_bytes({"value": status})), "sha256": digest, "value": status},
            validation={"matches_oracle": digest == contract["artifact"]["semantic_sha256"]},
        )

    if contract["task"] == "simplified_expression":
        form = contract["artifact"]["form"]
        if arm == "sympy_simplify_default":
            simplified, timings = _sympy_simplify(expr, n_vars, form, force=False)
        elif arm == "sympy_simplify_forced":
            simplified, timings = _sympy_simplify(expr, n_vars, form, force=True)
        elif arm == "cm_truth_sympy_minimizer":
            simplified, timings = _cm_truth_simplify(expr, n_vars, form)
        else:
            raise ValueError("unknown simplification arm")
        import sympy as sp

        text = sp.srepr(simplified)
        semantic_digest = packed_digest(_sympy_values(simplified, n_vars))
        return _result(
            contract=contract,
            arm=arm,
            repetition=repetition,
            timings=timings,
            task_started_ns=started,
            artifact={
                "kind": "simplified_boolean_expression",
                "bytes": len(text.encode("utf-8")),
                "sha256": sha256_bytes(text.encode("utf-8")),
                "semantic_sha256": semantic_digest,
                "form": form,
            },
            validation={"matches_oracle": semantic_digest == contract["artifact"]["semantic_sha256"]},
            quality=expression_quality(simplified),
        )

    raise ValueError("unknown task")


def validate_inputs(document: Mapping[str, Any]) -> None:
    if not isinstance(document, Mapping) or set(document) != {"schema", "cases", "assignment_generator"}:
        raise ValueError("input manifest fields")
    if document["schema"] != SCHEMA or not isinstance(document["cases"], list):
        raise ValueError("input manifest schema")
    ids: set[str] = set()
    for case in document["cases"]:
        if not isinstance(case, Mapping) or set(case) != {
            "case_id", "n_vars", "expression", "families", "comparison_expression", "simplification_forms"
        }:
            raise ValueError("case fields")
        case_id = case["case_id"]
        n_vars = case["n_vars"]
        if not isinstance(case_id, str) or case_id in ids or type(n_vars) is not int or not 1 <= n_vars <= MAX_VARIABLES:
            raise ValueError("case identity/bounds")
        ids.add(case_id)
        validate_expression(case["expression"], n_vars)
        if case["comparison_expression"] is not None:
            validate_expression(case["comparison_expression"], n_vars)
        if not set(case["families"]).issubset({"Y02", "Y03", "Y04", "Y05"}):
            raise ValueError("unknown case family")
        if not set(case["simplification_forms"]).issubset({"dnf", "cnf"}):
            raise ValueError("unknown simplification form")
    raw = assignment_rows(document["assignment_generator"], MAX_VARIABLES)
    if len(raw) != document["assignment_generator"]["rows"] * MAX_VARIABLES:
        raise ValueError("assignment generator size")


def build_contracts(document: Mapping[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return frozen contracts paired with their case records."""
    validate_inputs(document)
    contracts: list[tuple[dict[str, Any], dict[str, Any]]] = []
    generator = document["assignment_generator"]
    for case in document["cases"]:
        n_vars = case["n_vars"]
        expr = parse_expression(case["expression"])
        truth = scalar_truth_values(expr, n_vars)
        truth_digest = packed_digest(truth)
        if "Y02" in case["families"]:
            contracts.append((make_contract(
                family="Y02", task="complete_relation", case_id=case["case_id"],
                n_vars=n_vars, artifact_kind="packed_truth_bits", expected_sha256=truth_digest,
            ), dict(case)))
        if "Y03" in case["families"]:
            raw_rows = assignment_rows(generator, n_vars)
            batch_digest = packed_digest(assignment_output(expr, n_vars, raw_rows))
            contracts.append((make_contract(
                family="Y03", task="assignment_batch", case_id=case["case_id"],
                n_vars=n_vars, artifact_kind="packed_assignment_bits", expected_sha256=batch_digest,
                batch_rows=generator["rows"],
            ), dict(case)))
        if "Y04" in case["families"]:
            sat_digest = sha256_json({"value": bool(any(truth))})
            contracts.append((make_contract(
                family="Y04", task="sat_status", case_id=case["case_id"],
                n_vars=n_vars, artifact_kind="boolean_status", expected_sha256=sat_digest,
            ), dict(case)))
            if case["comparison_expression"] is not None:
                right = parse_expression(case["comparison_expression"])
                equivalent = truth == scalar_truth_values(right, n_vars)
                equiv_digest = sha256_json({"value": equivalent})
                contracts.append((make_contract(
                    family="Y04", task="equivalence_status", case_id=case["case_id"],
                    n_vars=n_vars, artifact_kind="boolean_status", expected_sha256=equiv_digest,
                ), dict(case)))
        if "Y05" in case["families"]:
            for form in case["simplification_forms"]:
                contracts.append((make_contract(
                    family="Y05", task="simplified_expression", case_id=case["case_id"],
                    n_vars=n_vars, artifact_kind="simplified_boolean_expression",
                    expected_sha256=truth_digest, form=form,
                ), dict(case)))
    return contracts


def arms_for(contract: Mapping[str, Any]) -> tuple[str, ...]:
    return {
        "complete_relation": ("sympy_truth_table", "cm_packed"),
        "assignment_batch": ("sympy_lambdify_cse_off", "sympy_lambdify_cse_on", "cm_ir_batch"),
        "sat_status": ("sympy_satisfiable", "cm_packed_sat", "pysat_tseitin"),
        "equivalence_status": ("sympy_difference_sat", "cm_packed_equivalence", "pysat_tseitin_miter"),
        "simplified_expression": (
            "sympy_simplify_default", "sympy_simplify_forced", "cm_truth_sympy_minimizer"
        ),
    }[contract["task"]]


def median(values: Sequence[int]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["family"], row["task"], row["arm"]), []).append(row)
    scoreboards: list[dict[str, Any]] = []
    for (family, task, arm), group in sorted(groups.items()):
        completed = [row for row in group if row["status"] == "ok"]
        totals = [row["timings_ns"]["task_total_ns"] for row in completed]
        caller = [row["caller_total_ns"] for row in completed]
        entry: dict[str, Any] = {
            "family": family,
            "task": task,
            "arm": arm,
            "cells": len(group),
            "ok": len(completed),
            "median_task_total_ns": median(totals) if totals else None,
            "median_caller_total_ns": median(caller) if caller else None,
        }
        if task == "simplified_expression" and completed:
            for key in ("literal_occurrences", "boolean_operations", "srepr_bytes"):
                entry[f"median_{key}"] = median([row["quality"][key] for row in completed])
        scoreboards.append(entry)
    return {
        "schema": "cm-sympy-claim-cleanup-summary/v1",
        "rows": len(rows),
        "ok": sum(row["status"] == "ok" for row in rows),
        "mismatch": sum(row["status"] == "mismatch" for row in rows),
        "timeout": sum(row["status"] == "timeout" for row in rows),
        "error": sum(row["status"] == "error" for row in rows),
        "scoreboards": scoreboards,
    }
