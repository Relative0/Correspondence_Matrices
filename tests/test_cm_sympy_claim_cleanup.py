from __future__ import annotations

import json
from pathlib import Path

import pytest

from cmbench.comparative.sympy_cm_claim_cleanup import (
    ASSIGNMENT_GENERATOR,
    arms_for,
    assignment_rows,
    build_contracts,
    execute_worker,
    pack_values,
    sha256_bytes,
    validate_inputs,
)


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "docs" / "audits" / "2026-09-15-cm-sympy-claim-cleanup" / "FROZEN_INPUTS.json"


def load_inputs():
    return json.loads(INPUTS.read_text(encoding="utf-8"))


def test_packing_contract_places_first_assignment_in_low_bit() -> None:
    assert pack_values([1, 0, 1, 0, 0, 0, 0, 1]) == b"\x85"
    with pytest.raises(ValueError):
        pack_values([0, 2])


def test_frozen_assignment_generator_is_exact_and_stable() -> None:
    spec = {
        "algorithm": ASSIGNMENT_GENERATOR,
        "rows": 4096,
        "multiplier": 2654435761,
        "offset": 1013904223,
        "shift": 13,
    }
    raw = assignment_rows(spec, 8)
    assert len(raw) == 32768
    assert sha256_bytes(raw) == "822c6e987b22f1298414feebe7299d4d9376364c6a2a8f0b0a2438185c935e00"


def test_frozen_inputs_and_contracts_cover_y02_through_y05() -> None:
    document = load_inputs()
    validate_inputs(document)
    contracts = build_contracts(document)
    assert {contract["family"] for contract, _ in contracts} == {"Y02", "Y03", "Y04", "Y05"}
    assert {contract["task"] for contract, _ in contracts} == {
        "complete_relation",
        "assignment_batch",
        "sat_status",
        "equivalence_status",
        "simplified_expression",
    }
    assert all(len(contract["variables"]) <= 8 for contract, _ in contracts)


@pytest.mark.parametrize(
    "task",
    [
        "complete_relation",
        "assignment_batch",
        "sat_status",
        "equivalence_status",
        "simplified_expression",
    ],
)
def test_every_arm_matches_one_shared_task_contract(task: str) -> None:
    document = load_inputs()
    contract, case = next(
        (contract, case)
        for contract, case in build_contracts(document)
        if contract["task"] == task
    )
    rows = []
    for arm in arms_for(contract):
        row = execute_worker({
            "contract": contract,
            "case": case,
            "arm": arm,
            "repetition": 0,
            "assignment_generator": document["assignment_generator"],
        })
        assert row["status"] == "ok", row
        assert row["validation"]["matches_oracle"] is True
        rows.append(row)
    assert len({row["contract_sha256"] for row in rows}) == 1
    if task != "simplified_expression":
        assert len({row["artifact"]["sha256"] for row in rows}) == 1
    else:
        assert all(row["artifact"]["semantic_sha256"] == contract["artifact"]["semantic_sha256"] for row in rows)
        assert all(row["quality"]["literal_occurrences"] >= 0 for row in rows)


def test_input_bounds_fail_closed() -> None:
    document = load_inputs()
    document["cases"][0]["n_vars"] = 9
    with pytest.raises(ValueError):
        validate_inputs(document)


def test_completed_audit_manifest_and_ledger_are_consistent() -> None:
    audit = INPUTS.parent
    manifest = json.loads((audit / "AUDIT_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["complete"] is True
    for record in manifest["files"]:
        payload = (audit / record["path"]).read_bytes()
        assert len(payload) == record["bytes"]
        assert sha256_bytes(payload) == record["sha256"]

    binding = json.loads((audit / "SOURCE_BINDING.json").read_text(encoding="utf-8"))
    for record in binding["source_bindings"]:
        assert record["verified"] is True
        assert sha256_bytes((ROOT / record["path"]).read_bytes()) == record["sha256"]
    assert sha256_bytes(INPUTS.read_bytes()) == binding["inputs"]["sha256"]

    rows = [json.loads(line) for line in (audit / "LEDGER.jsonl").read_text(encoding="ascii").splitlines()]
    assert len(rows) == 186
    assert {row["status"] for row in rows} == {"ok"}
    grouped = {}
    for row in rows:
        grouped.setdefault(row["contract_sha256"], []).append(row)
        assert row["validation"]["matches_oracle"] is True
        if row["task"] == "simplified_expression":
            assert row["artifact"]["semantic_sha256"]
    assert all(len({row["repetition"] for row in group}) == 3 for group in grouped.values())
    for group in grouped.values():
        if group[0]["task"] != "simplified_expression":
            assert len({row["artifact"]["sha256"] for row in group}) == 1
