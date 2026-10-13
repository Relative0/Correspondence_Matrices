from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

from cmbench.comparative.gf2_native_slot_batch import (
    NativeSlotBatchExecutor,
    prepare_bindings_many,
)
from cmbench.comparative.gf2_native_slots import (
    compile_native_slot_arena,
    load_native_slot_library,
)
from cmbench.comparative.gf2_wide_repeated_queries import (
    restrict_full_truth,
    validate_dataset,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"


def _library_path() -> Path | None:
    explicit = os.environ.get("CM_FUSED_SLOTS_BATCH_LIBRARY")
    candidates = [Path(explicit)] if explicit else []
    candidates.extend(
        (
            ROOT / "build/cm_fused_slots_batch/cm_fused_slots_batch.dll",
            ROOT / "build/cm_fused_slots_batch/libcm_fused_slots_batch.so",
            ROOT / "build/cm_fused_slots_batch/libcm_fused_slots_batch.dylib",
        )
    )
    return next((path for path in candidates if path.is_file()), None)


def test_prepare_bindings_many_preserves_query_and_residual_order() -> None:
    class Arena:
        variable_count = 4

    bindings, live_counts = prepare_bindings_many(
        Arena(),
        (
            ({"x0": 0, "x3": 1}, ("x2", "x1")),
            ({"x1": 1}, ("x3", "x0", "x2")),
        ),
    )
    assert bindings.dtype == np.int16
    assert bindings.flags.writeable is False
    assert bindings.tolist() == [[-1, 1, 0, -2], [1, -2, 2, 0]]
    assert live_counts == (2, 3)


def test_prepare_bindings_many_rejects_invalid_partitions() -> None:
    class Arena:
        variable_count = 3

    with pytest.raises(ValueError, match="batch restriction"):
        prepare_bindings_many(Arena(), (({"x0": 0}, ("x1",)),))


@pytest.mark.skipif(
    _library_path() is None,
    reason="native fused-slot batch successor library not built",
)
def test_native_batch_matches_scalar_and_independent_c36_oracles() -> None:
    path = _library_path()
    assert path is not None
    library = load_native_slot_library(path)
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    checked = 0
    observed_widths: set[int] = set()
    for case in dataset["cases"]:
        arena = compile_native_slot_arena(case["expression_v2"], library)
        batch = NativeSlotBatchExecutor(arena)
        bits = int(case["truth_bits_hex"], 16)
        queries = []
        expected = []
        scalar = []
        for query in case["c36_trace"]:
            fixed = {row["variable"]: row["value"] for row in query["fixed"]}
            remaining, oracle = restrict_full_truth(bits, case["n_vars"], fixed)
            queries.append((fixed, remaining))
            expected.append(oracle)
            observed_widths.add(len(remaining))
            prepared = arena.prepare_bindings(fixed, remaining)
            scalar.append(arena.evaluate(prepared, len(remaining)))
        assert batch.evaluate_queries(queries) == tuple(scalar) == tuple(expected)
        checked += len(queries)
    assert checked == 18 * 64
    assert len(observed_widths) >= 2
