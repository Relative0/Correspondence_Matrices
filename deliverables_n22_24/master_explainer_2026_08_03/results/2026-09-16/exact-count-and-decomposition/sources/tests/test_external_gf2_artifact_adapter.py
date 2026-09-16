from __future__ import annotations

from cmbench.recognition.external_gf2_artifact_adapter import (
    ADAPTER_SCHEMA,
    EXTERNAL_CANDIDATE_SCHEMA,
    adapt_abc_acd_result,
    adapt_external_candidate,
)
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2, truth_sha256


def _fixture() -> tuple[int, int, dict]:
    bits, n_vars = 0, 4
    for assignment in range(1 << n_vars):
        x0, x1, x2, x3 = ((assignment >> shift) & 1 for shift in (3, 2, 1, 0))
        bits |= ((x0 & x1) ^ (x2 | x3)) << assignment
    best = analyze_exact_gf2(bits, n_vars).best
    assert best is not None
    return bits, n_vars, best.to_dict()


def test_external_artifact_adapter_accepts_only_exact_c16_document() -> None:
    bits, n_vars, document = _fixture()
    result = adapt_external_candidate(
        source_bits=bits,
        n_vars=n_vars,
        external={
            "schema": EXTERNAL_CANDIDATE_SCHEMA,
            "producer": "independent-fixture",
            "n_vars": n_vars,
            "source_truth_sha256": truth_sha256(bits, n_vars),
            "artifact": document,
        },
        expected_selected_document=document,
    )
    assert result["schema"] == ADAPTER_SCHEMA
    assert result["status"] == "accepted"
    assert result["artifact"] == document
    assert result["byte_identical_to_expected_selected_artifact"] is True


def test_external_artifact_adapter_rejects_tampered_or_payloadless_results() -> None:
    bits, n_vars, document = _fixture()
    changed = dict(document)
    changed["source_sha256"] = truth_sha256(0, n_vars)
    rejected = adapt_external_candidate(
        source_bits=bits,
        n_vars=n_vars,
        external={
            "schema": EXTERNAL_CANDIDATE_SCHEMA,
            "producer": "tampered-fixture",
            "n_vars": n_vars,
            "source_truth_sha256": truth_sha256(bits, n_vars),
            "artifact": changed,
        },
    )
    assert rejected["status"] == "rejected"
    no_payload = adapt_external_candidate(
        source_bits=bits,
        n_vars=n_vars,
        external={
            "schema": EXTERNAL_CANDIDATE_SCHEMA,
            "producer": "payloadless-fixture",
            "n_vars": n_vars,
            "source_truth_sha256": truth_sha256(bits, n_vars),
            "artifact": None,
        },
    )
    assert no_payload["status"] == "incompatible"


def test_abc_acd_adapter_records_contract_incompatibility_without_fabricating_artifact() -> None:
    bits, n_vars, document = _fixture()
    result = adapt_abc_acd_result(
        source_bits=bits,
        n_vars=n_vars,
        abc_result={
            "status": "decomposed",
            "return_value": 1,
            "delay_profile": [0, 1, 1, 2],
            "lut_cost": 2,
            "algorithm_ns": 1,
            "n_vars": n_vars,
            "lut_size": 4,
        },
        expected_selected_document=document,
    )
    assert result["status"] == "incompatible"
    assert result["artifact"] is None
    assert result["byte_identical_to_expected_selected_artifact"] is None
