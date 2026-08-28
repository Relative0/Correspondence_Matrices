from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT_PATH = (
    ROOT
    / "deliverables_n22_24"
    / "master_explainer_2026_08_03"
    / "use_case_benchmarks_2026-08-27"
    / "cm_feature_model_history_pilot.py"
)
SPEC = importlib.util.spec_from_file_location("cm_feature_model_history_pilot", PILOT_PATH)
assert SPEC and SPEC.loader
pilot = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pilot
SPEC.loader.exec_module(pilot)

from bitset_backend import _eval_words, compile_expr_cse, get_flat_program  # noqa: E402
from cm_ir import compile_expr_to_cm_ir  # noqa: E402


def test_missing_promisor_object_uses_git_lazy_fetch(monkeypatch, tmp_path: Path) -> None:
    presence = iter((False, True))
    calls = []
    monkeypatch.setattr(pilot, "object_present", lambda _source, _sha: next(presence))

    def fake_git_run(source, args, *, check=True, no_lazy=False):
        calls.append((source, args, check, no_lazy))
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(pilot, "git_run", fake_git_run)
    pilot.ensure_object(tmp_path, "a" * 40)
    assert calls == [(tmp_path, ["cat-file", "-e", "a" * 40], False, False)]


def test_selection_uses_first_middle_last_transitions_for_all_histories() -> None:
    rows = []
    for history_index in range(7):
        for version_index in range(6):
            rows.append({
                "PartOfHistory": "True",
                "Name": f"history-{history_index}",
                "Version": f"v{version_index}",
                "Domain": "test",
                "Origin": "fixture",
                "Path": f"fixture/{history_index}/{version_index}",
                "NumberOfFeatures": "8",
                "NumberOfClauses": "4",
            })
    selected, transitions = pilot.select_models(rows)
    assert len(transitions) == 7
    assert {model.ordinal for model in selected if model.history == "history-0"} == {0, 1, 2, 3, 4, 5}
    assert [item["later_ordinal"] for item in transitions[0]["transitions"]] == [1, 3, 5]


def test_dimacs_parser_preserves_feature_mapping_and_spanning_clauses(tmp_path: Path) -> None:
    path = tmp_path / "fixture.dimacs"
    path.write_bytes(
        b"c 1 Root\n"
        b"c 2 Optional_Feature\n"
        b"p cnf 3 2\n"
        b"1 -2\n"
        b"3 0\n"
        b"-1 0\n"
    )
    parsed = pilot.parse_dimacs(path)
    assert parsed.n_vars == 3
    assert parsed.clauses == [(1, -2, 3), (-1,)]
    assert parsed.feature_names == {1: "Root", 2: "Optional_Feature"}


def test_conditioned_cnf_cm_cse_and_scalar_semantics_are_bit_identical() -> None:
    clauses = [(1, 9), (-1, -9), (2, 3), (10, 4), (-10, 5)]
    product = {variable: False for variable in range(1, 11)}
    product.update({2: True, 4: True, 9: True, 10: False})
    assert pilot.scalar_cnf(clauses, product)
    slice_variables = tuple(range(1, 9))
    residual, stats = pilot.condition_cnf(clauses, product, slice_variables)
    assert residual == ((-1,), (2, 3), (4,))
    assert stats["residual_clauses"] == 3

    direct = pilot.cnf_bitset(residual)
    expression = pilot.expression_from_residual(residual)
    evaluator_vars = tuple(f"x{index}" for index in range(7, -1, -1))
    cse = _eval_words(compile_expr_cse(expression, flatten=True), evaluator_vars, {})
    cm = _eval_words(get_flat_program(compile_expr_to_cm_ir(expression)), evaluator_vars, {})
    assert cm == cse == direct

    scalar = 0
    for assignment_index in range(256):
        assignment = dict(product)
        for index, variable in enumerate(slice_variables):
            assignment[variable] = bool((assignment_index >> index) & 1)
        if pilot.scalar_cnf(clauses, assignment):
            scalar |= 1 << assignment_index
    assert direct == scalar


def test_product_encoding_is_little_endian_by_dimacs_variable() -> None:
    product = {1: True, 2: False, 3: True, 8: True, 9: True}
    encoded = pilot.encode_product(product, 9)
    assert encoded == bytes((0b10000101, 0b00000001))
