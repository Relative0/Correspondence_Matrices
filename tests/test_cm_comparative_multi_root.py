from __future__ import annotations

import os
from pathlib import Path

import pytest

from bitset_backend import build_bitset_env, eval_expr_bitset
from cmbench.comparative.gf2_multi_root import sibling_output_workloads
from cmbench.comparative.gf2_native_slots import (
    compile_native_multi_root_arena,
    compile_native_slot_arena,
    load_native_slot_library,
)
from cmbench.comparative.gf2_wide_repeated_queries import restrict_full_truth


ROOT = Path(__file__).resolve().parents[1]


def _direct_arithmetic_truths(workload_id: str) -> tuple[int, int, int]:
    rows = 1 << 16
    packed = [bytearray(rows // 8) for _ in range(3)]
    for assignment in range(rows):
        values = [
            (assignment >> (15 - index)) & 1
            for index in range(16)
        ]
        if workload_id == "multi-multiply8-bits345":
            number = sum(values[i] << i for i in range(8)) * sum(
                values[8 + i] << i for i in range(8))
            output_bits = (3, 4, 5)
        elif workload_id == "multi-multiply8-bits567":
            number = sum(values[i] << i for i in range(8)) * sum(
                values[8 + i] << i for i in range(8))
            output_bits = (5, 6, 7)
        elif workload_id == "multi-add8-bits456":
            number = sum(values[i] << i for i in range(8)) + sum(
                values[8 + i] << i for i in range(8))
            output_bits = (4, 5, 6)
        elif workload_id == "multi-popcount16-bits123":
            number = sum(values)
            output_bits = (1, 2, 3)
        elif workload_id == "multi-addertree4x4-bits234":
            number = sum(
                sum(values[word * 4 + bit] << bit for bit in range(4))
                for word in range(4)
            )
            output_bits = (2, 3, 4)
        elif workload_id == "multi-muladd5x5c6-bits345":
            number = (
                sum(values[i] << i for i in range(5))
                * sum(values[5 + i] << i for i in range(5))
                + sum(values[10 + i] << i for i in range(6))
            )
            output_bits = (3, 4, 5)
        else:
            raise AssertionError(workload_id)
        for output_index, bit in enumerate(output_bits):
            if number & (1 << bit):
                packed[output_index][assignment >> 3] |= 1 << (assignment & 7)
    return tuple(int.from_bytes(value, "little") for value in packed)


def _library_path() -> Path | None:
    explicit = os.environ.get("CM_FUSED_SLOTS_LIBRARY")
    candidates = [Path(explicit)] if explicit else []
    candidates.extend((
        ROOT / "build/cm_fused_slots_multi/cm_fused_slots.dll",
        ROOT / "build/cm_fused_slots_multi/libcm_fused_slots.so",
        ROOT / "build/cm_fused_slots_multi/libcm_fused_slots.dylib",
        ROOT / "docs/recognition/runs/native-multi-root-development-20260902-002/native/cm_fused_slots.dll",
    ))
    return next((path for path in candidates if path.is_file()), None)


def test_sibling_workloads_have_real_union_sharing() -> None:
    for workload in sibling_output_workloads():
        separate_nodes = sum(len(document["nodes"])
                             for document in workload.separate_documents)
        union_nodes = len(workload.union_document["nodes"])
        assert union_nodes < separate_nodes
        assert separate_nodes / union_nodes >= 1.10


def test_sibling_workloads_match_independent_scalar_arithmetic() -> None:
    names = tuple(f"x{index}" for index in range(16))
    for workload in sibling_output_workloads():
        expression_truths = tuple(
            eval_expr_bitset(root, build_bitset_env(names))
            for root in workload.roots
        )
        assert expression_truths == _direct_arithmetic_truths(workload.workload_id)


@pytest.mark.skipif(_library_path() is None, reason="multi-root native library not built")
def test_native_multi_root_matches_separate_and_scalar_oracles() -> None:
    path = _library_path()
    assert path is not None
    library = load_native_slot_library(path)
    assert library.supports_multi_root
    checked = 0
    for workload in sibling_output_workloads():
        union = compile_native_multi_root_arena(
            workload.union_document, library, variable_count=workload.n_vars)
        separate = tuple(
            compile_native_slot_arena(
                document, library, variable_count=workload.n_vars)
            for document in workload.separate_documents
        )
        names = tuple(f"x{index}" for index in range(workload.n_vars))
        full_truths = tuple(
            eval_expr_bitset(root, build_bitset_env(names)) for root in workload.roots)
        for query in workload.trace:
            fixed = {row["variable"]: row["value"] for row in query["fixed"]}
            remaining = tuple(query["remaining_order"])
            bindings = union.prepare_bindings(fixed, remaining)
            multi_values = union.evaluate(bindings, len(remaining))
            separate_values = tuple(
                arena.evaluate(bindings, len(remaining)) for arena in separate)
            expected = tuple(
                restrict_full_truth(bits, workload.n_vars, fixed)[1]
                for bits in full_truths)
            assert multi_values == separate_values == expected
            checked += len(expected)
    assert checked == 6 * 64 * 3
