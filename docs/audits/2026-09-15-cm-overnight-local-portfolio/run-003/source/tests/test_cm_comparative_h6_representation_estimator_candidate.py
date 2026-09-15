from __future__ import annotations

from pathlib import Path

from cmbench.comparative import h6_representation_estimator_candidate as candidate


ROOT = Path(__file__).resolve().parents[1]


def test_candidate_freeze_is_deterministic_and_blind_to_memory_values():
    first = candidate.build_freeze(ROOT)
    second = candidate.build_freeze(ROOT)
    assert first == second
    assert first["status"] == "frozen_before_decision_bearing_candidate_evaluation"
    assert first["selection"]["selection_blind_to_case_memory_values"] is True
    assert first["selection"]["calibration_cells"] == 24
    assert first["selection"]["holdout_cells"] == 20
    assert first["models"]["candidate_count"] == 1
    assert first["continuation"]["production_routing_change_authorized"] is False
    assert first["continuation"]["runpod_authorized"] is False


def test_upper_envelope_covers_every_training_cell_and_is_nonnegative():
    cells = [
        {"expression_bytes": 100, "actual_bytes": 200_000},
        {"expression_bytes": 200, "actual_bytes": 250_000},
        {"expression_bytes": 400, "actual_bytes": 500_000},
    ]
    model = candidate.fit_upper_envelope(cells)
    assert model["slope"] >= 0.0
    assert all(candidate.predict(model, row["expression_bytes"]) >= row["actual_bytes"]
               for row in cells)


def test_cell_aggregation_keeps_all_arms_queries_and_replicates():
    calibration = [f"fresh-{index}" for index in range(6)]
    holdout = [f"c36-{index}" for index in range(5)]
    freeze = {
        "selection": {
            "calibration_case_ids": calibration,
            "holdout_case_ids": holdout,
            "source_rows_per_case_arm": 6,
        }
    }
    rows = []
    for case_index, case_id in enumerate(calibration + holdout):
        for arm_index, arm in enumerate(candidate.ARMS):
            for query_count in (1, 64):
                for replicate in range(3):
                    value = 100_000 + 10_000 * case_index + 1_000 * arm_index + replicate
                    rows.append({
                        "row_id": f"B:{case_id}:q{query_count}:{arm}:reused:r{replicate}",
                        "lane": "B", "case_id": case_id, "arm": arm,
                        "lifecycle": "reused", "query_count": query_count,
                        "replicate": replicate,
                        "features": {"expression_bytes": 500 + case_index},
                        "memory": {
                            "working_set_prepared_retained_delta_bytes": value,
                            "private_prepared_retained_delta_bytes": value - 100,
                        },
                    })
    cells = candidate.aggregate_cells(rows, freeze)
    assert len(cells) == 44
    assert sum(row["cohort"] == "calibration" for row in cells) == 24
    assert sum(row["cohort"] == "holdout" for row in cells) == 20
    assert all(len(row["source_row_ids"]) == 6 for row in cells)


def test_protocol_forbids_second_candidate_and_production_activation():
    text = (ROOT / candidate.PROTOCOL).read_text(encoding="utf-8")
    assert "no second candidate is tried" in text
    assert "does not itself authorize RunPod" in text
    assert "does not alter an evaluator" in text
