import hashlib
import json

import pytest

from scripts import cm_benchmark_record_successor_authorization as subject


def request_document():
    return {
        "campaign_id": subject.CAMPAIGN,
        "status": "exact_approval_pending",
        "authorization_granted": False,
        "approval_text_to_repeat": "exact approval",
        "bound_sha256": {"runner": "abc"},
        "maximum_total_pods": 1,
        "maximum_concurrent_pods": 1,
        "maximum_phase_pod_hours": 2.0,
        "maximum_phase_runpod_charges_usd": 1.35,
        "automatic_replacement": False,
        "further_creation_after_failure": False,
    }


def test_records_exact_hash_bound_successor_authorization(tmp_path):
    request = tmp_path / "request.json"
    out = tmp_path / "authorization.json"
    request.write_text(json.dumps(request_document()), encoding="utf-8")
    expected = hashlib.sha256(request.read_bytes()).hexdigest()

    result = subject.record(request, out, expected)

    assert result["authorized"] is True
    assert result["request_sha256"] == expected
    assert result["exact_authorized_text"] == "exact approval"
    assert result["maximum_total_pods"] == 1
    assert result["automatic_replacement"] is False


def test_refuses_wrong_request_hash_and_existing_output(tmp_path):
    request = tmp_path / "request.json"
    out = tmp_path / "authorization.json"
    request.write_text(json.dumps(request_document()), encoding="utf-8")
    expected = hashlib.sha256(request.read_bytes()).hexdigest()

    with pytest.raises(RuntimeError, match="identity or bounds"):
        subject.record(request, out, "0" * 64)

    subject.record(request, out, expected)
    with pytest.raises(FileExistsError):
        subject.record(request, out, expected)
