"""Resource admission and same-native-arena ownership regressions."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import threading
import time

import numpy as np
import pytest

import cm_ir
from cm_exprlib import And, Or, Not, Var, Xor
from cmbench.output_budget import OutputBudget, OutputBudgetExceeded, decide_output_budget, estimate_explicit_output
from cmbench.comparative.gf2_native_slots import (
    NativeSlotLibrary, compile_native_slot_arena, compile_native_multi_root_arena)


def mixed_node():
    p = Var(0)
    for i in range(1, 6):
        p = Xor(p, Var(i))
    return cm_ir.compile_expr_to_cm_ir(Or(And(p, Var(6)), And(Not(p), Var(7))))


def test_dense_admission_counts_memo_payload_before_backend():
    node = mixed_node()
    budget = OutputBudget(max_temporary_bytes=512)
    with patch.object(cm_ir, "_materialize_ir_tagged", side_effect=AssertionError("backend called")):
        with pytest.raises(OutputBudgetExceeded) as failure:
            cm_ir.materialize_cm(node, [f"x{i}" for i in range(4)], [f"x{i}" for i in range(4, 8)],
                materialize_mode="numpy", output_budget=budget)
    assert failure.value.decision.estimate.temporary_bytes > 512
    assert failure.value.decision.estimate.estimation_method == "cm_support_payload_v1"


@pytest.mark.parametrize("fixed", [{}, {"x0": 0, "x1": 1}])
def test_support_estimate_counts_dag_once_and_folds_fixed_axes(fixed):
    node = mixed_node()
    seen, stack, expected = set(), [node], 0
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        expected += 1 << sum(v not in fixed for v in cur.vars)
        stack.extend(cur.args)
    estimate = cm_ir.estimate_cm_output(node, 8, "dense_bool", fixed=fixed, materialize_mode="numpy")
    assert estimate.retained_array_bytes == expected
    assert estimate.temporary_bytes == expected + 2 * 256
    assert estimate.output_bytes == 256


def test_reserve_is_validated_added_once_and_can_refuse():
    original = estimate_explicit_output(4, "dense_bool")
    budget = OutputBudget(max_temporary_bytes=40, working_memory_reserve_bytes=9)
    first = decide_output_budget(budget, original)
    assert not first.allowed
    assert first.estimate.temporary_bytes == 41
    assert first.estimate.reserve_bytes == 9
    assert decide_output_budget(budget, first.estimate).estimate.temporary_bytes == 41
    assert budget.with_overrides(max_output_vars=4).working_memory_reserve_bytes == 9
    with pytest.raises(ValueError):
        OutputBudget(working_memory_reserve_bytes=-1)


@pytest.mark.parametrize("flat_fast", [False, True])
def test_no_reinflate_uses_identical_admission_on_fast_and_instrumented_paths(flat_fast):
    node = cm_ir.compile_expr_to_cm_ir(Var(0))
    diag = {} if not flat_fast else None
    budget = OutputBudget(max_temporary_bytes=1, working_memory_reserve_bytes=10)
    with pytest.raises(OutputBudgetExceeded) as failure:
        cm_ir.materialize_hybrid_no_reinflate(node, ["x0"], flat_eval=True,
            flat_fast_path=flat_fast, diagnostics=diag, output_budget=budget)
    assert failure.value.decision.estimate.reserve_bytes == 10
    assert failure.value.decision.estimate.estimation_method == "cm_support_payload_v1"


@pytest.mark.parametrize("kind", ["scalar", "multi"])
def test_same_arena_concurrent_result_ownership_and_failure_recovery(kind):
    state = dict(active=0, maximum=0, fail=False, status=0)
    state_lock = threading.Lock()
    def call(*args):
        binding_index = 6 if kind == "scalar" else 7
        with state_lock:
            state["active"] += 1
            state["maximum"] = max(state["maximum"], state["active"])
        try:
            if state["fail"]:
                raise RuntimeError("injected native exception")
            if state["status"]:
                return state["status"]
            value = int(args[binding_index][0])
            args[-1][0] = value
            if kind == "multi":
                args[-1][1] = 1 - value
            time.sleep(0.01)  # Stand-in for a GIL-releasing native call.
            return 0
        finally:
            with state_lock:
                state["active"] -= 1
    class Handle:
        cm_fused_slots_eval = staticmethod(call)
        cm_fused_slots_eval_multi = staticmethod(call)
    library = NativeSlotLibrary(Path("fake"), "fake", 1, True, Handle())
    nodes = [{"op": "var", "i": 0}]
    if kind == "multi":
        nodes.append({"op": "not", "a": 0})
    arena = (compile_native_slot_arena({"version": 2, "nodes": nodes, "root": 0}, library, variable_count=1)
        if kind == "scalar" else compile_native_multi_root_arena({"version": 2, "nodes": nodes, "roots": [0, 1]}, library, variable_count=1))
    def evaluate(index):
        result = arena.evaluate(np.array([index % 2], dtype=np.int16), 2)
        if kind == "multi":
            assert result[1] == 1 - index % 2
        return result if kind == "scalar" else result[0]
    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(evaluate, range(12))) == [i % 2 for i in range(12)]
    assert state["maximum"] == 1
    state["fail"] = True
    with pytest.raises(RuntimeError, match="injected"):
        evaluate(0)
    state["fail"] = False
    with ThreadPoolExecutor(max_workers=1) as executor:
        assert executor.submit(evaluate, 1).result(timeout=2) == 1
    state["status"] = 17
    with pytest.raises(RuntimeError, match="status 17"):
        evaluate(0)
    state["status"] = 0
    with ThreadPoolExecutor(max_workers=1) as executor:
        assert executor.submit(evaluate, 1).result(timeout=2) == 1


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_analytical_dense_payload_limit_neighbors(delta):
    node = cm_ir.compile_expr_to_cm_ir(Xor(Var(0), Var(1)))
    # Three retained arrays (2 + 2 + 4 bytes), plus two ambient 8-byte buffers.
    budget = OutputBudget(max_temporary_bytes=24 + delta)
    if delta < 0:
        with pytest.raises(OutputBudgetExceeded):
            cm_ir.materialize_cm(node, ["x0"], ["x1", "padding"], materialize_mode="numpy", output_budget=budget)
    else:
        result = cm_ir.materialize_cm(node, ["x0"], ["x1", "padding"], materialize_mode="numpy", output_budget=budget)
        np.testing.assert_array_equal(result, [[0, 0, 1, 1], [1, 1, 0, 0]])


@pytest.mark.parametrize("value", [-1, True, None, 1.5, "10"])
def test_reserve_rejects_malformed_values(value):
    with pytest.raises(ValueError):
        OutputBudget(working_memory_reserve_bytes=value)


def test_reduced_admission_keeps_reserve_and_provenance():
    node = cm_ir.compile_expr_to_cm_ir(Var(0))
    reserve = 1234
    reduced = cm_ir.estimate_cm_output(node, 1, "packed_bitset")
    budget = OutputBudget(max_output_bytes=1, max_temporary_bytes=reduced.temporary_bytes + reserve,
        allow_reduced_output=True, working_memory_reserve_bytes=reserve)
    diag = {}
    result = cm_ir.materialize_hybrid_no_reinflate(node, [f"x{i}" for i in range(32)],
        flat_eval=True, allow_reduced_output=True, diagnostics=diag, output_budget=budget)
    assert result.bits == 2 and result.output_vars == ("x0",)
    assert result.budget_decision.estimate.reserve_bytes == reserve
    assert diag["output_budget_estimation_method"] == "cm_support_payload_v1"
    assert diag["output_budget_estimation_scope"] == "payload_plus_selected_reserve_not_rss"


@pytest.mark.parametrize("representation", ["dense_bool", "packed_bitset", "truth_table_uint8"])
def test_resource_width_cannot_omit_live_support(representation):
    node = cm_ir.compile_expr_to_cm_ir(Xor(Var(0), Var(1)))
    with pytest.raises(ValueError, match="live node support"):
        cm_ir.estimate_cm_output(node, 1, representation)
