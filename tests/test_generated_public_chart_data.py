import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "generate_v4audit_public_chart_data.py"


def _module():
    spec = importlib.util.spec_from_file_location("chart_generator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_generated_chart_data_is_current_and_pages_reference_it():
    module = _module()
    generated = REPO / "deliverables_n22_24" / "v4audit_public_chart_data_2026_07_24.js"
    assert generated.read_text(encoding="utf-8") == module.render_javascript()
    for name in ("cm_head_to_head_explained.html", "cm_benchmark_charts.html"):
        html = (REPO / "deliverables_n22_24" / name).read_text(encoding="utf-8")
        assert 'src="v4audit_public_chart_data_2026_07_24.js"' in html
        assert "V4AUDIT_CHART_DATA" in html


def test_generated_core_series_match_current_public_values():
    data = _module().build_chart_data()
    assert data["kernel"]["bigint_engine"] == [0.56, 0.85, 0.89, 0.96, 0.87]
    assert data["kernel"]["words_engine"] == [0.9, 0.89, 0.96, 0.94, 1.04]
    assert data["wrapper"]["cm_over_bitset"] == [1.05, 1.27, 1.23, 1.15, 1.05, 0.98, 0.92, 0.89, 0.84]
    assert data["wrapper"]["cudd_build_over_bitset_contextual"] == [0.63, 4.4, 4.62, 4.81, 3.41, 3.34, 3.18, 3.19, 3.24]
