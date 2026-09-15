from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from bitset_backend import bitset_to_bool_array
from cmbench.comparative.gf2_projection_optimized import (
    compile_flat_projection_plan,
    compile_packed_cofactor_plan,
    minimum_projection_dtype,
    project_packed_truth,
    projection_indices_typed,
)
from cmbench.comparative.gf2_wide_repeated_queries import (
    project_truth_vector,
    projection_indices,
    restrict_full_truth,
    validate_dataset,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "docs" / "recognition" / "c36_wide_repeated_query_dataset.json"


def _cases() -> list[dict[str, object]]:
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    return dataset["cases"]


@pytest.mark.parametrize(
    ("n_vars", "expected"),
    [(8, np.dtype(np.uint8)), (9, np.dtype(np.uint16)),
     (16, np.dtype(np.uint16)), (17, np.dtype(np.uint32))],
)
def test_minimum_projection_dtype(n_vars: int, expected: np.dtype[object]) -> None:
    assert minimum_projection_dtype(n_vars) == expected


def test_typed_flat_and_packed_projection_match_all_exposed_c36_queries() -> None:
    checked = 0
    for case in _cases():
        n_vars = int(case["n_vars"])
        bits = int(str(case["truth_bits_hex"]), 16)
        vector = bitset_to_bool_array(bits, n_vars)
        trace = case["c36_trace"]
        flat = compile_flat_projection_plan(n_vars, trace)
        assert flat.dtype_name == "uint16"
        assert flat.index_bytes * 2 == sum(
            projection_indices(
                n_vars,
                {row["variable"]: row["value"] for row in query["fixed"]},
                query["remaining_order"],
            ).nbytes
            for query in trace
        )
        for query_index, query in enumerate(trace):
            fixed = {row["variable"]: row["value"] for row in query["fixed"]}
            remaining, expected = restrict_full_truth(bits, n_vars, fixed)
            assert remaining == tuple(query["remaining_order"])
            typed = projection_indices_typed(
                n_vars, fixed, query["remaining_order"])
            assert typed.dtype == np.uint16
            assert np.array_equal(
                typed.astype(np.uint32),
                projection_indices(n_vars, fixed, query["remaining_order"]),
            )
            assert project_truth_vector(vector, typed) == expected
            assert project_truth_vector(vector, flat.query_indices(query_index)) == expected
            packed = compile_packed_cofactor_plan(
                n_vars, fixed, query["remaining_order"])
            assert project_packed_truth(bits, packed) == expected
            checked += 1
    assert checked == 18 * 64


def test_projection_rejects_an_index_dtype_that_is_too_narrow() -> None:
    with pytest.raises(ValueError, match="too narrow"):
        projection_indices_typed(
            9,
            {"x0": 0},
            tuple(f"x{index}" for index in range(1, 9)),
            dtype=np.uint8,
        )
