"""Audit harness correctness only; no benchmark or new confirmation inputs."""
from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("cm_time_ladder_under_test", HERE / "ladder_diagnostics.py")
ladder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ladder
SPEC.loader.exec_module(ladder)


def case_named(name):
    return next(case for case in ladder.cases() if case["id"] == name)


def expected_bytes(case, *, reverse=False):
    expression = ladder.serde.expr_from_json(json.loads(case["payload"]))
    truth = ladder.eval_expr_tt(expression, case["n"]).astype(np.uint8)
    if reverse:
        truth = truth.reshape((2,) * case["n"]).transpose(tuple(reversed(range(case["n"]))))
    return np.packbits(truth.reshape(-1), bitorder="little").tobytes()


@pytest.fixture(autouse=True)
def isolated_cache_and_defaults():
    before = ladder.ir.get_evaluation_defaults()
    ladder.clear_caches()
    try:
        yield
    finally:
        ladder.clear_caches()
        assert ladder.TRACE is None
        assert ladder.ir.get_evaluation_defaults() == before


def test_exclusive_nested_spans_conserve_wall_and_cpu(monkeypatch):
    wall = iter((0., 1., 3., 5.))
    cpu = iter((0., 1., 2., 4.))
    monkeypatch.setattr(ladder.time, "perf_counter", lambda: next(wall))
    monkeypatch.setattr(ladder.time, "process_time", lambda: next(cpu))
    tracer = ladder.ExclusiveTracer()
    result = tracer.call("outer", "outer", lambda: tracer.call("inner", "inner", lambda: 7))
    assert result == 7
    report = tracer.record({"wall_s": 5., "cpu_s": 4.})
    assert report["exclusive_phases"]["outer"]["wall_s"] == 3.
    assert report["exclusive_phases"]["inner"]["wall_s"] == 2.
    assert report["exclusive_phases"]["outer"]["cpu_s"] == 3.
    assert report["exclusive_phases"]["inner"]["cpu_s"] == 1.
    assert sum(row["wall_s"] for row in report["exclusive_phases"].values()) == 5.
    assert sum(row["cpu_s"] for row in report["exclusive_phases"].values()) == 4.
    assert sum(row["percent_of_phase_pass_caller_wall"] for row in report["exclusive_phases"].values()) == 100.
    assert not tracer.stack


def test_recursive_same_phase_does_not_double_count(monkeypatch):
    wall = iter((0., 1., 2., 3., 4., 5.))
    cpu = iter((0., 1., 2., 3., 4., 5.))
    monkeypatch.setattr(ladder.time, "perf_counter", lambda: next(wall))
    monkeypatch.setattr(ladder.time, "process_time", lambda: next(cpu))
    tracer = ladder.ExclusiveTracer()
    def recur(depth):
        return depth if not depth else tracer.call("recursion", "recur", recur, depth - 1)
    assert tracer.call("recursion", "recur", recur, 2) == 0
    assert tracer.phases["recursion"]["calls"] == 3
    assert tracer.phases["recursion"]["wall_s"] == 5.
    assert tracer.helpers["recur"]["inclusive_wall_s"] == 9.


def test_exception_restores_static_descriptors_and_module_functions():
    original_static = inspect.getattr_static(ladder.ir.CMIRBuilder, "_shared_assoc_uids")
    original_compile = ladder.ir.compile_expr_to_cm_ir
    original_eval = ladder.bb.eval_cm_node_flat
    with pytest.raises(RuntimeError, match="intentional"):
        with ladder.ExclusiveTracer() as tracer:
            patched_static = inspect.getattr_static(ladder.ir.CMIRBuilder, "_shared_assoc_uids")
            assert isinstance(original_static, staticmethod)
            assert isinstance(patched_static, staticmethod)
            assert patched_static is not original_static
            assert ladder.ir.CMIRBuilder._shared_assoc_uids(ladder.Var(0))[0]
            tracer.call("failure", "raiser", lambda: (_ for _ in ()).throw(RuntimeError("intentional")))
    assert inspect.getattr_static(ladder.ir.CMIRBuilder, "_shared_assoc_uids") is original_static
    assert ladder.ir.compile_expr_to_cm_ir is original_compile
    assert ladder.bb.eval_cm_node_flat is original_eval
    assert not tracer.stack
    assert tracer.phases["failure"]["calls"] == 1
    assert ladder.TRACE is None


def test_nested_global_scope_rejection_preserves_outer_scope():
    with ladder.ExclusiveTracer() as tracer:
        patched = ladder.bb.eval_expr_bitset
        with pytest.raises(RuntimeError, match="nested global"):
            with ladder.ExclusiveTracer():
                pass
        assert ladder.TRACE is tracer
        assert ladder.bb.eval_expr_bitset is patched


@pytest.mark.parametrize("case_id", [
    "shared-h", "equal-separate-h", "single-consumer-chain-k12",
    "random-existing-k16", "fixed-structure-output-k18",
])
def test_all_ladder_arms_deliver_exact_same_complete_bytes(case_id):
    case = case_named(case_id)
    expected = expected_bytes(case)
    for arm in ladder.ARMS:
        session = ladder.Session(case, arm)
        assert session.run(expected, setup=True) == expected
        assert session.run(expected, setup=False, q=2) == expected


def test_common_executor_has_identical_mask_and_basis_for_cm_and_cse():
    case = case_named("shared-h")
    expected = expected_bytes(case, reverse=True)
    sessions = [ladder.Session(case, arm) for arm in ("occurrence_flat", "cse_flat", "cm_common_flat")]
    for session in sessions:
        session.names = tuple(reversed(session.names))
        session.setup()
    assert all(type(s.prepared) is ladder.bb.PreparedFlatEvaluation for s in sessions)
    assert len({s.prepared.full_mask for s in sessions}) == 1
    masks = []
    for session in sessions:
        masks.append({name: session.prepared.template[slot]
                      for slot, kind, name in session.prog.loads if kind == "var"})
        assert session.run(expected, setup=False) == expected
    assert masks[0] == masks[1] == masks[2]


def test_public_diagnostics_branch_is_not_silently_enabled_by_tracer(monkeypatch):
    case = case_named("shared-h")
    expected = expected_bytes(case)
    init_calls = []
    original = ladder.ir._init_final_output_diagnostics
    def track_init(diag):
        init_calls.append(diag)
        return original(diag)
    monkeypatch.setattr(ladder.ir, "_init_final_output_diagnostics", track_init)
    normal = ladder.Session(case, "public_cm")
    normal.run(expected, setup=True)
    assert normal.last_diag is None
    assert init_calls == []
    with ladder.ExclusiveTracer():
        normal.run(expected, setup=False)
    assert normal.last_diag is None
    assert init_calls == []
    diagnosed = ladder.Session(case, "public_cm_diag")
    with ladder.ExclusiveTracer():
        diagnosed.run(expected, setup=True)
    assert diagnosed.last_diag["ir_timing_enabled"] == 1
    assert len(init_calls) == 1


def test_public_alias_kernel_is_attributed_after_module_import_warmup():
    case = case_named("shared-h")
    expected = expected_bytes(case)
    session = ladder.Session(case, "public_cm")
    session.run(expected, setup=True)  # imports engine selector before tracer patches
    with ladder.ExclusiveTracer() as tracer:
        session.run(expected, setup=False)
    assert tracer.phases["kernel_and_intermediate_allocation_release"]["calls"] >= 1
    assert tracer.phases["public_wrapper_lifecycle"]["calls"] == 1


def test_public_explicit_flags_preserve_unrelated_process_defaults():
    case = case_named("shared-h")
    expected = expected_bytes(case)
    for flat, words in ((False, False), (False, True), (True, False), (True, True)):
        with ladder.ir.evaluation_defaults_scope(flat_eval=flat, words_eval=words):
            current = ladder.ir.get_evaluation_defaults()
            for arm in ("public_cm", "public_cm_diag", "cm_common_flat"):
                session = ladder.Session(case, arm)
                assert session.run(expected, setup=True) == expected
            assert ladder.ir.get_evaluation_defaults() == current


def test_dense_output_metadata_uses_delivered_dense_bytes():
    case = case_named("fixed-structure-output-k4")
    expression = ladder.serde.expr_from_json(json.loads(case["payload"]))
    dense = ladder.eval_expr_tt(expression, case["n"]).astype(np.uint8).reshape(-1).tobytes()
    session = ladder.Session(case, "dense_cm")
    assert session.run(dense, setup=True) == dense
    metrics = ladder.graph_metrics(session)
    assert metrics["delivered_bytes"] == len(dense)
