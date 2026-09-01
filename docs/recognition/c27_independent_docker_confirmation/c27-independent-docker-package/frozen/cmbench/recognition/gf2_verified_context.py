"""Hash-bound single-evaluation request contexts for exact GF(2) completion."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from cm_expr_serde import expr_from_json

from .gf2_decomposition import truth_sha256
from .gf2_task_dispatcher import canonical_sha256
from .portfolio import reference_bits
from .source_anf_hybrid import packed_truth_bits, source_anf_packed

CONTEXT_SCHEMA = "crse-c26-verified-gf2-request-context/v1"
MIN_VARS = 3
MAX_VARS = 6


@dataclass(frozen=True)
class VerifiedGF2RequestContext:
    case_id: str
    n_vars: int
    expression_sha256: str
    truth_bits_hex: str
    truth_sha256: str
    packed_polynomial_hex: str | None
    packed_polynomial_sha256: str | None
    packed_instrumentation: dict[str, Any] | None
    source_packed_verified: bool
    context_sha256: str
    schema: str = CONTEXT_SCHEMA

    @property
    def truth_bits(self) -> int:
        return int(self.truth_bits_hex, 16)

    @property
    def packed_polynomial(self) -> int | None:
        return (None if self.packed_polynomial_hex is None
                else int(self.packed_polynomial_hex, 16))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _body(*, case_id: str, n_vars: int, expression_sha256: str,
          truth_bits_hex: str, truth_digest: str,
          packed_polynomial_hex: str | None,
          packed_polynomial_sha256: str | None,
          packed_instrumentation: dict[str, Any] | None,
          source_packed_verified: bool) -> dict[str, Any]:
    return {
        "schema": CONTEXT_SCHEMA,
        "case_id": case_id,
        "n_vars": n_vars,
        "expression_sha256": expression_sha256,
        "truth_bits_hex": truth_bits_hex,
        "truth_sha256": truth_digest,
        "packed_polynomial_hex": packed_polynomial_hex,
        "packed_polynomial_sha256": packed_polynomial_sha256,
        "packed_instrumentation": packed_instrumentation,
        "source_packed_verified": source_packed_verified,
    }


def build_verified_gf2_context(
    case: Mapping[str, Any], *, require_source_packed: bool,
) -> VerifiedGF2RequestContext:
    """Validate one request and evaluate its expression exactly once."""
    case_id = case.get("case_id") if isinstance(case, Mapping) else None
    n_vars = case.get("n_vars") if isinstance(case, Mapping) else None
    if (
        not isinstance(case, Mapping)
        or type(case_id) is not str
        or not case_id
        or len(case_id) > 256
        or type(n_vars) is not int
        or not MIN_VARS <= n_vars <= MAX_VARS
        or type(case.get("expression_v2")) is not dict
        or type(case.get("truth_bits_hex")) is not str
        or type(require_source_packed) is not bool
    ):
        raise ValueError("invalid C26 request envelope")
    expression_document = case["expression_v2"]
    expression = expr_from_json(expression_document)
    frozen_bits = int(case["truth_bits_hex"], 16)
    if frozen_bits < 0 or frozen_bits.bit_length() > (1 << n_vars):
        raise ValueError("invalid C26 frozen truth bound")
    evaluated_bits = reference_bits(expression, n_vars)
    if evaluated_bits != frozen_bits:
        raise ValueError("C26 expression/truth mismatch")
    expression_digest = canonical_sha256(expression_document)
    truth_digest = truth_sha256(evaluated_bits, n_vars)

    polynomial_hex = polynomial_digest = None
    instrumentation = None
    source_verified = False
    if require_source_packed:
        polynomial, stats = source_anf_packed(expression_document, n_vars)
        if packed_truth_bits(polynomial, n_vars) != evaluated_bits:
            raise RuntimeError("C26 source-packed context disagrees with verified truth")
        polynomial_hex = hex(polynomial)
        polynomial_digest = canonical_sha256({
            "n_vars": n_vars,
            "packed_polynomial_hex": polynomial_hex,
        })
        instrumentation = stats.to_dict()
        source_verified = True
    body = _body(
        case_id=case_id,
        n_vars=n_vars,
        expression_sha256=expression_digest,
        truth_bits_hex=hex(evaluated_bits),
        truth_digest=truth_digest,
        packed_polynomial_hex=polynomial_hex,
        packed_polynomial_sha256=polynomial_digest,
        packed_instrumentation=instrumentation,
        source_packed_verified=source_verified,
    )
    return VerifiedGF2RequestContext(
        case_id=case_id,
        n_vars=n_vars,
        expression_sha256=expression_digest,
        truth_bits_hex=hex(evaluated_bits),
        truth_sha256=truth_digest,
        packed_polynomial_hex=polynomial_hex,
        packed_polynomial_sha256=polynomial_digest,
        packed_instrumentation=instrumentation,
        source_packed_verified=source_verified,
        context_sha256=canonical_sha256(body),
    )


def verify_verified_gf2_context(document: dict[str, Any], case: Mapping[str, Any], *,
                                replay_semantics: bool = False) -> None:
    expected = {field.name for field in VerifiedGF2RequestContext.__dataclass_fields__.values()}
    if type(document) is not dict or set(document) != expected:
        raise ValueError("invalid C26 verified-context fields")
    case_id, n_vars = case.get("case_id"), case.get("n_vars")
    truth_bits_hex = document.get("truth_bits_hex")
    try:
        bits = int(truth_bits_hex, 16)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid C26 verified truth encoding") from exc
    source_verified = document.get("source_packed_verified")
    polynomial_hex = document.get("packed_polynomial_hex")
    polynomial_digest = document.get("packed_polynomial_sha256")
    instrumentation = document.get("packed_instrumentation")
    if source_verified is True:
        if type(polynomial_hex) is not str or type(polynomial_digest) is not str or type(instrumentation) is not dict:
            raise ValueError("invalid C26 packed context")
        try:
            polynomial = int(polynomial_hex, 16)
        except ValueError as exc:
            raise ValueError("invalid C26 packed polynomial") from exc
        if polynomial_digest != canonical_sha256({
                "n_vars": n_vars, "packed_polynomial_hex": polynomial_hex}):
            raise ValueError("invalid C26 packed polynomial digest")
    elif source_verified is False:
        polynomial = None
        if polynomial_hex is not None or polynomial_digest is not None or instrumentation is not None:
            raise ValueError("invalid C26 truth-only context")
    else:
        raise ValueError("invalid C26 packed verification flag")
    body = _body(
        case_id=document.get("case_id"),
        n_vars=document.get("n_vars"),
        expression_sha256=document.get("expression_sha256"),
        truth_bits_hex=truth_bits_hex,
        truth_digest=document.get("truth_sha256"),
        packed_polynomial_hex=polynomial_hex,
        packed_polynomial_sha256=polynomial_digest,
        packed_instrumentation=instrumentation,
        source_packed_verified=source_verified,
    )
    if (
        document.get("schema") != CONTEXT_SCHEMA
        or document.get("case_id") != case_id
        or document.get("n_vars") != n_vars
        or not MIN_VARS <= n_vars <= MAX_VARS
        or document.get("expression_sha256") != canonical_sha256(case.get("expression_v2"))
        or bits != int(case.get("truth_bits_hex"), 16)
        or document.get("truth_sha256") != truth_sha256(bits, n_vars)
        or document.get("context_sha256") != canonical_sha256(body)
    ):
        raise ValueError("invalid C26 verified-context identity")
    if replay_semantics:
        expression = expr_from_json(case["expression_v2"])
        if reference_bits(expression, n_vars) != bits:
            raise ValueError("C26 context semantic replay mismatch")
        if polynomial is not None and packed_truth_bits(polynomial, n_vars) != bits:
            raise ValueError("C26 packed context semantic replay mismatch")
