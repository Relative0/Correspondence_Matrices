"""Tiny deterministic checks for the additive SymPy/CM worker timing schema."""

from itertools import count
import json

import pytest

from cmbench.comparative import sympy_cm_claim_cleanup as cleanup


def _document():
    left = {
        "op": "imp",
        "args": [
            {
                "op": "and",
                "args": [{"op": "var", "index": 0}, {"op": "var", "index": 1}],
            },
            {
                "op": "or",
                "args": [{"op": "var", "index": 2}, {"op": "var", "index": 3}],
            },
        ],
    }
    return {
        "schema": cleanup.SCHEMA,
        "cases": [{
            "case_id": "tiny",
            "n_vars": 4,
            "expression": left,
            "families": ["Y02", "Y03", "Y04", "Y05"],
            "comparison_expression": dict(left),
            "simplification_forms": ["dnf", "cnf"],
        }],
        "assignment_generator": {
            "algorithm": cleanup.ASSIGNMENT_GENERATOR,
            "rows": 4,
            "multiplier": 3,
            "offset": 1,
            "shift": 1,
        },
    }


def _requests():
    document = _document()
    arm = {
        "complete_relation": "sympy_truth_table",
        "assignment_batch": "sympy_lambdify_cse_off",
        "sat_status": "sympy_satisfiable",
        "equivalence_status": "sympy_difference_sat",
        "simplified_expression": "sympy_simplify_default",
    }
    return [
        {
            "contract": contract,
            "case": case,
            "arm": arm[contract["task"]],
            "repetition": 0,
            "assignment_generator": document["assignment_generator"],
        }
        for contract, case in cleanup.build_contracts(document)
    ]


def _clock(step=10):
    ticks = count(0, step)
    return lambda: next(ticks)


def _all_arm_cases():
    cases = []
    for request in _requests():
        for arm in cleanup.arms_for(request["contract"]):
            item = {**request, "arm": arm}
            form = request["contract"]["artifact"]["form"] or "none"
            cases.append(pytest.param(
                item,
                id=f"{request['contract']['task']}-{form}-{arm}",
            ))
    return cases


@pytest.mark.parametrize("worker_case", _requests(), ids=lambda item: item["contract"]["task"])
def test_worker_timing_v2_is_additive_and_preserves_v1_result(worker_case):
    row = cleanup.execute_worker(worker_case, clock=_clock())

    assert row["schema"] == cleanup.RESULT_SCHEMA
    assert row["status"] == "ok"
    assert "task_total_ns" in row["timings_ns"]
    timing = row["timing_v2"]
    assert json.loads(cleanup.canonical_bytes(row)) == row
    cleanup.validate_worker_timing(timing)
    assert timing["schema"] == cleanup.TIMING_SCHEMA
    assert timing["input_preparation_ns"] > 0
    assert timing["execution_delivery_ns"] > 0
    assert timing["independent_validation_ns"] > 0
    assert timing["full_worker_ns"] >= timing["execution_delivery_ns"]


@pytest.mark.parametrize("worker_case", _all_arm_cases())
def test_every_arm_matches_the_tiny_shared_contract(worker_case):
    row = cleanup.execute_worker(worker_case, clock=_clock())

    assert row["status"] == "ok", row
    assert row["validation"]["matches_oracle"] is True
    cleanup.validate_worker_timing(row["timing_v2"])


def test_equivalence_parses_both_inputs_inside_the_same_preparation_phase(monkeypatch):
    requests = {request["contract"]["task"]: request for request in _requests()}
    original = cleanup.parse_expression

    def clocked_parse(spec):
        cleanup._clock_ns()
        return original(spec)

    monkeypatch.setattr(cleanup, "parse_expression", clocked_parse)
    complete = cleanup.execute_worker(requests["complete_relation"], clock=_clock())
    equivalent = cleanup.execute_worker(requests["equivalence_status"], clock=_clock())

    assert (
        equivalent["timing_v2"]["input_preparation_ns"]
        > complete["timing_v2"]["input_preparation_ns"]
    )


def test_sat_oracle_work_is_accounted_only_as_independent_validation(monkeypatch):
    request = next(
        item for item in _requests() if item["contract"]["task"] == "sat_status"
    )
    baseline = cleanup.execute_worker(request, clock=_clock())
    original = cleanup.scalar_truth_values

    def clocked_oracle(expr, n_vars):
        cleanup._clock_ns()
        cleanup._clock_ns()
        return original(expr, n_vars)

    monkeypatch.setattr(cleanup, "scalar_truth_values", clocked_oracle)
    row = cleanup.execute_worker(request, clock=_clock())
    timing = row["timing_v2"]

    assert timing["execution_delivery_ns"] == baseline["timing_v2"]["execution_delivery_ns"]
    assert timing["independent_validation_ns"] == (
        baseline["timing_v2"]["independent_validation_ns"] + 20
    )
    assert timing["full_worker_ns"] == baseline["timing_v2"]["full_worker_ns"] + 20
    cleanup.validate_worker_timing(timing)


def test_required_delivery_delay_is_in_execution_delivery_and_full_only(monkeypatch):
    request = next(
        item for item in _requests() if item["contract"]["task"] == "complete_relation"
    )
    baseline = cleanup.execute_worker(request, clock=_clock())
    original = cleanup.pack_values

    def clocked_delivery(values):
        cleanup._clock_ns()
        cleanup._clock_ns()
        return original(values)

    monkeypatch.setattr(cleanup, "pack_values", clocked_delivery)
    row = cleanup.execute_worker(request, clock=_clock())

    assert row["timing_v2"]["execution_delivery_ns"] == (
        baseline["timing_v2"]["execution_delivery_ns"] + 20
    )
    assert row["timing_v2"]["independent_validation_ns"] == (
        baseline["timing_v2"]["independent_validation_ns"]
    )
    assert row["timing_v2"]["full_worker_ns"] == (
        baseline["timing_v2"]["full_worker_ns"] + 20
    )


def test_injected_clock_context_restores_after_worker_failure():
    request = dict(_requests()[0])
    request["arm"] = "unknown"
    before = cleanup._WORKER_CLOCK.get()
    with pytest.raises(ValueError, match="unknown complete-relation arm"):
        cleanup.execute_worker(request, clock=_clock())
    assert cleanup._WORKER_CLOCK.get() is before


def test_injected_clock_context_restores_after_evaluator_failure(monkeypatch):
    request = next(
        item for item in _requests() if item["contract"]["task"] == "complete_relation"
    )
    before = cleanup._WORKER_CLOCK.get()

    def fail(*_args):
        raise RuntimeError("evaluator failure sentinel")

    monkeypatch.setattr(cleanup, "_sympy_truth", fail)
    with pytest.raises(RuntimeError, match="evaluator failure sentinel"):
        cleanup.execute_worker(request, clock=_clock())
    assert cleanup._WORKER_CLOCK.get() is before


def test_sat_false_and_inequivalent_pair_have_exact_validation():
    var0 = {"op": "var", "index": 0}
    false_expr = {"op": "and", "args": [var0, {"op": "not", "args": [var0]}]}
    document = {
        "schema": cleanup.SCHEMA,
        "cases": [{
            "case_id": "false-and-inequivalent",
            "n_vars": 4,
            "expression": false_expr,
            "families": ["Y04"],
            "comparison_expression": {"op": "var", "index": 1},
            "simplification_forms": [],
        }],
        "assignment_generator": _document()["assignment_generator"],
    }
    contracts = cleanup.build_contracts(document)
    rows = {}
    selected = {
        "sat_status": "sympy_satisfiable",
        "equivalence_status": "sympy_difference_sat",
    }
    for contract, case in contracts:
        rows[contract["task"]] = cleanup.execute_worker({
            "contract": contract,
            "case": case,
            "arm": selected[contract["task"]],
            "repetition": 0,
            "assignment_generator": document["assignment_generator"],
        }, clock=_clock())

    assert rows["sat_status"]["artifact"]["value"] is False
    assert rows["equivalence_status"]["artifact"]["value"] is False
    assert all(row["validation"]["matches_oracle"] for row in rows.values())


def test_both_simplification_forms_deliver_quality_and_semantic_validation():
    rows = []
    for request in _requests():
        if request["contract"]["task"] == "simplified_expression":
            rows.append(cleanup.execute_worker(request, clock=_clock()))

    assert {row["artifact"]["form"] for row in rows} == {"dnf", "cnf"}
    assert all(row["artifact"]["semantic_sha256"] for row in rows)
    assert all(row["quality"]["srepr_bytes"] > 0 for row in rows)
    assert all(row["validation"]["matches_oracle"] for row in rows)


def test_assignment_generator_is_fully_delivered_and_scalar_broadcast_is_matched():
    request = next(
        item for item in _requests() if item["contract"]["task"] == "assignment_batch"
    )
    row = cleanup.execute_worker(request, clock=_clock())
    raw = cleanup.assignment_rows(request["assignment_generator"], 4)

    assert row["validation"]["assignment_sha256"] == cleanup.sha256_bytes(raw)
    assert cleanup._normalize_vector(True, 4) == [1, 1, 1, 1]
    assert cleanup._normalize_vector(False, 4) == [0, 0, 0, 0]


def test_shared_k6_fixture_round_trips_under_new_timing_schema():
    def var(index):
        return {"op": "var", "index": index}

    h = {
        "op": "xor",
        "args": [{
            "op": "xor",
            "args": [{"op": "xor", "args": [var(0), var(1)]}, var(2)],
        }, var(3)],
    }
    expression = {
        "op": "and",
        "args": [
            {"op": "xor", "args": [h, var(4)]},
            {"op": "xor", "args": [h, var(5)]},
        ],
    }
    document = {
        "schema": cleanup.SCHEMA,
        "cases": [{
            "case_id": "shared-k6",
            "n_vars": 6,
            "expression": expression,
            "families": ["Y02"],
            "comparison_expression": None,
            "simplification_forms": [],
        }],
        "assignment_generator": _document()["assignment_generator"],
    }
    contract, case = cleanup.build_contracts(document)[0]
    row = cleanup.execute_worker({
        "contract": contract,
        "case": case,
        "arm": "cm_packed",
        "repetition": 0,
        "assignment_generator": document["assignment_generator"],
    }, clock=_clock())

    assert row["status"] == "ok"
    cleanup.validate_worker_timing(row["timing_v2"])


def test_mismatch_is_terminal_and_validation_exception_returns_no_success(monkeypatch):
    request = next(
        item for item in _requests() if item["contract"]["task"] == "complete_relation"
    )
    mismatched = {**request, "contract": {
        **request["contract"],
        "artifact": {**request["contract"]["artifact"], "semantic_sha256": "0" * 64},
    }}
    row = cleanup.execute_worker(mismatched, clock=_clock())
    assert row["status"] == "mismatch"
    assert row["validation"]["matches_oracle"] is False

    sat_request = next(
        item for item in _requests() if item["contract"]["task"] == "sat_status"
    )
    before = cleanup._WORKER_CLOCK.get()

    def fail_validation(*_args):
        raise RuntimeError("validation failure sentinel")

    monkeypatch.setattr(cleanup, "scalar_truth_values", fail_validation)
    with pytest.raises(RuntimeError, match="validation failure sentinel"):
        cleanup.execute_worker(sat_request, clock=_clock())
    assert cleanup._WORKER_CLOCK.get() is before
