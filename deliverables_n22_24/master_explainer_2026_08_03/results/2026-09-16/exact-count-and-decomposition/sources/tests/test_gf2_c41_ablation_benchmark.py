import json
import shutil
from pathlib import Path

from cmbench.recognition.gf2_c41_ablation_benchmark import (
    C41Config,
    METHODS,
    SOURCE_CLOSURE_PATHS,
    _analysis,
    build_freeze,
    validate_freeze,
    verify_freeze,
)
from cmbench.recognition.gf2_decomposition_experiment import make_gf2_controls
from cmbench.recognition.gf2_decomposition import truth_sha256


ROOT = Path(__file__).resolve().parents[1]


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


def test_c41_freeze_is_self_contained_and_verifies(tmp_path) -> None:
    # Exercise the actual closure checks without redistributing C40 corpus data.
    for relative in SOURCE_CLOSURE_PATHS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    c40_freeze = tmp_path / "synthetic-c40-shaped-input.json"
    c40_freeze.write_text(json.dumps({
        "freeze_sha256": "synthetic-test-fixture-not-a-measurement",
        "cases": [{"case_id": "synthetic-c40-control", "n_vars": 2,
                   "truth_bits_hex": "0x6", "truth_sha256": truth_sha256(6, 2)}],
    }), encoding="utf-8")
    freeze = build_freeze(
        project_root=tmp_path,
        c40_freeze_path=c40_freeze,
        config=C41Config(rounds=3),
        created_utc="2026-09-16T00:00:00Z",
    )
    validate_freeze(json.loads(json.dumps(freeze)))
    assert verify_freeze(freeze, tmp_path) == {
        "schema": "crse-c41-freeze-verification/v1", "verified": True, "errors": []
    }
    assert len(freeze["schedule"]) == len(freeze["cases"]) * 3 * len(METHODS)
    c40_freeze.write_text("{}", encoding="utf-8")
    assert not verify_freeze(freeze, tmp_path)["verified"]
