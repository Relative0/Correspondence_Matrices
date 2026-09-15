from __future__ import annotations

from cmbench.comparative.gf2_multi_root import (
    prospective_sibling_output_workloads,
    sibling_output_workloads,
)
from cmbench.comparative.gf2_native_confirmation import NativeConfirmationConfig
from cmbench.recognition.yosys_native_confirmation_data import prospective_candidates
from cmbench.recognition.yosys_wide_restriction_data import candidate_pool
from cmbench.recognition.yosys_unused_gf2_data import candidate_identity


def test_prospective_single_root_candidate_freeze_is_balanced_and_disjoint() -> None:
    candidates = prospective_candidates()
    assert len(candidates) == 18
    assert {len(candidate.variable_specs) for candidate in candidates} == set(range(11, 17))
    assert all(
        sum(len(candidate.variable_specs) == width for candidate in candidates) == 3
        for width in range(11, 17)
    )
    assert not (
        {candidate_identity(candidate) for candidate in candidates}
        & {candidate_identity(candidate) for candidate in candidate_pool()}
    )


def test_prospective_multi_root_workloads_are_distinct_and_share_nodes() -> None:
    workloads = prospective_sibling_output_workloads()
    assert len(workloads) == 6
    assert not ({row.workload_id for row in workloads}
                & {row.workload_id for row in sibling_output_workloads()})
    for workload in workloads:
        assert len(workload.roots) == 3
        assert 11 <= workload.n_vars <= 16
        assert len(workload.union_document["nodes"]) < sum(
            len(document["nodes"]) for document in workload.separate_documents
        )


def test_confirmation_configuration_is_immutable() -> None:
    NativeConfirmationConfig("c37-test").validate()
    try:
        NativeConfirmationConfig("c37-test", single_blocks=6).validate()
    except ValueError:
        pass
    else:
        raise AssertionError("changed C37 block count was accepted")
