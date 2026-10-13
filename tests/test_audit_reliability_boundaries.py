"""Bounded regressions for audit findings F04, F07 and F08."""
import hashlib
import inspect
import sys
import threading
from concurrent.futures import Future
from unittest.mock import patch

import numpy as np
import pytest

import cm_ir
import cm_parallel
from cm_exprlib import And, Or, Xor, Not, Var, Imp, Eqv, random_expr


def legacy_hash(e):
    h = hashlib.blake2b(digest_size=16)
    if isinstance(e, Var):
        h.update(b"VAR:" + f"x{e.i}".encode())
    elif isinstance(e, Not):
        h.update(b"NOT:" + legacy_hash(e.a))
    elif isinstance(e, (And, Or, Xor)):
        parts, stack = [], [e]
        while stack:
            node = stack.pop()
            if isinstance(node, type(e)):
                stack.extend((node.a, node.b))
            else:
                parts.append(legacy_hash(node))
        h.update({And: b"AND:", Or: b"OR:", Xor: b"XOR:"}[type(e)])
        for part in sorted(parts):
            h.update(part)
    else:
        parts = [legacy_hash(e.a), legacy_hash(e.b)]
        if isinstance(e, Eqv):
            parts.sort()
        h.update(b"EQV:" if isinstance(e, Eqv) else b"IMP:")
        for part in parts:
            h.update(part)
    return h.digest()


def shared(depth, op=Or):
    e = Var(0)
    for _ in range(depth):
        e = op(e, e)
    return e


def test_hash_legacy_compatibility():
    rng = np.random.default_rng(441)
    for _ in range(100):
        e = random_expr(5, rng, max_depth=5)
        assert cm_ir.expr_structural_hash(e) == legacy_hash(e).hex()
    for op in (And, Or, Xor):
        assert cm_ir.expr_structural_hash(shared(12, op)) == legacy_hash(shared(12, op)).hex()
        assert cm_ir.expr_structural_hash(op(Var(0), Var(0))) != cm_ir.expr_structural_hash(Var(0))


def test_hash_rejects_expanded_work_before_digest():
    with patch.object(cm_ir.hashlib, "blake2b", wraps=hashlib.blake2b) as digest:
        with pytest.raises(ValueError, match="hash.*work"):
            cm_ir.expr_structural_hash(shared(40))
        assert digest.call_count <= 2


def test_hash_deep_input_has_explicit_admission():
    e = Var(0)
    for _ in range(1200):
        e = Not(e)
    with pytest.raises(ValueError, match="depth"):
        cm_ir.expr_structural_hash(e)


def test_node_count_shared_and_deep():
    assert cm_parallel.count_expr_nodes(shared(40)) == (1 << 41) - 1
    e = Var(0)
    for _ in range(1200):
        e = Not(e)
    assert cm_parallel.count_expr_nodes(e) == 1201


def test_associative_graph_visit_count():
    # Count traversal work, not elapsed time: 13 distinct nodes versus 8191
    # unfolded occurrences. Two stack events per distinct node, plus shared edges.
    lines, start = inspect.getsourcelines(cm_ir._structural_digest)
    visit_line = start + next(i for i, line in enumerate(lines) if "z, ready = stack.pop()" in line)
    visits = 0
    def trace(frame, event, arg):
        nonlocal visits
        if event == "line" and frame.f_code is cm_ir._structural_digest.__code__ and frame.f_lineno == visit_line:
            visits += 1
        return trace
    previous = sys.gettrace()
    try:
        sys.settrace(trace)
        cm_ir.expr_structural_hash(shared(12))
    finally:
        sys.settrace(previous)
    assert visits == 38


def test_hash_node_admission_and_cycles():
    with patch.object(cm_ir, "_STRUCTURAL_HASH_MAX_NODES", 2):
        with pytest.raises(ValueError, match="node limit"):
            cm_ir.expr_structural_hash(And(Var(0), Var(1)))
    e = Not(Var(0))
    object.__setattr__(e, "a", e)
    for fn in (cm_ir.expr_structural_hash, cm_parallel.count_expr_nodes):
        with pytest.raises(ValueError, match="acyclic"):
            fn(e)


class Memory:
    def __init__(self, index, events):
        self.name = str(index)
        self.buf = bytearray(4)
        self.events = events
    def close(self):
        self.events.append((self.name, "close"))
    def unlink(self):
        self.events.append((self.name, "unlink"))


@pytest.mark.parametrize("fail_at", [1, 2, 3])
@pytest.mark.parametrize("worker", [False, True])
def test_partial_shared_memory_cleanup(fail_at, worker):
    events, allocated = [], []
    def allocate(**kwargs):
        if len(allocated) + 1 == fail_at:
            raise OSError("injected allocation/attachment failure")
        m = Memory(len(allocated), events)
        allocated.append(m)
        return m
    with patch.object(cm_parallel.shared_memory, "SharedMemory", side_effect=allocate):
        with pytest.raises(OSError):
            if worker:
                cm_parallel._combine_chunk_worker_shared("OR", "a", "b", "c", "|b1", 4, 0, 4)
            else:
                cm_parallel._combine_parallel_shared(np.zeros(4), np.ones(4), "OR", None,
                    chunk_ranges=[(0, 4)], out_shape=(4,), diagnostics=None)
    for m in allocated:
        assert (m.name, "close") in events
        assert ((m.name, "unlink") in events) == (not worker)


def test_submit_failure_settles_workers_before_cleanup():
    events = []
    memories = [Memory(i, events) for i in range(3)]
    future = Future()
    class Executor:
        calls = 0
        def submit(self, *args):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("injected submit failure")
            return future
    def settle(futures):
        assert not events
        assert future.cancelled()
        events.append(("workers", "settled"))
    with patch.object(cm_parallel.shared_memory, "SharedMemory", side_effect=memories), \
         patch.object(cm_parallel, "wait", side_effect=settle):
        with pytest.raises(RuntimeError, match="submit"):
            cm_parallel._combine_parallel_shared(np.zeros(4), np.ones(4), "OR", Executor(),
                chunk_ranges=[(0, 2), (2, 4)], out_shape=(4,), diagnostics=None)
    assert events[0] == ("workers", "settled")
    assert len(events) == 7


def test_failed_future_waits_for_running_worker():
    events, threads = [], []
    memories = [Memory(i, events) for i in range(3)]
    failed, running = Future(), Future()
    failed.set_exception(RuntimeError("worker failed"))
    running.set_running_or_notify_cancel()
    class Executor:
        calls = 0
        def submit(self, *args):
            self.calls += 1
            if self.calls == 1:
                return failed
            def finish():
                # Bounded stand-in for a worker still using owner memory.
                threading.Event().wait(0.03)
                assert not events
                events.append(("worker", "finished"))
                running.set_result(2)
            thread = threading.Thread(target=finish)
            threads.append(thread)
            thread.start()
            return running
    try:
        with patch.object(cm_parallel.shared_memory, "SharedMemory", side_effect=memories):
            with pytest.raises(RuntimeError, match="worker failed"):
                cm_parallel._combine_parallel_shared(np.zeros(4), np.ones(4), "OR", Executor(),
                    chunk_ranges=[(0, 2), (2, 4)], out_shape=(4,), diagnostics=None)
    finally:
        for thread in threads:
            thread.join(timeout=2)
    assert running.done()
    assert events[0] == ("worker", "finished")
    assert len(events) == 7


@pytest.mark.parametrize("worker", [False, True])
def test_setup_failure_closes_all_resources(worker):
    events = []
    memories = [Memory(i, events) for i in range(3)]
    with patch.object(cm_parallel.shared_memory, "SharedMemory", side_effect=memories), \
         patch.object(cm_parallel.np, "ndarray", side_effect=RuntimeError("view failed")):
        with pytest.raises(RuntimeError, match="view failed"):
            if worker:
                cm_parallel._combine_chunk_worker_shared("OR", "a", "b", "c", "|b1", 4, 0, 4)
            else:
                cm_parallel._combine_parallel_shared(np.zeros(4), np.ones(4), "OR", None,
                    chunk_ranges=[(0, 4)], out_shape=(4,), diagnostics=None)
    assert len(events) == (3 if worker else 6)


def test_cleanup_failure_still_attempts_all_buffers():
    events = []
    memories = [Memory(i, events) for i in range(3)]
    def failed_close():
        events.append(("2", "close"))
        raise OSError("close failed")
    memories[2].close = failed_close
    with patch.object(cm_parallel.shared_memory, "SharedMemory", side_effect=memories), \
         patch.object(cm_parallel.np, "ndarray", side_effect=RuntimeError("view failed")):
        with pytest.raises(OSError, match="close failed"):
            cm_parallel._combine_parallel_shared(np.zeros(4), np.ones(4), "OR", None,
                chunk_ranges=[(0, 4)], out_shape=(4,), diagnostics=None)
    assert len(events) == 6


@pytest.mark.parametrize("basis", [("x0", "x0"), ()])
@pytest.mark.parametrize("packed", [False, True])
def test_invalid_basis_before_evaluation(basis, packed):
    node = cm_ir.compile_expr_to_cm_ir(Var(0), reuse_cache=False)
    with patch.object(cm_ir, "_materialize_ir_tagged", side_effect=AssertionError("backend called")), \
         patch.object(cm_ir, "_cm_node_count", side_effect=AssertionError("budget called")):
        with pytest.raises(ValueError, match="basis"):
            if packed:
                cm_ir.materialize_hybrid_no_reinflate(node, basis, flat_eval=True)
            else:
                cm_ir.materialize_cm(node, basis, ())


def test_fixed_and_unused_basis_allowed():
    node = cm_ir.compile_expr_to_cm_ir(And(Var(0), Var(1)), reuse_cache=False)
    result = cm_ir.materialize_cm(node, ["padding"], ["x1"], fixed={"x0": 1})
    np.testing.assert_array_equal(result, [[0, 1], [0, 1]])


@pytest.mark.parametrize("expr", [Var(0), Var(2), Xor(Var(0), Var(2)),
    Imp(Var(1), Var(2)), Eqv(Var(0), Var(0)), Xor(Var(0), Var(0))])
@pytest.mark.parametrize("corrupt", [False, True])
def test_truth_bdd_validates_against_source(expr, corrupt):
    import cm_bench
    from cmbench.config import BenchmarkConfig
    config = BenchmarkConfig(sizes=(3,), trials=1, seed=1, max_depth=2,
        no_dd=True, no_robdd_dd=True, no_numba=True, no_espresso=True)
    original = cm_bench.cm_matrix_to_tt
    def project(*args):
        values = original(*args)
        return 1 - values if corrupt else values
    with patch.object(cm_bench, "cm_matrix_to_tt", side_effect=project):
        row = cm_bench.time_backends_on_expr(3, expr, False, False, False, config=config)
    assert row["custom_tt_robdd_input_ok"] is True
    assert row["custom_tt_robdd_ok"] is (not corrupt)
    assert row["custom_tt_robdd_validation_method"] == "full_source_eval_expr_tt"
    assert row["custom_tt_robdd_validation_time_s"] >= 0
