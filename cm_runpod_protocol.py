from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

from cm_expr_serde import expr_from_json, expr_to_json
from cm_exprlib import Expr
from cmbench.output_budget import OutputBudget


@dataclass(frozen=True)
class CMRemoteRequest:
    request_id: str
    expr: dict[str, Any]
    vars_all: list[str]
    mode: str = "hybrid_no_reinflate"
    use_persistent_cache: bool = True
    hybrid_threshold: int = 7
    eval_repeat: int = 1
    return_format: str = "packed_bitset_or_summary"
    allow_reduced_output: bool = False
    max_full_output_vars: int | None = None
    max_output_bytes: int | None = 1 << 16
    max_temporary_bytes: int | None = None
    words_eval: bool = False

    @classmethod
    def from_expr(
        cls,
        expr: Expr,
        vars_all: list[str],
        *,
        request_id: str | None = None,
        mode: str = "hybrid_no_reinflate",
        use_persistent_cache: bool = True,
        hybrid_threshold: int = 7,
        eval_repeat: int = 1,
        return_format: str = "packed_bitset_or_summary",
        allow_reduced_output: bool = False,
        max_full_output_vars: int | None = None,
        max_output_bytes: int | None = 1 << 16,
        max_temporary_bytes: int | None = None,
        words_eval: bool = False,
    ) -> "CMRemoteRequest":
        return cls(
            request_id=request_id or str(uuid.uuid4()),
            expr=expr_to_json(expr),
            vars_all=list(vars_all),
            mode=mode,
            use_persistent_cache=use_persistent_cache,
            hybrid_threshold=int(hybrid_threshold),
            eval_repeat=int(eval_repeat),
            return_format=return_format,
            allow_reduced_output=bool(allow_reduced_output),
            max_full_output_vars=max_full_output_vars,
            max_output_bytes=max_output_bytes,
            max_temporary_bytes=max_temporary_bytes,
            words_eval=bool(words_eval),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CMRemoteRequest":
        # Validate before coercion: int(-0.5), int(True), and int("16") must not
        # silently turn malformed limits into valid remote admission policies.
        budget = OutputBudget(
            max_output_bytes=data.get("max_output_bytes", 1 << 16),
            max_temporary_bytes=data.get("max_temporary_bytes"),
            max_output_vars=data.get("max_full_output_vars"),
        )
        return cls(
            request_id=str(data["request_id"]),
            expr=dict(data["expr"]),
            vars_all=[str(v) for v in data["vars_all"]],
            mode=str(data.get("mode", "hybrid_no_reinflate")),
            use_persistent_cache=bool(data.get("use_persistent_cache", True)),
            hybrid_threshold=int(data.get("hybrid_threshold", 7)),
            eval_repeat=int(data.get("eval_repeat", 1)),
            return_format=str(data.get("return_format", "packed_bitset_or_summary")),
            allow_reduced_output=bool(data.get("allow_reduced_output", False)),
            max_full_output_vars=budget.max_output_vars,
            max_output_bytes=budget.max_output_bytes,
            max_temporary_bytes=budget.max_temporary_bytes,
            words_eval=bool(data.get("words_eval", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "expr": self.expr,
            "vars_all": self.vars_all,
            "mode": self.mode,
            "use_persistent_cache": self.use_persistent_cache,
            "hybrid_threshold": self.hybrid_threshold,
            "eval_repeat": self.eval_repeat,
            "return_format": self.return_format,
            "allow_reduced_output": self.allow_reduced_output,
            "max_full_output_vars": self.max_full_output_vars,
            "max_output_bytes": self.max_output_bytes,
            "max_temporary_bytes": self.max_temporary_bytes,
            "words_eval": self.words_eval,
        }

    def to_expr(self) -> Expr:
        return expr_from_json(self.expr)


@dataclass(frozen=True)
class CMRemoteResponse:
    request_id: str
    ok: bool
    result_repr: str
    status: str = "ok"
    result: dict[str, Any] | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)
    timing: dict[str, float] = field(default_factory=dict)
    error: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CMRemoteResponse":
        result = data.get("result")
        return cls(
            request_id=str(data.get("request_id", "")),
            ok=bool(data.get("ok", False)),
            result_repr=str(data.get("result_repr", "")),
            status=str(data.get("status", "ok" if data.get("ok", False) else "error")),
            result=dict(result) if isinstance(result, Mapping) else None,
            diagnostics=dict(data.get("diagnostics", {})),
            timing={str(k): float(v) for k, v in dict(data.get("timing", {})).items()},
            error=None if data.get("error") is None else str(data.get("error")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "ok": self.ok,
            "result_repr": self.result_repr,
            "status": self.status,
            "result": self.result,
            "diagnostics": self.diagnostics,
            "timing": self.timing,
            "error": self.error,
        }


def dumps_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def result_payload(result: Any, *, return_format: str = "packed_bitset_or_summary") -> tuple[str, dict[str, Any]]:
    output_vars = list(getattr(result, "output_vars", tuple()))
    code = int(getattr(result, "final_output_representation_code"))
    bits = getattr(result, "bits", None)
    tt = getattr(result, "tt", None)
    if bits is not None:
        payload = {"bits_hex": hex(int(bits)), "output_vars": output_vars, "representation_code": code}
        return "packed_bitset", _with_digest(payload)
    if isinstance(tt, np.ndarray):
        flat = tt.astype(np.uint8, copy=False).reshape(-1)
        if return_format == "dense_tt":
            payload = {"tt": flat.tolist(), "output_vars": output_vars, "representation_code": code}
        else:
            payload = {
                "length": int(flat.size),
                "ones": int(flat.sum()),
                "output_vars": output_vars,
                "representation_code": code,
            }
        return "truth_table_summary" if return_format != "dense_tt" else "truth_table", _with_digest(payload, flat)
    payload = {"output_vars": output_vars, "representation_code": code}
    return "summary", _with_digest(payload)


def _with_digest(payload: dict[str, Any], arr: np.ndarray | None = None) -> dict[str, Any]:
    h = hashlib.sha256()
    if arr is not None:
        h.update(arr.astype(np.uint8, copy=False).reshape(-1).tobytes())
    else:
        h.update(dumps_json(payload).encode("utf-8"))
    payload["sha256"] = h.hexdigest()
    return payload
