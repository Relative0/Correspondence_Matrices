from __future__ import annotations

from bitset_backend import build_bitset_env, eval_expr_bitset
from cmbench.recognition.normalization_experiment import (
    NormalizationConfig, _measure_arm, load_cases,
)
from cmbench.recognition.rule_pack import compile_rule_pack, prove_rule_pack_v2


def test_normalization_experiment_slice_is_exact_and_bounded() -> None:
    config = NormalizationConfig(case_count=8, rounds=1)
    cases, selection, document = load_cases(config)
    matcher = compile_rule_pack(prove_rule_pack_v2())
    expected = {case.cone_id: eval_expr_bitset(case.expr,
        build_bitset_env(tuple(f"x{i}" for i in range(case.n_vars)))) for case in cases}

    row = _measure_arm(cases[:1], "fixpoint", 0, matcher, 128, 8, expected)

    assert row["status"] == "ok"
    assert row["case_count"] == 1
    assert row["kernel_repeats"] == 128
    assert len(selection["selected_ids"]) == 8
    assert len(document["cases"]) == 8
