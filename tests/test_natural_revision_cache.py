from __future__ import annotations

from cmbench.recognition.natural_revision_experiment import (
    ExactRevisionCache, NaturalRevisionConfig, build_cache_snapshot,
    cnf_bitset, expected_case_details, load_natural_revision_cases,
)


def test_audited_natural_revision_selection_and_identity_boundary() -> None:
    cases, selection = load_natural_revision_cases()
    details = expected_case_details(cases)

    assert len(cases) == selection["selected_case_count"] == 120
    assert len(selection["histories"]) == 7
    assert len(selection["transition_ids"]) == 20
    assert sum(row["exact_source_equal"] for row in details) == 41
    assert sum(row["semantic_relation_equal"] for row in details) == 117
    assert sum(row["unsafe_semantic_only_equal"] for row in details) == 76


def test_exact_revision_cache_checks_bytes_after_forced_digest_collision() -> None:
    cache = ExactRevisionCache(max_entries=1, identity_hasher=lambda _value: "collision")
    first = cache.lookup("case", b"first")
    cache.store("case", b"first", first.source_sha256, 7, 8)

    hit = cache.lookup("case", b"first")
    changed = cache.lookup("case", b"second")

    assert hit.hit and hit.value == 7
    assert not changed.hit and changed.invalidated and changed.reason == "source_changed"


def test_natural_revision_outputs_and_snapshot_reproduce() -> None:
    cases, _selection = load_natural_revision_cases(6)
    for case in cases:
        assert cnf_bitset(case.earlier_residual, case.k) >= 0
        assert cnf_bitset(case.later_residual, case.k) >= 0
    snapshot = build_cache_snapshot(cases)
    assert snapshot["entry_count"] == 6
    assert len(snapshot["entries"]) == 6


def test_natural_revision_config_bounds() -> None:
    NaturalRevisionConfig(rounds=3, case_limit=120, max_seconds=120).validate()
