import pandas as pd

from cmbench.results.aggregation import build_agg_spec, safe_all, safe_any, safe_first, safe_median
from cmbench.results.flatten import flatten_backend_result
from cmbench.results.schema import BackendResult


def test_aggregation_helpers():
    s = pd.Series([1.0, None, 3.0])
    assert safe_median(s) == 2.0
    assert safe_first(s) == 1.0
    assert safe_all(pd.Series([True, True, None])) is True
    assert safe_any(pd.Series([False, True, None])) is True

    spec = build_agg_spec(["value"], first_cols=["name"], all_cols=["ok"])
    assert set(spec) == {"value_median", "name", "ok_all"}


def test_backend_result_error_alias_and_flattening():
    result = BackendResult.error("backend", ValueError("bad"))
    row = flatten_backend_result(result)

    assert row["backend_status"] == "error"
    assert "bad" in row["backend_error"]
