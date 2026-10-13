import json
from pathlib import Path

from cmbench.recognition.gf2_c41_ablation_benchmark import (
    C41Config,
    METHODS,
    _analysis,
    build_freeze,
    validate_freeze,
    verify_freeze,
)
from cmbench.recognition.gf2_decomposition_experiment import make_gf2_controls


ROOT = Path(__file__).resolve().parents[1]
C40_FREEZE = ROOT / "docs/recognition/c40_gf2_development_blind_freeze_20260916/FREEZE.json"


def test_each_c41_ablation_preserves_selected_document_and_reconstruction() -> None:
    config = C41Config()
    for control in make_gf2_controls(config.seed):
        kwargs = {"row_partitions": control["row_partitions"]} if control["row_partitions"] else {}
        reference = _analysis("c16_reference", control["bits"], control["n_vars"], config, **kwargs)
        expected = reference.best.to_dict() if reference.best is not None else None
        for method in METHODS:
            analysis = _analysis(method, control["bits"], control["n_vars"], config, **kwargs)
            actual = analysis.best.to_dict() if analysis.best is not None else None
            assert actual == expected, (control["case_id"], method)
            assert analysis.best is None or analysis.best.reconstruct() == control["bits"]


def test_c41_freeze_is_self_contained_and_verifies() -> None:
    freeze = build_freeze(
        project_root=ROOT,
        c40_freeze_path=C40_FREEZE,
        config=C41Config(rounds=3),
        created_utc="2026-09-16T00:00:00Z",
    )
    validate_freeze(json.loads(json.dumps(freeze)))
    assert verify_freeze(freeze, ROOT) == {
        "schema": "crse-c41-freeze-verification/v1", "verified": True, "errors": []
    }
    assert len(freeze["schedule"]) == len(freeze["cases"]) * 3 * len(METHODS)
