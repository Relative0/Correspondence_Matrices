from __future__ import annotations

from pathlib import Path

from cmbench.recognition.native_portfolio_reassessment import (
    build_assessment,
    verify_development_artifact,
)


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/recognition/runs/neural-native-portfolio-reassessment-development-20260903-001"


def test_native_portfolio_closure_stops_training_and_prospective_use() -> None:
    result = build_assessment()
    assert result["labels"]["counts"] == {"native_fused_slots": 18}
    assert result["labels"]["complete_current_portfolio_in_one_run"] is True
    assert result["labels"]["training_label_ready"] is True
    assert result["labels"]["training_eligible"] is False
    assert result["economics"]["gross_headroom_speedup"] == 1.0
    assert result["economics"]["optimistic_feature_only_charged_speedup"] < 1.0
    assert result["decision"]["training_allowed"] is False
    assert result["decision"]["prospective_confirmation_allowed"] is False


def test_retained_native_portfolio_reassessment_replays() -> None:
    if not RUN.is_dir():
        return
    result = verify_development_artifact(RUN)
    assert result["status"] == "verified"
    assert result["backend_labels_replayed"] == 18
