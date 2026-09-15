from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cmbench.comparative.gf2_native_slots import (
    compile_native_slot_arena,
    load_native_slot_library,
)
from cmbench.comparative.gf2_wide_repeated_queries import (
    restrict_full_truth,
    validate_dataset,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "docs" / "recognition" / "c36_wide_repeated_query_dataset.json"


def _library_path() -> Path | None:
    explicit = os.environ.get("CM_FUSED_SLOTS_LIBRARY")
    candidates = [Path(explicit)] if explicit else []
    candidates.extend((
        ROOT / "build/cm_fused_slots/cm_fused_slots.dll",
        ROOT / "build/cm_fused_slots/Release/cm_fused_slots.dll",
        ROOT / "build/cm_fused_slots/libcm_fused_slots.so",
        ROOT / "build/cm_fused_slots/libcm_fused_slots.dylib",
        ROOT / "docs/recognition/runs/native-fused-slot-development-20260902-002/native/cm_fused_slots.dll",
    ))
    return next((path for path in candidates if path.is_file()), None)


@pytest.mark.skipif(_library_path() is None, reason="native fused slot library not built")
def test_native_slots_match_all_exposed_c36_queries() -> None:
    library_path = _library_path()
    assert library_path is not None
    library = load_native_slot_library(library_path)
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    checked = 0
    for case in dataset["cases"]:
        arena = compile_native_slot_arena(case["expression_v2"], library)
        assert arena.variable_count == case["n_vars"]
        bits = int(case["truth_bits_hex"], 16)
        for query in case["c36_trace"]:
            fixed = {row["variable"]: row["value"] for row in query["fixed"]}
            remaining, expected = restrict_full_truth(bits, case["n_vars"], fixed)
            assert remaining == tuple(query["remaining_order"])
            bindings = arena.prepare_bindings(fixed, remaining)
            assert arena.evaluate(bindings, len(remaining)) == expected
            checked += 1
    assert checked == 18 * 64
