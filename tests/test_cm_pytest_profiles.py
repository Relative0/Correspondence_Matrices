from types import SimpleNamespace
from pathlib import Path

from cmbench import pytest_profiles as profiles


def test_windows_profile_is_exactly_bound_to_both_audits() -> None:
    profile = profiles.validate_profile()
    summary = profiles.profile_summary(profile)

    assert summary["profile"] == "windows-supported"
    assert summary["historical_replay_tests"] == 76
    assert summary["optional_modules"] == 9
    assert summary["collection_refusal_modules"] == 8
    assert summary["all_skipped_modules"] == 1
    assert sum(
        record["kind"] == "collection_refusal"
        for record in profile.optional.values()
    ) == 8
    assert profile.optional["tests/test_bucket_cudd_reference.py"] == {
        "kind": "all_skipped",
        "reason": "optional CUDD binding is absent",
    }


def test_historical_evidence_hash_is_stable_across_checkout_line_endings(
    tmp_path: Path,
) -> None:
    lf = tmp_path / "lf.json"
    crlf = tmp_path / "crlf.json"
    lf.write_bytes(b'{"value": 1}\n')
    crlf.write_bytes(b'{"value": 1}\r\n')

    assert profiles.sha256_lf(lf) == profiles.sha256_lf(crlf)
    assert profiles.sha256(lf) != profiles.sha256(crlf)


def test_item_key_matches_junit_classname_contract() -> None:
    item = SimpleNamespace(
        nodeid="tests/test_example.py::ExampleTests::test_case",
        cls=type("ExampleTests", (), {}),
        name="test_case",
    )
    assert profiles.item_key(item) == (
        "tests.test_example.ExampleTests",
        "test_case",
    )
    item.cls = None
    item.nodeid = r"tests\test_example.py::test_case"
    assert profiles.item_key(item) == ("tests.test_example", "test_case")


def test_historical_inventory_check_fails_closed() -> None:
    expected = {("tests.test_a", "test_one"), ("tests.test_b", "test_two")}
    assert profiles.missing_historical_keys(expected, expected) == set()
    assert profiles.missing_historical_keys(
        {("tests.test_a", "test_one")}, expected
    ) == {("tests.test_b", "test_two")}
