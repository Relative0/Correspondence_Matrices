from __future__ import annotations

import copy
from itertools import product
from subprocess import CompletedProcess, TimeoutExpired

import pytest

from cmbench.biology_bnet import parse_bnet
from cmbench.biology_controls import bnet_scalar_oracle, encode_fixed_points, is_fixed_point, native_fixed_points
from cmbench.backends.projected_count import scalar_projected_count, pysat_projected_count, ProjectedCNF
from cmbench.backends.exact_controls_v2 import parse_counting_v2, projected_count_v2, run_exact_counter_v2, run_sat_v2, run_projected_ganak_v2
from cmbench.benchmark_contracts import SCHEMA, mechanism_attribution, validate_result


@pytest.mark.parametrize("source", [
    "a, a\nb, b", "a, !a", "a, 1\nb, 0", "a, b\nb, a",
    "a, b | !a\nb, a & b", "a, (a | b) & (!a | !b)\nb, !a",
    "a, !!!a | (a & a)",
])
def test_parsimonious_encoding_counts_and_original_witness(source):
    functions = parse_bnet("targets,factors\n" + source)
    for fixed in ({}, {functions[0].target: 0}, {functions[0].target: 1}):
        for semantics in ("clamp", "condition"):
            cnf = encode_fixed_points(functions, fixed=fixed, semantics=semantics)
            oracle = bnet_scalar_oracle(functions, fixed=fixed, semantics=semantics)
            native = native_fixed_points(functions, fixed=fixed, semantics=semantics)
            full = ProjectedCNF(cnf.variables, cnf.clauses, tuple(range(1, cnf.variables + 1)), "exact")
            assert oracle.count == native.count == scalar_projected_count(full) == pysat_projected_count(cnf.as_projected())
            # Check unique auxiliary extension for EVERY original assignment.
            for bits in product((False, True), repeat=len(functions)):
                assignment = dict(zip(cnf.targets, bits))
                units = tuple((i + 1 if value else -(i + 1),) for i, value in enumerate(bits))
                restricted = ProjectedCNF(cnf.variables, cnf.clauses + units, full.projection, "exact")
                assert scalar_projected_count(restricted) == int(is_fixed_point(functions, assignment, fixed=fixed, semantics=semantics))
            if native.count:
                assert is_fixed_point(functions, native.witness, fixed=fixed, semantics=semantics)


def test_clamp_replaces_equation_while_condition_retains_it():
    functions = parse_bnet("targets,factors\na, !a")
    assert native_fixed_points(functions, fixed={"a": 1}, semantics="clamp").count == 1
    assert native_fixed_points(functions, fixed={"a": 1}, semantics="condition").count == 0
    with pytest.raises(ValueError, match="undeclared"):
        encode_fixed_points(parse_bnet("targets,factors\na, input"))
    with pytest.raises(ValueError, match="fixed"):
        bnet_scalar_oracle(functions, fixed={"unknown": 1})
    with pytest.raises(ValueError, match="enumeration limit"):
        native_fixed_points(parse_bnet("targets,factors\na, a"), max_solutions=1)


def test_projection_support_distinction_and_empty_projection():
    source = "c ind 1 0\nc p show 2 0\np cnf 3 1\n1 0\n"
    instance = parse_counting_v2(source, mode="projected")
    assert instance.projection == (2,) and instance.declared_support == (1,)
    assert scalar_projected_count(instance) == pysat_projected_count(instance) == 2
    for clause, count in (("1 0", 1), ("0", 0)):
        instance = parse_counting_v2(f"c p show 0\np cnf 1 1\n{clause}\n", mode="projected")
        assert scalar_projected_count(instance) == projected_count_v2(instance) == count
    with pytest.raises(ValueError, match="conflicts"):
        parse_counting_v2(source, mode="exact")
    with pytest.raises(ValueError, match="explicit"):
        parse_counting_v2("c ind 1 0\np cnf 2 0\n", mode="projected")
    with pytest.raises(ValueError, match="weighted"):
        parse_counting_v2("c p weight 1 0.5 0\np cnf 1 0\n", mode="exact")


@pytest.mark.parametrize("backend", ["d4", "ganak"])
def test_native_exact_ignores_untrusted_support_and_rejects_universe_overflow(tmp_path, monkeypatch, backend):
    source = tmp_path / "input.cnf"
    source.write_text("c ind 1 0\np cnf 3 1\n1 0\n")
    def completed(command, **kwargs):
        from pathlib import Path
        input_path = command[command.index("-i") + 1] if backend == "d4" else command[-1]
        assert "c ind" not in Path(input_path).read_text()
        output = "s 999\n" if backend == "d4" else "s SATISFIABLE\nc s exact arb int 999\n"
        return CompletedProcess(command, 0, output, "")
    monkeypatch.setattr("cmbench.backends.native_count.subprocess.run", completed)
    with pytest.raises(ValueError, match="universe"):
        run_exact_counter_v2(source, backend=backend, executable="pinned")


def test_sat_duplicate_conflicts_timeout_and_link_rejection(tmp_path, monkeypatch):
    source = tmp_path / "input.cnf"
    source.write_text("p cnf 2 1\n1 0\n")
    monkeypatch.setattr("cmbench.backends.native_sat.subprocess.run", lambda command, **kwargs:
                        CompletedProcess(command, 10, "s SATISFIABLE\nv -1 1 -2 0\n", ""))
    with pytest.raises(ValueError, match="contradictory"):
        run_sat_v2(source, executable="pinned")
    def timeout(command, **kwargs):
        raise TimeoutExpired(command, 1)
    monkeypatch.setattr("cmbench.backends.native_sat.subprocess.run", timeout)
    with pytest.raises(TimeoutError):
        run_sat_v2(source, executable="pinned", timeout_seconds=1)
    monkeypatch.setattr("pathlib.Path.is_symlink", lambda path: path == source)
    with pytest.raises(ValueError, match="linked"):
        run_sat_v2(source, executable="pinned")


def valid_row():
    return {"schema": SCHEMA, "arm": "bnet_scalar_oracle",
            "mechanism_attribution": mechanism_attribution("bnet_scalar_oracle"),
            "input_sha256": "a" * 64, "query_schedule_sha256": "b" * 64, "source_manifest_sha256": "c" * 64,
            "instance_id": "test", "cluster_id": "test-family", "partition": "diagnostic",
            "environment_id": "local", "memory_scope": "process_tree_peak_rss",
            "perturbation_semantics": "clamp", "queries": 1, "repetition": 0,
            "status": "ok", "peak_memory_bytes": 100,
            "timing_seconds": {"cold_construction": 1., "preparation": 1., "warm_queries": 1., "total_session": 3.},
            "outputs": [{"count": "1", "satisfiable": True, "witness": {"a": True}, "witness_validated": True,
                         "witness_backend": "bnet_scalar_oracle"}]}


def test_future_schema_requires_attribution_and_exact_semantics():
    row = valid_row()
    validate_result(row)
    for key, value in (("mechanism_attribution", None), ("arm", "bnet_cm_scalar"), ("outputs", [])):
        bad = copy.deepcopy(row)
        bad[key] = value
        with pytest.raises(ValueError):
            validate_result(bad)
    bad = copy.deepcopy(row)
    bad["mechanism_attribution"]["category"] = "attribution-isolated CM effect"
    with pytest.raises(ValueError, match="isolated"):
        validate_result(bad)
    for status in ("timeout", "unavailable", "resource_limit"):
        failed = {**row, "status": status, "outputs": None, "failure_reason": "bounded diagnostic"}
        validate_result(failed)
        with pytest.raises(ValueError):
            validate_result({**failed, "outputs": [{"count": "0"}]})


@pytest.mark.parametrize("status,code,witness", [
    ("SATISFIABLE", 10, "v 1 0 -2"), ("SATISFIABLE", 10, "v 1 -2"),
    ("UNSATISFIABLE", 20, "v 1 -2 0"),
])
def test_sat_protocol_requires_final_terminator_and_no_unsat_witness(tmp_path, monkeypatch, status, code, witness):
    source = tmp_path / "input.cnf"
    source.write_text("p cnf 2 1\n1 0\n")
    monkeypatch.setattr("cmbench.backends.native_sat.subprocess.run", lambda command, **kwargs:
                        CompletedProcess(command, code, f"s {status}\n{witness}\n", ""))
    with pytest.raises(ValueError):
        run_sat_v2(source, executable="pinned")


def test_projected_ganak_normalizes_support_and_bounds_empty_universe(tmp_path, monkeypatch):
    source = tmp_path / "projected.cnf"
    source.write_text("c ind 1 0\nc p show 0\np cnf 1 1\n1 0\n")
    count = 1
    def completed(command, **kwargs):
        from pathlib import Path
        normalized = Path(command[-1]).read_text()
        assert "c ind" not in normalized and "c p show" in normalized
        return CompletedProcess(command, 0, f"s SATISFIABLE\nc s exact arb int {count}\n", "")
    monkeypatch.setattr("cmbench.backends.exact_controls_v2.subprocess.run", completed)
    assert run_projected_ganak_v2(source, executable="pinned").count == 1
    count = 2
    with pytest.raises(ValueError, match="universe"):
        run_projected_ganak_v2(source, executable="pinned")
