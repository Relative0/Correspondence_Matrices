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


def test_v2_content_bible_locks_audited_51_episode_curriculum():
    bible = load("deep_series/episode_content_bible.json")
    factory.validate_episode_content_bible(
        bible, load("claim_registry.json"), load("source_registry.json")
    )
    episode_ids = [episode["video_id"] for episode in bible["episodes"]]
    assert bible["schema_version"] == "2.0"
    assert bible["baseline_episode_count"] == 51
    assert len(episode_ids) == 51
    assert episode_ids[0] == "conceptual-vs-measured"
    assert episode_ids[-1] == "source-hash-reproduction"
    assert episode_ids.index("instruction-operations-memory") > episode_ids.index(
        "cm-ir-vs-cse-flat-mechanism"
    )
    assert episode_ids.index("no-fastest-chart") > episode_ids.index("read-a-ratio")
    assert {
        "recognition-c9-c11", "recognition-c12-c16", "recognition-d10", "recognition-e1-e2"
    }.issubset(episode_ids)


def test_v2_episode_content_is_specific_and_reviewable():
    bible = load("deep_series/episode_content_bible.json")
    visual_spines = []
    for episode in bible["episodes"]:
        assert 6 <= len(episode["teaching_beats"]) <= 10
        assert len(episode["visual_spine"]) >= 3
        assert all("show boxes" not in beat.lower() for beat in episode["teaching_beats"])
        assert all("add diagram later" not in beat.lower() for beat in episode["teaching_beats"])
        assert all(episode["dialogue_anchors"].values())
        assert episode["source_ids"]
        assert episode["retrieval_check"]
        assert episode["misconceptions"]
        assert episode["caveats"]
        assert episode["references"]
        covered_beats = [
            number
            for chapter in episode["chapter_plan"]
            for number in chapter["teaching_beat_numbers"]
        ]
        assert covered_beats == list(range(1, len(episode["teaching_beats"]) + 1))
        assert episode["visual_contract"]["minimum_distinct_compositions"] >= 15
        assert episode["visual_contract"]["minimum_meaningful_state_changes"] >= 38
        assert len(episode["visual_contract"]["required_asset_kinds"]) >= 5
        visual_spines.append(tuple(episode["visual_spine"]))
    assert len(visual_spines) == len(set(visual_spines))


def test_v2_content_approval_is_required_and_not_runpod_authorization():
    gate = load("deep_series/episode_content_bible.json")["approval_gate"]
    assert gate["required"] is True
    assert gate["separate_from_runpod_authorization"] is True
    request_path = ROOT / "deep_series" / "content_review_request.json"
    approval_path = ROOT / "deep_series" / "production_planning" / "content_approval.json"
    if request_path.is_file():
        request = json.loads(request_path.read_text("utf-8"))
        assert gate["review_manifest_sha256"] == request["review_manifest_sha256"]
        assert request["content_approval_authorizes_remote_or_paid_work"] is False
        if approval_path.is_file():
            approval = json.loads(approval_path.read_text("utf-8"))
            assert gate["status"] == "approved"
            assert gate["approval_identity"] == approval["approval_identity"]
            assert gate["approved_by"] == approval["approved_by"]
            assert gate["approved_at"] == approval["approved_at"]
            assert approval["content_approval_authorizes_remote_or_paid_work"] is False
        else:
            expected_status = (
                "review_requested"
                if request["bible_content_hash"] == load("deep_series/episode_content_bible.json")["content_hash"]
                else "stale"
            )
            assert gate["status"] == expected_status
            assert gate["approved_by"] is None
            assert gate["approved_at"] is None
            assert gate["approval_identity"] is None
    else:
        assert gate["status"] == "not_requested"
        assert gate["review_manifest_sha256"] is None
        assert gate["approved_by"] is None
        assert gate["approved_at"] is None
        assert gate["approval_identity"] is None
    assert {
        "scripts", "claim_maps", "storyboards", "visual_directors",
        "representative_previews",
    }.issubset(gate["required_artifact_types"])


def test_v2_content_bible_rejects_drift_and_late_prerequisites():
    claims = load("claim_registry.json")
    sources = load("source_registry.json")
    changed = load("deep_series/episode_content_bible.json")
    changed["dialogue_rules"][0] += " changed"
    with pytest.raises(factory.FactoryError, match="content-bible:changed-root-hash"):
        factory.validate_episode_content_bible(changed, claims, sources)

    late = load("deep_series/episode_content_bible.json")
    late["episodes"][0]["prerequisite_ids"] = ["source-hash-reproduction"]
    with pytest.raises(factory.FactoryError, match="content-bible:late-prerequisite"):
        factory.validate_episode_content_bible(late, claims, sources)


def test_v2_content_identity_is_stable_across_review_state_changes():
    bible = load("deep_series/episode_content_bible.json")
    content_hash = bible["content_hash"]
    bible["approval_gate"].update({
        "status": "stale",
        "approved_by": None,
        "approved_at": None,
        "approval_identity": None,
    })
    factory.validate_episode_content_bible(
        bible, load("claim_registry.json"), load("source_registry.json")
    )
    assert bible["content_hash"] == content_hash


def test_claim_registry_covers_representation_execution_and_current_crse_program():
    claim_ids = {claim["id"] for claim in load("claim_registry.json")["claims"]}
    assert {
        "cm-ir-sharing-roots",
        "cm-ir-normalization-interning",
        "cm-ir-persistence-contract",
        "flat-program-lowering",
        "packed-truth-vector-contract",
        "parallel-materialization-contract",
        "source-provenance-contract",
        "crse-current-program-map",
        "crse-initial-learning-slice",
        "crse-c9-c11-negative",
        "crse-c12-c16-exact",
        "crse-d10-negative",
        "crse-e1-e2-guidance",
    }.issubset(claim_ids)


def test_initial_crse_learning_slice_has_explicit_orientation_coverage():
    episode = next(
        item for item in load("deep_series/episode_content_bible.json")["episodes"]
        if item["video_id"] == "recognition-question"
    )
    assert "crse-initial-learning-slice" in episode["claim_ids"]
    assert "initial matrix/graph/fused/retrieval learning baseline" in episode["owns"]
    assert any("matrix/graph/fused/retrieval baseline" in chapter["working_title"] for chapter in episode["chapter_plan"])


def test_c9_c11_exact_routing_progression_is_not_hidden_inside_c12():
    claims = {claim["id"]: claim for claim in load("claim_registry.json")["claims"]}
    claim = claims["crse-c9-c11-negative"]
    assert "C9 static routing" in claim["allowed_wording"]
    assert "C10 guarded restart" in claim["allowed_wording"]
    assert "C11 one-pass conversion" in claim["allowed_wording"]
    assert claim["status"] == "negative"
    episode = next(
        item for item in load("deep_series/episode_content_bible.json")["episodes"]
        if item["video_id"] == "recognition-c9-c11"
    )
    assert episode["claim_ids"] == ["crse-c9-c11-negative", "crse-current-program-map"]
    assert episode["prerequisite_ids"] == ["recognition-c6"]
    assert len(episode["chapter_plan"]) == 4


def test_latest_c16_linux_confirmation_is_reflected_without_universalizing_it():
    claims = {claim["id"]: claim for claim in load("claim_registry.json")["claims"]}
    c16_claim = claims["crse-c12-c16-exact"]
    assert "3.178x Linux" in c16_claim["allowed_wording"]
    assert "tiny-case regression" in c16_claim["allowed_wording"]
    assert {ref["source_id"] for ref in c16_claim["sources"]} == {
        "src-recognition-register", "src-c16-report", "src-c16-linux-v2-final"
    }
    episode = next(
        item for item in load("deep_series/episode_content_bible.json")["episodes"]
        if item["video_id"] == "recognition-c12-c16"
    )
    assert "passed the corrected Linux second-machine gate" in episode["caveats"][0]
    assert "fresh non-XOR-heavy family remains untested" in episode["caveats"][0]
    assert [chapter["working_title"] for chapter in episode["chapter_plan"]][-2:] == [
        "C15 reconstructible GF(2) artifacts",
        "C16 screened materialization: local and Linux evidence",
    ]


def test_content_readiness_audit_is_hash_bound_and_honest_about_pending_work():
    bible = load("deep_series/episode_content_bible.json")
    audit = load("deep_series/content_readiness_audit.json")
    factory.validate_content_readiness_audit(audit, bible, load("glossary.json"))
    assert audit["status"] == "ready_for_script_and_storyboard_authoring"
    assert audit["summary"]["episodes"] == 51
    assert audit["summary"]["glossary_terms"] >= 16
    assert audit["summary"]["planned_chapters"] == 203
    assert audit["summary"]["visual_systems"] >= 150
    assert audit["summary"]["minimum_distinct_compositions"] >= 1100
    statuses = {gate["gate_id"]: gate["status"] for gate in audit["gates"]}
    assert statuses["curriculum-coverage"] == "pass"
    assert statuses["visual-authoring-readiness"] == "pass"
    assert statuses["complete-scripts"] == "pending"
    assert statuses["storyboards-assets-previews"] == "pending"
    assert statuses["human-content-approval"] == "pending"


def test_catalog_is_generated_from_bible_and_has_one_rendered_flagship():
    bible = load("deep_series/episode_content_bible.json")
    catalog = load("video_catalog.json")
    proposed = [item for item in catalog["candidates"] if item["status"] == "proposed"]
    rendered = [item for item in catalog["candidates"] if item["status"] == "rendered"]
    assert len(catalog["candidates"]) == len(bible["episodes"]) + 1
    assert [item["video_id"] for item in proposed] == [
        episode["video_id"] for episode in bible["episodes"]
    ]
    assert [item["video_id"] for item in rendered] == [
        "cm-flagship-representation-to-evidence-v1"
    ]


def test_v2_master_prompt_requires_both_content_and_runpod_gates():
    prompt = (ROOT / "RUNPOD_DEEP_SERIES_MASTER_PROMPT_V2.md").read_text("utf-8")
    assert "LOCKED BASELINE — 51 UNPRODUCED EPISODES" in prompt
    assert "PHASE 6.5 — MANDATORY CONTENT-APPROVAL GATE" in prompt
    assert "SEPARATE RUNPOD AUTHORIZATION GATE" in prompt
    assert "recognition-c12-c16" in prompt
    assert "recognition-c9-c11" in prompt
    assert "recognition-d10" in prompt
    assert "recognition-e1-e2" in prompt


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
