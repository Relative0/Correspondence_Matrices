"""Validate an external decomposition payload against the C16 artifact contract.

This adapter deliberately does not translate a foreign decomposition into a
different GF(2) factorization.  A direct output-contract comparison is valid
only when the external producer supplies a complete C16-shaped artifact that
passes the same reconstruction and document-identity checks.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .gf2_decomposition import ExactGF2Artifact, SCHEMA as ARTIFACT_SCHEMA, truth_sha256


ADAPTER_SCHEMA = "crse-external-gf2-artifact-adapter/v1"
EXTERNAL_CANDIDATE_SCHEMA = "crse-external-exact-gf2-candidate/v1"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _artifact_document_sha256(document: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(document)).hexdigest()


def _result(*, producer: str, bits: int, n_vars: int, status: str, detail: str,
            artifact: ExactGF2Artifact | None = None,
            expected_selected_document: Mapping[str, Any] | None = None) -> dict[str, Any]:
    document = artifact.to_dict() if artifact is not None else None
    expected = dict(expected_selected_document) if expected_selected_document is not None else None
    return {
        "schema": ADAPTER_SCHEMA,
        "external_producer": producer,
        "source_truth_sha256": truth_sha256(bits, n_vars),
        "n_vars": n_vars,
        "artifact_contract": ARTIFACT_SCHEMA,
        "status": status,
        "detail": detail,
        "artifact": document,
        "artifact_document_sha256": _artifact_document_sha256(document) if document is not None else None,
        "expected_selected_document_supplied": expected is not None,
        "byte_identical_to_expected_selected_artifact": (
            document == expected if expected is not None and document is not None else None
        ),
    }


def adapt_external_candidate(*, source_bits: int, n_vars: int, external: Mapping[str, Any],
                             expected_selected_document: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Accept only an externally supplied, reconstructing C16 artifact document.

    ``expected_selected_document`` is optional.  It is for a comparison caller
    that already has a frozen global selection answer; the adapter never
    computes an alternative winner and never turns a non-C16 payload into one.
    """
    if not isinstance(external, Mapping):
        raise ValueError("external candidate record must be a mapping")
    required = {"schema", "producer", "n_vars", "source_truth_sha256", "artifact"}
    if set(external) != required:
        raise ValueError("invalid external candidate fields")
    producer = external["producer"]
    if type(producer) is not str or not producer:
        raise ValueError("external producer must be a non-empty string")
    source_sha = truth_sha256(source_bits, n_vars)
    if external["schema"] != EXTERNAL_CANDIDATE_SCHEMA:
        return _result(
            producer=producer, bits=source_bits, n_vars=n_vars, status="incompatible",
            detail="External record does not declare the exact-GF(2) candidate interchange schema.",
            expected_selected_document=expected_selected_document,
        )
    if external["n_vars"] != n_vars or external["source_truth_sha256"] != source_sha:
        return _result(
            producer=producer, bits=source_bits, n_vars=n_vars, status="rejected",
            detail="External record source-function identity does not match the frozen truth vector.",
            expected_selected_document=expected_selected_document,
        )
    if external["artifact"] is None:
        return _result(
            producer=producer, bits=source_bits, n_vars=n_vars, status="incompatible",
            detail="External record provides no complete C16 artifact document or factor payload.",
            expected_selected_document=expected_selected_document,
        )
    try:
        artifact = ExactGF2Artifact.from_dict(external["artifact"])
    except (TypeError, ValueError, KeyError) as exc:
        return _result(
            producer=producer, bits=source_bits, n_vars=n_vars, status="rejected",
            detail=f"External artifact fails the C16 artifact contract: {type(exc).__name__}: {exc}",
            expected_selected_document=expected_selected_document,
        )
    if artifact.document["n_vars"] != n_vars or artifact.reconstruct() != source_bits:
        return _result(
            producer=producer, bits=source_bits, n_vars=n_vars, status="rejected",
            detail="External artifact does not reconstruct the supplied frozen truth vector.",
            expected_selected_document=expected_selected_document,
        )
    return _result(
        producer=producer, bits=source_bits, n_vars=n_vars, status="accepted",
        detail="External artifact is C16-contract-valid and exactly reconstructs the frozen truth vector.",
        artifact=artifact, expected_selected_document=expected_selected_document,
    )


def adapt_abc_acd_result(*, source_bits: int, n_vars: int, abc_result: Mapping[str, Any],
                         producer: str = "Berkeley ABC ACD",
                         expected_selected_document: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Expose the precise C16-contract gap in an ABC ACD result.

    The existing ABC runner reports only feasibility, LUT cost, and delay.  It
    has no full factor payload that can be checked as a C16 artifact.  Returning
    ``incompatible`` is intentional: fabricating a GF(2) payload would make a
    direct artifact or timing comparison misleading.
    """
    if not isinstance(abc_result, Mapping):
        raise ValueError("ABC result must be a mapping")
    observed = {"status", "return_value", "delay_profile", "lut_cost", "algorithm_ns", "n_vars", "lut_size"}
    missing = sorted(observed - set(abc_result))
    if missing:
        return _result(
            producer=producer, bits=source_bits, n_vars=n_vars, status="rejected",
            detail=f"ABC result is missing required runner fields: {', '.join(missing)}.",
            expected_selected_document=expected_selected_document,
        )
    if abc_result["n_vars"] != n_vars:
        return _result(
            producer=producer, bits=source_bits, n_vars=n_vars, status="rejected",
            detail="ABC result n_vars does not match the frozen truth vector.",
            expected_selected_document=expected_selected_document,
        )
    candidate = {
        "schema": EXTERNAL_CANDIDATE_SCHEMA,
        "producer": producer,
        "n_vars": n_vars,
        "source_truth_sha256": truth_sha256(source_bits, n_vars),
        "artifact": None,
    }
    return adapt_external_candidate(
        source_bits=source_bits, n_vars=n_vars, external=candidate,
        expected_selected_document=expected_selected_document,
    )
