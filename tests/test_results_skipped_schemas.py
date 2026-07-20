from cmbench.results.expression_family import skipped_family_backend
from cmbench.results.partial_context import skipped_partial_backend
from cmbench.results.single_expr import error_result_from_exception, skipped_single_backend


def test_partial_skipped_schema_preserves_legacy_keys():
    row = skipped_partial_backend("partial_robdd", reason="disabled")

    assert row["partial_robdd_status"] == "disabled"
    assert "partial_robdd_build_once_s" in row
    assert "partial_robdd_build_restrict_extract_total_s" in row


def test_family_skipped_schema_preserves_legacy_keys():
    row = skipped_family_backend("family_robdd", reason="skipped")

    assert row["family_robdd_status"] == "skipped"
    assert "family_robdd_build_total_time_s" in row
    assert "family_robdd_nodes_total_or_manager_if_shared" in row


def test_single_expr_skipped_and_error_helpers():
    skipped = skipped_single_backend("numba", reason="disabled")
    errored = error_result_from_exception("numba", RuntimeError("boom"))

    assert skipped["numba_status"] == "disabled"
    assert skipped["numba_time_s"] is None
    assert errored["numba_status"] == "error"
    assert "boom" in errored["numba_error"]
