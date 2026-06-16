from __future__ import annotations

from typing import Any, Mapping

from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor


_BIN_OPS = {
    "and": And,
    "or": Or,
    "xor": Xor,
    "imp": Imp,
    "eqv": Eqv,
}


def expr_to_json(expr: Expr) -> dict[str, Any]:
    if isinstance(expr, Var):
        return {"op": "var", "i": int(expr.i)}
    if isinstance(expr, Not):
        return {"op": "not", "a": expr_to_json(expr.a)}
    for op_name, cls in _BIN_OPS.items():
        if isinstance(expr, cls):
            return {"op": op_name, "a": expr_to_json(expr.a), "b": expr_to_json(expr.b)}
    raise TypeError(f"unsupported expression node: {expr!r}")


def expr_from_json(data: Mapping[str, Any]) -> Expr:
    op = str(data.get("op", "")).lower()
    if op == "var":
        return Var(int(data["i"]))
    if op == "not":
        return Not(expr_from_json(_expect_mapping(data.get("a"), "a")))
    if op in _BIN_OPS:
        return _BIN_OPS[op](
            expr_from_json(_expect_mapping(data.get("a"), "a")),
            expr_from_json(_expect_mapping(data.get("b"), "b")),
        )
    raise ValueError(f"unsupported expression op: {op!r}")


def _expect_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"expression field {field!r} must be an object")
    return value
