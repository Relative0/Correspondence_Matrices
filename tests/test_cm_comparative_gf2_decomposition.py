from __future__ import annotations

import copy

import pytest

from cmbench.comparative.contracts import ContractError, validate_contract, validate_result
from cmbench.comparative.gf2_decomposition import (
    ARMS, decomposition_contract, delivered_sha256, execute_decomposition_arm)
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2
from cmbench.recognition.gf2_task_dispatcher import freeze_gf2_dispatch_policy


def fixture_bits() -> int:
    # f(x0,x1,x2,x3) = (x0 & x1) XOR (x2 | x3)
    value = 0
    for assignment in range(16):
        x0, x1, x2, x3 = ((assignment >> shift) & 1 for shift in (3, 2, 1, 0))
        value |= ((x0 & x1) ^ (x2 | x3)) << assignment
    return value


def test_all_f1_gf2_arms_deliver_same_exact_artifact() -> None:
    bits = fixture_bits()
    exhaustive = analyze_exact_gf2(bits, 4, max_partitions=64)
    best = exhaustive.best.to_dict() if exhaustive.best else None
    contract = decomposition_contract(
        contract_id="gf2-fixture", n_vars=4,
        required_output_sha256=delivered_sha256(best))
    policy = freeze_gf2_dispatch_policy()
    results = [execute_decomposition_arm(
        bits=bits, contract=contract, case_id="fixture", arm=arm,
        policy=policy if "c17" in arm else None) for arm in sorted(ARMS)]
    assert {row["artifact"]["sha256"] for row in results} == {delivered_sha256(best)}
    assert all(row["identity"]["best_artifact"] == best for row in results)
    assert {row["identity"]["selected_exact_arm"] for row in results} == {
        "explicit_cm_exhaustive", "explicit_cm_screened"}


def test_decomposition_contract_cannot_masquerade_as_count_or_relation() -> None:
    contract = decomposition_contract(contract_id="gf2", n_vars=4,
                                      required_output_sha256=None)
    changed = copy.deepcopy(contract)
    changed["task"] = "exact_count"
    with pytest.raises(ContractError):
        validate_contract(changed)
    changed = copy.deepcopy(contract)
    changed["artifact"]["kind"] = "packed_bigint"
    with pytest.raises(ContractError):
        validate_contract(changed)


def test_result_digest_tamper_is_refused() -> None:
    bits = fixture_bits()
    best = analyze_exact_gf2(bits, 4).best
    contract = decomposition_contract(
        contract_id="gf2", n_vars=4,
        required_output_sha256=delivered_sha256(best.to_dict() if best else None))
    result = execute_decomposition_arm(
        bits=bits, contract=contract, case_id="fixture", arm="gf2_screened")
    changed = copy.deepcopy(result)
    changed["artifact"]["sha256"] = "0" * 64
    with pytest.raises(ContractError):
        validate_result(changed, contract)
