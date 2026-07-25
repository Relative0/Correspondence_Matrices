from cmbench.results.timing import (
    ArtifactKind,
    TimingDescriptor,
    TimingKind,
    comparison_compatibility,
)


def test_equivalent_packed_execution_is_comparable():
    descriptor = TimingDescriptor(
        ArtifactKind.PACKED_TRUTH_FUNCTION, TimingKind.PACKED_EXECUTION
    )
    assert comparison_compatibility(descriptor, descriptor) == (True, "equivalent")


def test_symbolic_build_is_not_packed_execution():
    cudd = TimingDescriptor(ArtifactKind.SYMBOLIC_BDD, TimingKind.COMPILATION)
    bitset = TimingDescriptor(
        ArtifactKind.PACKED_TRUTH_FUNCTION, TimingKind.PACKED_EXECUTION
    )
    ok, reason = comparison_compatibility(cudd, bitset)
    assert ok is False
    assert reason.startswith("artifact_mismatch")
    assert comparison_compatibility(cudd, bitset, contextual=True) == (
        True,
        "contextual_different_artifacts",
    )


def test_same_artifact_with_different_boundaries_is_rejected():
    build = TimingDescriptor(ArtifactKind.SYMBOLIC_BDD, TimingKind.COMPILATION)
    all_in = TimingDescriptor(
        ArtifactKind.SYMBOLIC_BDD,
        TimingKind.COMPILATION,
        includes_preparation=True,
    )
    assert comparison_compatibility(build, all_in) == (False, "boundary_mismatch")
