from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import factory


ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text("utf-8"))


def test_all_authoritative_artifacts_validate_and_hashes_reproduce():
    factory.validate()


def test_schema_rejects_unknown_fields():
    brief = load("fixtures/valid/video_brief.json")
    brief["unknown"] = "refused"
    with pytest.raises(factory.FactoryError, match="schema:video_brief.*unknown"):
        factory.validate_schema("video_brief.schema.json", brief)


def test_missing_source_is_rejected():
    sources = load("source_registry.json")
    claims = load("fixtures/invalid/missing_source.claim_registry.json")
    with pytest.raises(factory.FactoryError, match="claim:missing-source"):
        factory.validate_business(sources, claims, [], verify_source_hashes=False)


def test_superseded_claim_is_rejected_outside_correction_history():
    sources = load("source_registry.json")
    claims = load("fixtures/invalid/superseded_claim.claim_registry.json")
    brief = load("fixtures/invalid/superseded_claim.video_brief.json")
    with pytest.raises(factory.FactoryError, match="brief:superseded-claim"):
        factory.validate_business(sources, claims, [brief], verify_source_hashes=False)


def test_conflicting_measurement_boundary_is_rejected():
    sources = load("source_registry.json")
    claims = load("claim_registry.json")
    brief = load("fixtures/invalid/conflicting_boundary.video_brief.json")
    with pytest.raises(factory.FactoryError, match="brief:conflicting-boundary"):
        factory.validate_business(sources, claims, [brief], verify_source_hashes=False)


def test_changed_brief_hash_is_rejected():
    sources = load("source_registry.json")
    claims = load("claim_registry.json")
    brief = load("fixtures/invalid/changed_hash.video_brief.json")
    with pytest.raises(factory.FactoryError, match="brief:changed-hash"):
        factory.validate_business(sources, claims, [brief], verify_source_hashes=False)


def test_catalog_has_two_paths_and_bounded_wave_with_negative_result():
    catalog = load("video_catalog.json")
    series = load("series_map.json")
    assert 8 <= len(catalog["first_wave"]) <= 12
    assert len(series["paths"]) >= 2
    assert "recognition-d8" in catalog["first_wave"]
    assert len(catalog["candidates"]) >= 40


def test_visual_values_recompute_from_machine_sources():
    sources = load("source_registry.json")
    rebuilt = factory.build_visual_data(sources)
    for name, value in rebuilt.items():
        assert value == load(f"visual_data/{name}")


def test_flagship_longform_contracts_validate_and_total_seven_minutes():
    factory.validate_longform(load("source_registry.json"), load("claim_registry.json"))
    episode = load("episodes/cm-flagship-representation-to-evidence-v1/episode.json")
    narration = load("episodes/cm-flagship-representation-to-evidence-v1/narration_contract.json")
    captions = load("episodes/cm-flagship-representation-to-evidence-v1/caption_contract.json")
    assert episode["target_duration_s"] == 420.0
    assert len(episode["chapters"]) == 7
    assert len(narration["cues"]) == 42
    assert {cue["cue_id"] for cue in narration["cues"]} == {
        cue["cue_id"] for cue in captions["cues"]
    }


def test_narration_contract_rejects_unknown_fields_and_binds_text_hashes():
    narration = load("episodes/cm-flagship-representation-to-evidence-v1/narration_contract.json")
    narration["unknown"] = "refused"
    with pytest.raises(factory.FactoryError, match="schema:narration_contract.*unknown"):
        factory.validate_schema("narration_contract.schema.json", narration)

    narration.pop("unknown")
    narration["cues"][0]["text"] += " changed"
    assert narration["cues"][0]["text_sha256"] != hashlib.sha256(
        narration["cues"][0]["text"].encode("utf-8")
    ).hexdigest()
