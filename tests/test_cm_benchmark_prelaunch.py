from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]

from cmbench.campaign_prelaunch import (
    Candidate,
    admit_candidate,
    build_admission_ledger,
    build_arm_manifest,
    build_schedule_ledger,
    build_upload_bundle,
    build_upload_bundles,
    safe_relative_path,
    sha256_file,
    source_identity,
    synthetic_specs,
    verify_upload_bundle,
    verify_upload_bundles,
)


def candidate(path: Path, root: Path, *, kind="cnf", digest=None, license_path="LICENSE") -> Candidate:
    return Candidate(
        case_id="case-1", group="feature_models", family_id="F01", cluster_id="system-1",
        role="regression", path=path.relative_to(root).as_posix(), kind=kind,
        source_url="https://example.invalid/source", source_revision="1" * 40,
        expected_sha256=digest or hashlib.sha256(path.read_bytes()).hexdigest(), license_spdx="MIT",
        license_path=license_path, redistribution="permitted_with_license_notice",
    )


def test_safe_paths_refuse_traversal_secrets_and_windows_absolute_paths():
    for value in ("../x", "/absolute", "C:/absolute", "a\\b", ".env", "data/token-cache.json"):
        with pytest.raises(ValueError):
            safe_relative_path(value)
    assert safe_relative_path("inputs/a.cnf") == "inputs/a.cnf"


def test_source_identity_marks_dirty_or_untracked_files_and_hashes_exact_bytes():
    record = source_identity(ROOT, ["cmbench/campaign_prelaunch.py"])
    assert record["schema"] == "cm-benchmark-source-identity/v1"
    assert record["workspace_dirty_in_scope"] is True
    assert record["files"][0]["git_state"] in {
        "untracked", "tracked_modified", "tracked_staged", "tracked_staged_and_modified",
    }
    assert record["files"][0]["sha256"] == sha256_file(ROOT / "cmbench/campaign_prelaunch.py")


def test_dimacs_admission_checks_hash_license_and_semantics(tmp_path: Path):
    (tmp_path / "LICENSE").write_text("MIT\n", encoding="utf-8")
    source = tmp_path / "valid.cnf"
    source.write_text("c fixture\np cnf 3 2\n1 -2 0\n3 0\n", encoding="utf-8")
    row = admit_candidate(tmp_path, candidate(source, tmp_path))
    assert row["state"] == "admitted"
    assert row["metadata"]["variables"] == 3
    assert row["metadata"]["clauses"] == 2

    changed = admit_candidate(tmp_path, candidate(source, tmp_path, digest="0" * 64))
    assert changed["state"] == "rejected"
    assert "SHA-256" in changed["reason"]

    projected = tmp_path / "projected.cnf"
    projected.write_text("c ind 1 0\np cnf 1 1\n1 0\n", encoding="utf-8")
    refused = admit_candidate(tmp_path, candidate(projected, tmp_path))
    assert refused["state"] == "rejected"
    assert "separate declared contract" in refused["reason"]


def test_executable_payload_is_rejected_before_parser(tmp_path: Path):
    (tmp_path / "LICENSE").write_text("MIT\n", encoding="utf-8")
    source = tmp_path / "fake.cnf"
    source.write_bytes(b"MZ" + b"0" * 20)
    row = admit_candidate(tmp_path, candidate(source, tmp_path))
    assert row["state"] == "rejected"
    assert "executable payload" in row["reason"]


def test_bnet_fixed_point_admission_requires_a_closed_model(tmp_path: Path):
    (tmp_path / "LICENSE").write_text("CC-BY-4.0\n", encoding="utf-8")
    source = tmp_path / "model.bnet"
    source.write_text("targets,factors\na, external\n", encoding="utf-8")
    base = candidate(source, tmp_path, kind="bnet")
    selected = Candidate(**{**base.__dict__, "selector": "a"})
    refused = admit_candidate(tmp_path, selected)
    assert refused["state"] == "rejected"
    assert refused["reason"] == "BNet fixed-point model is not closed under declared targets"

    source.write_text("targets,factors\na, b\nb, !a\n", encoding="utf-8")
    selected = Candidate(**{
        **base.__dict__,
        "selector": "a",
        "expected_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    })
    admitted = admit_candidate(tmp_path, selected)
    assert admitted["state"] == "admitted"
    assert admitted["metadata"]["closed_under_declared_targets"] is True
    assert admitted["metadata"]["undeclared_regulators"] == []


def test_admission_and_schedule_keep_shortfalls_visible(tmp_path: Path):
    (tmp_path / "LICENSE").write_text("MIT\n", encoding="utf-8")
    source = tmp_path / "one.cnf"
    source.write_text("p cnf 1 1\n1 0\n", encoding="utf-8")
    admitted = build_admission_ledger(tmp_path, "campaign", [candidate(source, tmp_path)], created_utc="2026-09-13T00:00:00Z")
    schedule = build_schedule_ledger("campaign", admitted, synthetic_specs(count=600), created_utc="2026-09-13T00:00:00Z")
    assert len(schedule["rows"]) == 2400
    assert sum(row["state"] == "planned" for row in schedule["rows"]) == 601
    assert sum(row["state"] == "not_run" for row in schedule["rows"]) == 1799
    biology = [row for row in schedule["rows"] if row["group"] == "biological_functions"]
    assert all(row["state"] == "not_run" and row["reason"] == "corpus_quota_shortfall" for row in biology)


def test_prior_refusals_remain_in_admission_ledger(tmp_path: Path):
    refused = {"case_id": "refused", "group": "feature_models", "state": "rejected",
               "reason": "prior_manifest_refusal:oversized"}
    ledger = build_admission_ledger(
        tmp_path, "campaign", [], created_utc="2026-09-13T00:00:00Z", prior_rows=[refused],
    )
    assert ledger["rows"] == [refused]
    assert ledger["summary"]["states"] == {"rejected": 1}


def test_synthetic_specs_are_balanced_deterministic_and_labeled():
    first = synthetic_specs()
    second = synthetic_specs()
    assert first == second
    assert len(first) == 600
    counts = {}
    for row in first:
        counts[row["spec"]["family"]] = counts.get(row["spec"]["family"], 0) + 1
        assert "never real-world" in row["provenance"]
    assert max(counts.values()) - min(counts.values()) <= 1
    assert {row["spec"]["width"] for row in first} == {4, 8, 12, 16, 20, 24, 28, 32}


def test_reduced_arm_scope_plans_only_verified_adapters():
    readiness = {"rows": [
        {"adapter": "exact_count.ganak", "state": "present_verified"},
        {"adapter": "gf2.m4ri", "state": "present_unverified"},
        {"adapter": "hardware.yosys_transform", "state": "missing"},
    ]}
    manifest = build_arm_manifest("campaign", readiness, created_utc="2026-09-13T00:00:00Z")
    assert manifest["summary"] == {"not_run": 2, "planned": 1}
    assert manifest["outcome_responsive_changes_permitted"] is False
    assert [row["adapter"] for row in manifest["rows"] if row["state"] == "planned"] == ["exact_count.ganak"]


def test_deterministic_bundle_has_exact_safe_manifest(tmp_path: Path):
    root = tmp_path / "root"
    out = tmp_path / "out"
    root.mkdir()
    (root / "source.py").write_text("x = 1\n", encoding="utf-8")
    manifest = build_upload_bundle(root, out, "campaign", [{"source": "source.py", "archive": "source/source.py"}],
                                   {"manifests/freeze.json": b"{}\n"})
    checked = verify_upload_bundle(out, manifest)
    assert checked["verified"]
    assert manifest["upload_authorized"] is False
    assert manifest["excluded"][0] == ".env*"
    with zipfile.ZipFile(out / "SOURCE_BUNDLE.zip") as archive:
        assert set(archive.namelist()) == {row["archive"] for row in manifest["contents"]}

    changed = json.loads(json.dumps(manifest))
    changed["contents"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="identity"):
        verify_upload_bundle(out, changed)


def test_deterministic_upload_shards_cover_every_member_once(tmp_path: Path):
    root = tmp_path / "root"
    out = tmp_path / "out"
    root.mkdir()
    entries = []
    for index in range(3):
        path = root / f"input-{index}.cnf"
        path.write_bytes(bytes([65 + index]) * 1800)
        entries.append({"source": path.name, "archive": "inputs/" + path.name})
    manifest = build_upload_bundles(
        root, out, "campaign", entries, {"manifests/freeze.json": b"{}\n"}, maximum_expanded=4096,
    )
    checked = verify_upload_bundles(out, manifest)
    assert checked["verified"] and checked["bundles"] >= 2
    assert manifest["upload_scope"] == [row["path"] for row in manifest["bundles"]]
    assert all(row["expanded_bytes"] <= row["expanded_limit"] for row in manifest["bundles"])
