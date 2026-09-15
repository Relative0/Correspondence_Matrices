from __future__ import annotations

import copy

import pytest

from cmbench.recognition import post_benchmark_neural_gate as gate


EVIDENCE_CHECKPOINT = "27e88d26a780da0840cd9ed221c1f8966dfeb039"
EVIDENCE_TREE = "3fe0e88497d09a7b768e827e669dc6138bed31fd"
SOURCE_BINDINGS = {"synthetic/source.py": "a" * 64}


@pytest.fixture(scope="module")
def current_inputs():
    return gate.load_default_inputs()


@pytest.fixture(scope="module")
def current_assessment(current_inputs):
    return gate.build_assessment(
        current_inputs,
        evidence_checkpoint=EVIDENCE_CHECKPOINT,
        evidence_tree=EVIDENCE_TREE,
        source_bindings=SOURCE_BINDINGS,
    )


def _row(case_id: str, block: int, arm: str, total: int, status: str = "ok"):
    row = {
        "lane": "X",
        "case_id": case_id,
        "block": block,
        "arm": arm,
        "status": status,
    }
    if status == "ok":
        row["timings_ns"] = {"accounted_total_ns": total}
    return row


def test_surface_uses_per_case_medians_and_retains_refusals():
    rows = []
    for block in (0, 1):
        rows.extend([
            _row("case-a", block, "a", 100),
            _row("case-a", block, "b", 50),
            _row("case-b", block, "a", 100),
            _row("case-b", block, "b", 200),
            _row("refused", block, "a", 0, "refused"),
            _row("refused", block, "b", 0, "refused"),
        ])
    result = gate._surface(
        rows,
        surface_id="synthetic",
        lane="X",
        arms=["a", "b"],
        recognition_ns_per_case=10,
    )
    assert result["complete_cases"] == 2
    assert result["excluded_case_ids"] == ["refused"]
    assert result["refused_rows_retained"] == 4
    assert result["best_fixed_method"] == "a"
    assert result["best_fixed_median_sum_ns"] == 200
    assert result["oracle_median_sum_ns"] == 150
    assert result["gross_headroom_speedup"] == pytest.approx(4 / 3)
    assert result["diagnostic_label_counts"] == {"a": 1, "b": 1}


def test_retry_002_recomputes_22_task_and_cohort_surfaces(current_assessment):
    assessment = current_assessment
    assert assessment["status"] == "complete_no_training"
    assert len(assessment["surfaces"]) == 22
    assert assessment["gross_gate_candidates"] == [
        "lane_d_version_history_resident_engine"
    ]
    assert assessment["charged_gate_candidates"] == []
    assert assessment["decision"]["training_allowed"] is False
    assert assessment["decision"]["complete_abstention"] is True


def test_strongest_surface_is_only_a_gross_signal(current_assessment):
    strongest = current_assessment["strongest_surface"]
    assert strongest["surface_id"] == "lane_d_version_history_resident_engine"
    assert strongest["complete_cases"] == 3
    assert strongest["best_fixed_method"] == "sat/resident_engine"
    assert strongest["gross_headroom_speedup"] == pytest.approx(
        1.1375804204974516
    )
    assert strongest["gross_headroom_ns"] == 43_015.0
    assert strongest["diagnostic_label_counts"] == {
        "cnf/resident_engine": 1,
        "sat/resident_engine": 2,
    }
    assert strongest["optimistic_feature_only_charged_speedup"] == pytest.approx(
        0.5208562305091795
    )
    assert strongest["maximum_overhead_ns_per_case_preserving_1_10x"] == pytest.approx(
        3_560.5
    )


def test_major_exact_surfaces_remain_below_development_gate(current_assessment):
    surfaces = current_assessment["surfaces"]
    assert surfaces["lane_a_all"]["gross_headroom_speedup"] == pytest.approx(
        1.006013801527839
    )
    assert surfaces["lane_b_all"]["gross_headroom_speedup"] == pytest.approx(
        1.0510981485591786
    )
    assert surfaces["lane_b_fresh"]["gross_headroom_speedup"] == pytest.approx(
        1.0582401965135309
    )
    assert surfaces["lane_c_all"]["gross_headroom_speedup"] == pytest.approx(
        1.0240958584387994
    )


def test_tampered_evidence_bindings_fail_closed(current_inputs):
    tampered = dict(current_inputs)
    documents = dict(current_inputs["documents"])
    analysis = copy.deepcopy(documents["analysis"])
    analysis["inputs"]["raw_measurements_sha256"] = "0" * 64
    documents["analysis"] = analysis
    tampered["documents"] = documents
    with pytest.raises(ValueError, match="analysis evidence binding"):
        gate.build_assessment(
            tampered,
            evidence_checkpoint=EVIDENCE_CHECKPOINT,
            evidence_tree=EVIDENCE_TREE,
            source_bindings=SOURCE_BINDINGS,
        )


def test_tampered_permissions_labels_and_candidates_fail_closed(current_assessment):
    mutations = []
    changed = copy.deepcopy(current_assessment)
    changed["permissions"]["neural_training"] = True
    mutations.append(changed)
    changed = copy.deepcopy(current_assessment)
    changed["gross_gate_candidates"] = []
    mutations.append(changed)
    changed = copy.deepcopy(current_assessment)
    changed["surfaces"]["lane_a_all"]["diagnostic_label_counts"] = {
        "direct_expression_bitset": 77
    }
    mutations.append(changed)
    for value in mutations:
        with pytest.raises(ValueError):
            gate.validate_assessment(value)


def test_report_states_signal_without_authorizing_training(current_assessment):
    report = gate.render_report(current_assessment)
    assert "new gross signal worth recording" in report
    assert "neural training remains prohibited" in report
    assert "0.520856231x" in report
    assert "sub-3.6 microsecond" in report
