from __future__ import annotations

import gzip

import pytest

from scripts.cm_benchmark_acquire import _gunzip_bounded, _select_balanced, git_blob_sha1


def test_git_blob_identity_matches_git_object_contract():
    assert git_blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_bounded_gzip_roundtrip_and_limit(monkeypatch):
    payload = b"p cnf 1 1\n1 0\n"
    assert _gunzip_bounded(gzip.compress(payload)) == payload
    monkeypatch.setattr("scripts.cm_benchmark_acquire.MAX_INPUT_BYTES", 4)
    with pytest.raises(ValueError, match="exceeds"):
        _gunzip_bounded(gzip.compress(payload))


def test_family_round_robin_selection_is_path_hash_deterministic():
    rows = [
        {"type": "blob", "path": f"root/{family}/case-{index}.cnf.gz", "size": 100,
         "sha": f"{family}{index}"}
        for family in ("a", "b") for index in range(3)
    ]
    first = _select_balanced([dict(row) for row in rows], 4, ("root/",))
    second = _select_balanced([dict(row) for row in reversed(rows)], 4, ("root/",))
    assert [row["path"] for row in first] == [row["path"] for row in second]
    assert {row["path"].split("/")[1] for row in first} == {"a", "b"}
