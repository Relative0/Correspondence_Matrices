"""Contract checks for family configuration, scoped build plans and phase records."""
import json
from unittest.mock import patch

import numpy as np
import pytest

import cm_bench as bench
import cm_ir as ir
from bitset_backend import bitset_to_bool_array, get_flat_program
from cm_exprlib import And, Imp, Not, Or, Var, Xor
from cmbench.config import BenchmarkConfig
from cmbench.expr.eval import eval_expr_assignment
from cmbench.output_budget import OutputBudget, OutputBudgetExceeded, estimate_explicit_output
from cmbench.phase_timing import PhaseRecorder, active_recorder


def config(**kwargs):
    return BenchmarkConfig(sizes=(4,), trials=1, seed=2, max_depth=3,
                           no_dd=True, no_robdd_dd=True, **kwargs)


def family():
    return bench.generate_expression_family(4, np.random.default_rng(2), 3,
        "mixed_no_constants", family_size=8, variant_style="shared_block_mix",
        shared_blocks=3, force_shared_substructure=True)


def run_family(cfg, **kwargs):
    return bench.time_expression_family_workload(4, family(), family_id="repair",
        trial=0, expr_style="mixed_no_constants", variant_style="shared_block_mix",
        mutation_rate=.15, bit_env=None, sample_rng=np.random.default_rng(4),
        robdd_order_seed=5, config=cfg, **kwargs)


@pytest.mark.parametrize("flat,words,kind", [(False,False,"recursive"),
    (True,False,"flat"), (False,True,"flat"), (True,True,"flat")])
def test_family_explicit_config_wins_over_opposite_defaults(flat, words, kind):
    cfg = config(cm_flat_eval=flat, cm_words_eval=words, cm_use_persistent_cache=True)
    with ir.evaluation_defaults_scope(flat_eval=not flat, words_eval=not words):
        row = run_family(cfg)
        assert ir.get_evaluation_defaults() == (not flat, not words)
    assert row["family_bitset_baseline_kind"] == "raw_ast_" + kind
    for prefix in ("family_cm_no_cache", "family_cm_cache"):
        assert row[prefix + "_engine_kind"] == "cm_node_" + kind
        assert row[prefix + "_completed_variants"] == 8
        assert row[prefix + "_checked_variants"] == 8
        assert row[prefix + "_correct_variants"] == 8
        assert json.loads(row[prefix + "_output_width_counts_json"]) == {"4": 8}
    assert "family_phase_timing_json" not in row


@pytest.mark.parametrize("flat,words", [(False,False), (True,False), (True,True)])
def test_partial_and_equivalence_pass_explicit_config(flat, words, monkeypatch):
    cfg = config(cm_flat_eval=flat, cm_words_eval=words)
    expr = Xor(Var(0), Var(1))
    with ir.evaluation_defaults_scope(flat_eval=not flat, words_eval=not words):
        with patch.object(bench, "materialize_hybrid_no_reinflate", wraps=ir.materialize_hybrid_no_reinflate) as evaluate:
            bench._cm_partial_workload(expr, 4, [{"x0": 1}], output_mode="remaining-vars",
                persistent_cache=False, reuse_compiled_ir=False, reference_arrays=[None],
                sample_rng=np.random.default_rng(2), config=cfg)
            assert evaluate.call_args.kwargs["flat_eval"] is flat
            assert evaluate.call_args.kwargs["words_eval"] is words
        monkeypatch.setattr(bench, "_current_config", lambda: cfg)
        with patch.object(bench, "evaluate_compiled", wraps=ir.evaluate_compiled) as evaluate:
            row = bench.cm_equivalence_check(expr, Xor(Var(1), Var(0)), 4, expected=True)
            assert row["cm_equiv_ok"] is True
            assert len(evaluate.call_args_list) == 2
            for call in evaluate.call_args_list:
                assert call.kwargs["flat_eval"] is flat
                assert call.kwargs["words_eval"] is words


def test_recorder_exclusive_partition_and_failure():
    wall, cpu = iter([0,10,30,50]), iter([0,2,6,10])
    trace = PhaseRecorder(wall_clock=lambda: next(wall), cpu_clock=lambda: next(cpu))
    with pytest.raises(ValueError), trace.activate(), trace.span("outer"):
        with trace.span("inner"):
            raise ValueError("expected")
    assert active_recorder() is None
    assert ir._IR_PHASE_OBSERVER.get() is None
    root, child = trace.snapshot()["records"]
    assert root["exclusive_wall_ns"] == 30
    assert child["exclusive_wall_ns"] == 20
    assert root["exclusive_cpu_ns"] + child["exclusive_cpu_ns"] == root["cpu_ns"] == 10
    assert child["parent"] == root["id"]
    assert root["status"] == child["status"] == "error"


def test_family_capture_has_oracles_and_partition():
    row = run_family(config(cm_flat_eval=True, cm_use_persistent_cache=True, family_profile_timing=True))
    records = json.loads(row["family_phase_timing_json"])["records"]
    assert records[0]["phase"] == "family_observed"
    for axis in ("wall", "cpu"):
        assert sum(r[f"exclusive_{axis}_ns"] for r in records) == records[0][f"{axis}_ns"]
        assert all(r[f"exclusive_{axis}_ns"] >= 0 for r in records)
    phases = [r["phase"] for r in records]
    assert phases.count("cm_compile_api") == phases.count("correctness_oracle") == 16
    assert phases.count("cache_lifecycle_reset") == 2
    assert "reference_construction" in phases
    assert "persistent_sharing_eligibility" in phases


def test_failure_trace_and_no_silent_reference_truncation():
    recorder = PhaseRecorder()
    with recorder.activate(), pytest.raises(ValueError):
        bench._cm_family_workload([Var(0)], 1, persistent_cache=False, tt_refs=[],
            sample_rng=np.random.default_rng(0), config=config())
    assert recorder.snapshot()["records"][0]["status"] == "error"
    recorder = PhaseRecorder()
    with pytest.raises(OutputBudgetExceeded):
        run_family(config(cm_max_output_bytes=0), timing=recorder)
    assert any(r["phase"] == "cm_evaluate_api" and r["status"] == "error"
               for r in recorder.snapshot()["records"])
    assert active_recorder() is None


def test_failure_midway_records_consumed_variants(monkeypatch):
    recorder = PhaseRecorder()
    original = bench.materialize_hybrid_no_reinflate
    calls = 0
    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("second variant")
        return original(*args, **kwargs)
    monkeypatch.setattr(bench, "materialize_hybrid_no_reinflate", fail_second)
    with pytest.raises(RuntimeError):
        run_family(config(cm_flat_eval=True), timing=recorder)
    evaluations = [r for r in recorder.records if r["phase"] == "cm_evaluate_api"]
    assert [r["status"] for r in evaluations] == ["ok", "error"]
    assert len([r for r in recorder.records if r["phase"] == "correctness_oracle"]) == 1


def test_reduced_family_oracle_checks_full_semantics():
    expr = Xor(Var(0),Var(1))
    reference = scalar(expr,("x0","x1","x2","x3"),{})
    row = bench._cm_family_workload([expr],4,persistent_cache=False,tt_refs=[reference],
        sample_rng=np.random.default_rng(2),config=config(cm_flat_eval=True,cm_max_full_output_vars=2))
    assert row["family_cm_no_cache_correct_variants"] == 1
    assert json.loads(row["family_cm_no_cache_output_status_counts_json"]) == {"reduced":1}
    assert json.loads(row["family_cm_no_cache_output_width_counts_json"]) == {"2":1}


def test_cli_serializes_schema_provenance_and_preserves_disabled_rows(tmp_path):
    import csv
    import subprocess
    import sys
    prefix = tmp_path / "family"
    proc = subprocess.run([sys.executable,"-B","cm_bench.py","--sizes","4","--trials","1",
        "--max-depth","2","--bench-expression-family","--family-size","2",
        "--no-dd","--no-sympy","--no-espresso","--no-numba","--family-profile-timing",
        "--cm-flat-eval","--out",str(prefix)],capture_output=True,text=True,timeout=30)
    assert proc.returncode == 0, proc.stderr
    paths = list(tmp_path.glob("*family*csv"))
    assert len(paths) >= 2
    records = [row for p in paths for row in csv.DictReader(p.open(newline="",encoding="utf-8"))]
    assert any(row.get("family_timing_schema") == "cm-family-phases-v1" for row in records)
    assert any(row.get("family_cm_cache_engine_kind") == "not_run" for row in records)
    captures = [json.loads(row["family_phase_timing_json"]) for row in records if row.get("family_phase_timing_json")]
    assert captures and all(c["schema"] == "cm-family-phases-v1" for c in captures)


def shared_expr():
    h = Xor(Xor(Xor(Var(0), Var(1)), Var(2)), Var(3))
    return And(Xor(h, Var(4)), Xor(h, Var(5)))


def test_shared_plan_once_on_miss_and_hit_with_canonical_program():
    expr = shared_expr()
    normal = ir.compile_expr_to_cm_ir(expr)
    ir.clear_cm_ir_persistent_cache()
    with patch.object(ir.CMIRBuilder, "_shared_assoc_uids", wraps=ir.CMIRBuilder._shared_assoc_uids) as sharing:
        cold = ir.compile_expr_to_cm_ir_persistent(expr)
        assert sharing.call_count == 1
        warm = ir.compile_expr_to_cm_ir_persistent(shared_expr())
        assert sharing.call_count == 2
    assert cold is warm
    assert normal.key == cold.key
    assert get_flat_program(normal).ops == get_flat_program(cold).ops
    assert get_flat_program(normal).loads == get_flat_program(cold).loads


def test_prepared_plan_preserves_subclass_dispatch_and_exception_cleanup():
    expr = shared_expr()
    calls = []
    class Builder(ir.CMIRBuilder):
        def build(self, root):
            calls.append(root)
            return super().build(root)
    builder = Builder()
    plan = builder._shared_assoc_uids(expr)
    node = builder._build_with_sharing_plan(expr, *plan)
    assert calls == [expr]
    assert builder._build_state is builder._prepared_sharing_plan is None
    assert node.key == ir.compile_expr_to_cm_ir(expr).key

    class Failing(Builder):
        def _build_rec(self, root, state):
            raise RuntimeError("expected")
    builder = Failing()
    with pytest.raises(RuntimeError):
        builder._build_with_sharing_plan(expr, *plan)
    assert builder._build_state is builder._prepared_sharing_plan is None


def test_prepared_plan_rejects_substituted_root_and_obeys_options():
    expr, other = shared_expr(), Or(Var(0), Var(2))
    class Substitute(ir.CMIRBuilder):
        def build(self, root):
            return super().build(other)
    builder = Substitute()
    result = builder._build_with_sharing_plan(expr, *builder._shared_assoc_uids(expr))
    assert result.key == ir.compile_expr_to_cm_ir(other).key
    builder = ir.CMIRBuilder(share_aware_flatten=False)
    result = builder._build_with_sharing_plan(expr, *builder._shared_assoc_uids(expr))
    assert result.key == ir.compile_expr_to_cm_ir(expr, share_aware_flatten=False).key


def test_prepared_build_reentry_reuses_outer_state():
    expr = shared_expr()
    class Reentrant(ir.CMIRBuilder):
        entered = False
        def _build_rec(self, root, state):
            if root is expr and not self.entered:
                self.entered = True
                return self.build(root)
            return super()._build_rec(root, state)
    builder = Reentrant()
    result = builder._build_with_sharing_plan(expr,*builder._shared_assoc_uids(expr))
    assert result.key == ir.compile_expr_to_cm_ir(expr).key
    assert builder._build_state is builder._prepared_sharing_plan is None


def test_cache_telemetry_does_not_equate_same_call_and_prior_call_hits():
    ir.clear_cm_ir_persistent_cache()
    trace = PhaseRecorder()
    with trace.activate():
        cold, warm = {}, {}
        ir.compile_expr_to_cm_ir_persistent(shared_expr(), cold)
        ir.compile_expr_to_cm_ir_persistent(shared_expr(), warm)
    assert cold["ir_cache_profile_v1"]["policy"] == "root_only"
    assert cold["ir_cache_profile_v1"]["root_hits"] == 0
    assert warm["ir_cache_profile_v1"]["root_hits"] == 1
    assert warm["ir_cache_profile_v1"]["prior_call_hits"] == 1
    assert warm["ir_cache_profile_v1"]["same_call_hits"] == 0
    plain = {}
    ir.compile_expr_to_cm_ir_persistent(shared_expr(), plain)
    assert "ir_cache_profile_v1" not in plain


def test_subtree_policy_can_hit_the_root():
    ir.clear_cm_ir_persistent_cache()
    expr = Or(And(Var(0),Var(1)),Xor(Var(2),Var(3)))
    trace = PhaseRecorder()
    with trace.activate():
        ir.compile_expr_to_cm_ir_persistent(expr)
        diag = {}
        ir.compile_expr_to_cm_ir_persistent(expr, diag)
    detail = diag["ir_cache_profile_v1"]
    assert detail["policy"] == "subtree"
    assert detail["root_hits"] == detail["prior_call_hits"] == 1
    assert detail["subtree_hits"] == detail["same_call_hits"] == 0


def test_reinserted_initial_key_has_same_call_origin(monkeypatch):
    ir.clear_cm_ir_persistent_cache()
    monkeypatch.setattr(ir,"_PERSISTENT_IR_CACHE_MAXSIZE",3)
    ir.compile_expr_to_cm_ir_persistent(Var(0))
    expr = Or(And(Var(2),Var(3)),Xor(Var(0),Var(0)))
    trace, diag = PhaseRecorder(), {}
    with trace.activate():
        node = ir.compile_expr_to_cm_ir_persistent(expr,diag)
    detail = diag["ir_cache_profile_v1"]
    assert node.key == ir.compile_expr_to_cm_ir(expr).key
    assert detail["entries_before"] == 1
    assert detail["evictions"] > 0
    assert detail["same_call_hits"] == 1
    assert detail["prior_call_hits"] == 0
    ir.clear_cm_ir_persistent_cache()


def scalar(expr, names, fixed):
    return np.array([eval_expr_assignment(expr, {
        **{v: (row >> (len(names)-1-i)) & 1 for i,v in enumerate(names)}, **fixed})
        for row in range(1 << len(names))], dtype=np.uint8)


@pytest.mark.parametrize("fast", [False,True])
@pytest.mark.parametrize("mode", ["off","counts","ir","profile"])
@pytest.mark.parametrize("threshold", [0,16])
def test_wrapper_fixed_basis_and_fallback_match_scalar(fast, mode, threshold):
    expr = Imp(And(Var(0), Var(1)), Or(Var(2), Var(3)))
    node = ir.compile_expr_to_cm_ir(expr)
    diag = {"off":None,"counts":{},"ir":{"ir_timing_enabled":1},
            "profile":{"cached_exec_profile_enabled":1}}[mode]
    # Reuse diagnostics through complete, partial, all-fixed, and restored basis.
    for fixed in ({}, {"x0":1}, dict(x0=1,x1=1,x2=0,x3=1), {}):
        names = tuple(v for v in ("x3","x2","x1","x0","x4") if v not in fixed)
        result = ir.materialize_hybrid_no_reinflate(node, names, fixed=fixed,
            flat_eval=True, words_eval=False, diagnostics=diag,
            hybrid_threshold=threshold, flat_fast_path=fast)
        actual = bitset_to_bool_array(result.bits,len(names)) if result.bits is not None else result.tt
        assert np.array_equal(actual, scalar(expr,names,fixed))
        assert result.output_vars == names


@pytest.mark.parametrize("fast", [False,True])
def test_admission_once_for_fallback_and_refuses_before_evaluator(fast):
    node = ir.compile_expr_to_cm_ir(Xor(Var(0),Var(1)))
    with patch.object(ir, "decide_output_budget", wraps=ir.decide_output_budget) as decide:
        ir.materialize_hybrid_no_reinflate(node, ("x0","x1"), hybrid_threshold=0,
            flat_eval=True, flat_fast_path=fast)
        assert decide.call_count == 1
    estimate = estimate_explicit_output(2,"packed_bitset",operation_slots=ir._cm_node_count(node))
    for field, limit in [("max_output_bytes",estimate.output_bytes),
                         ("max_temporary_bytes",estimate.temporary_bytes)]:
        for delta in [-1,0,1]:
            kwargs = dict(flat_eval=True,flat_fast_path=fast,output_budget=OutputBudget(**{field:limit+delta}))
            if delta < 0:
                with pytest.raises(OutputBudgetExceeded):
                    ir.materialize_hybrid_no_reinflate(node,("x0","x1"),**kwargs)
            else:
                assert ir.materialize_hybrid_no_reinflate(node,("x0","x1"),**kwargs).bits == 6


def test_words_uses_actual_output_width_and_reduced_width():
    node = ir.compile_expr_to_cm_ir(Or(Var(0),Var(19)))
    names = tuple(f"x{i}" for i in range(20))
    diag = {}
    result = ir.materialize_hybrid_no_reinflate(node,names,words_eval=True,flat_eval=True,
        diagnostics=diag,allow_reduced_output=True,max_full_output_vars=16)
    assert result.output_vars == ("x0","x19")
    assert result.bits == 14
    assert diag["cached_exec_engine_kind"] == "cm_node_flat"
    node = ir.compile_expr_to_cm_ir(Xor(Var(0),Var(1)))
    result = ir.evaluate_compiled(ir.compile_expr(Xor(Var(0),Var(1))),
        vars_all=names[:16],flat_eval=False,words_eval=True,diagnostics=diag)
    assert diag["cached_exec_engine_kind"] == "cm_node_words"
    assert diag["cached_exec_engine_live_k"] == 16
    assert result.bits.bit_count() == 32768


def test_q64_all_assignments_and_invalid_threshold_precedence():
    expr = shared_expr()
    node = ir.compile_expr_to_cm_ir(expr)
    for row in range(64):
        fixed = {f"x{i}": (row >> (5-i)) & 1 for i in range(6)}
        assert ir.materialize_hybrid_no_reinflate(node,(),fixed=fixed,flat_eval=True).bits == int(eval_expr_assignment(expr,fixed))
    for fast, exception in [(True,ValueError),(False,OutputBudgetExceeded)]:
        with pytest.raises(exception):
            ir.materialize_hybrid_no_reinflate(node,node.vars,hybrid_threshold=-1,
                flat_eval=True,flat_fast_path=fast,output_budget=OutputBudget(max_output_bytes=0))
