"""Record and validate exact first-five content and RunPod authorization.

The recorder is deliberately separate from proposal creation.  It writes no
record unless the caller supplies the current Bible, scoped review, and
canonical proposal identities exactly.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any
import uuid

import deep_series_first5_proposal as first5_proposal


HERE = Path(__file__).resolve().parent
FACTORY = HERE.parent
DEEP_ROOT = FACTORY / "deep_series"
REVIEW_ROOT = DEEP_ROOT / "first_five_review"
RUN_ROOT = HERE / "deep_series_first5_v1"
CONTENT_APPROVAL_PATH = REVIEW_ROOT / "approval.json"
AUTHORIZATION_PATH = RUN_ROOT / "authorization.json"
PROPOSAL_PATH = RUN_ROOT / "proposal.json"
REVIEW_PATH = REVIEW_ROOT / "manifest.json"
PROPOSAL_ID = "cm-video-deep-series-first5-production-remote-v1"
AUTHORIZATION_ID = PROPOSAL_ID + "-auth"

if str(FACTORY) not in sys.path:
    sys.path.insert(0, str(FACTORY))
import deep_series_first_five_review as first5_review  # noqa: E402


class AuthorizationError(RuntimeError):
    """Raised when approval evidence disagrees with the frozen proposal."""


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pending-" + uuid.uuid4().hex)
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def approval_text(
    bible_content_hash: str,
    review_manifest_sha256: str,
    proposal_identity: str,
) -> str:
    return (
        "I approve CM deep-series first-five revised content bible "
        f"`{bible_content_hash}` and scoped review manifest "
        f"`{review_manifest_sha256}` for production planning, and I approve "
        f"proposal `{PROPOSAL_ID}` exactly as stated, proposal identity "
        f"`{proposal_identity}`, including at most $2.00 RunPod spend."
    )


def current_request() -> dict[str, Any]:
    first5_review.validate()
    first5_proposal.validate()
    proposal = load(PROPOSAL_PATH)
    review = load(REVIEW_PATH)
    record = load(RUN_ROOT / "bundle_record.json")
    if (
        proposal["proposal_id"] != PROPOSAL_ID
        or proposal["content_identity"]["bible_content_hash"]
        != review["bible_content_hash"]
        or proposal["content_identity"]["review_manifest_sha256"]
        != review["review_manifest_sha256"]
        or record["bible_content_hash"] != review["bible_content_hash"]
        or record["review_manifest_sha256"] != review["review_manifest_sha256"]
    ):
        raise AuthorizationError("proposal, bundle, and scoped review identities disagree")
    return {
        "bible_content_hash": review["bible_content_hash"],
        "review_manifest_sha256": review["review_manifest_sha256"],
        "proposal_id": PROPOSAL_ID,
        "proposal_identity": proposal["proposal_sha256"],
        "proposal_file_sha256": file_sha256(PROPOSAL_PATH),
        "approval_text": approval_text(
            review["bible_content_hash"],
            review["review_manifest_sha256"],
            proposal["proposal_sha256"],
        ),
        "maximum_total_runpod_spend_usd": proposal["authorization_ceiling"][
            "maximum_total_runpod_spend_usd"
        ],
        "maximum_pod_creates": proposal["authorization_ceiling"][
            "maximum_pod_creates"
        ],
    }


def _parse_approved_at(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise AuthorizationError("approved-at is not ISO-8601") from exc
    if parsed.tzinfo is None:
        raise AuthorizationError("approved-at must include a timezone")
    return value


def record(
    *,
    bible_content_hash: str,
    review_manifest_sha256: str,
    proposal_identity: str,
    approved_by: str,
    approved_at: str,
) -> dict[str, Any]:
    request = current_request()
    supplied = (
        bible_content_hash,
        review_manifest_sha256,
        proposal_identity,
    )
    expected = (
        request["bible_content_hash"],
        request["review_manifest_sha256"],
        request["proposal_identity"],
    )
    if supplied != expected:
        raise AuthorizationError("supplied approval identities are not the current request")
    if not approved_by.strip():
        raise AuthorizationError("approved-by is required")
    approved_at = _parse_approved_at(approved_at)
    if CONTENT_APPROVAL_PATH.exists() or AUTHORIZATION_PATH.exists():
        if CONTENT_APPROVAL_PATH.exists() and AUTHORIZATION_PATH.exists():
            validate()
            existing = load(AUTHORIZATION_PATH)
            if (
                existing["bible_content_hash"],
                existing["review_manifest_sha256"],
                existing["proposal_identity"],
            ) == expected:
                return existing
        raise AuthorizationError("partial or conflicting approval evidence already exists")

    text = request["approval_text"]
    approval_identity = canonical_sha256(
        {
            "bible_content_hash": bible_content_hash,
            "review_manifest_sha256": review_manifest_sha256,
            "proposal_identity": proposal_identity,
            "approved_by": approved_by,
            "approved_at": approved_at,
        }
    )
    content_approval = {
        "schema_version": "1.0",
        "status": "approved",
        "scope": "production_planning_for_first_five_only",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "bible_content_hash": bible_content_hash,
        "review_manifest_sha256": review_manifest_sha256,
        "approval_text": text,
        "approval_text_sha256": text_sha256(text),
        "approval_identity": approval_identity,
        "content_approval_authorizes_remote_or_paid_work": False,
        "publication_authorized": False,
    }
    proposal = load(PROPOSAL_PATH)
    immutable = proposal["immutable_inputs"]
    ceiling = proposal["authorization_ceiling"]
    authorization = {
        "schema_version": "1.0",
        "authorization_id": AUTHORIZATION_ID,
        "proposal_id": PROPOSAL_ID,
        "status": "approved",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "approval_text": text,
        "approval_text_sha256": text_sha256(text),
        "approval_identity": approval_identity,
        "proposal_identity": proposal_identity,
        "proposal_file_sha256": request["proposal_file_sha256"],
        "bible_content_hash": bible_content_hash,
        "review_manifest_sha256": review_manifest_sha256,
        "bundle_sha256": immutable["bundle_sha256"],
        "batch_manifest_sha256": immutable["batch_manifest_sha256"],
        "maximum_total_runpod_spend_usd": ceiling[
            "maximum_total_runpod_spend_usd"
        ],
        "maximum_pod_creates": ceiling["maximum_pod_creates"],
        "maximum_parallel_pods": ceiling["maximum_parallel_pods"],
        "maximum_runtime_seconds_per_pod": ceiling[
            "maximum_runtime_seconds_per_pod"
        ],
        "remote_or_paid_work_authorized": True,
        "publication_authorized": False,
        "commit_or_push_authorized": False,
    }
    # A lone content approval remains fail-closed if the second atomic write fails.
    atomic_json(CONTENT_APPROVAL_PATH, content_approval)
    atomic_json(AUTHORIZATION_PATH, authorization)
    validate()
    return authorization


def validate() -> None:
    request = current_request()
    approval = load(CONTENT_APPROVAL_PATH)
    authorization = load(AUTHORIZATION_PATH)
    proposal = load(PROPOSAL_PATH)
    immutable = proposal["immutable_inputs"]
    ceiling = proposal["authorization_ceiling"]
    identities = (
        request["bible_content_hash"],
        request["review_manifest_sha256"],
        request["proposal_identity"],
    )
    approval_identity = canonical_sha256(
        {
            "bible_content_hash": approval["bible_content_hash"],
            "review_manifest_sha256": approval["review_manifest_sha256"],
            "proposal_identity": authorization["proposal_identity"],
            "approved_by": approval["approved_by"],
            "approved_at": approval["approved_at"],
        }
    )
    checks = (
        approval["status"] == "approved",
        approval["scope"] == "production_planning_for_first_five_only",
        approval["content_approval_authorizes_remote_or_paid_work"] is False,
        approval["publication_authorized"] is False,
        authorization["authorization_id"] == AUTHORIZATION_ID,
        authorization["proposal_id"] == PROPOSAL_ID,
        authorization["status"] == "approved",
        authorization["remote_or_paid_work_authorized"] is True,
        authorization["publication_authorized"] is False,
        authorization["commit_or_push_authorized"] is False,
        approval["approved_by"] == authorization["approved_by"],
        approval["approved_at"] == authorization["approved_at"],
        authorization["proposal_file_sha256"] == request["proposal_file_sha256"],
        authorization["bundle_sha256"] == immutable["bundle_sha256"],
        authorization["batch_manifest_sha256"]
        == immutable["batch_manifest_sha256"],
        authorization["maximum_total_runpod_spend_usd"]
        == ceiling["maximum_total_runpod_spend_usd"]
        == 2.0,
        authorization["maximum_pod_creates"]
        == ceiling["maximum_pod_creates"]
        == 1,
        authorization["maximum_parallel_pods"]
        == ceiling["maximum_parallel_pods"]
        == 1,
        authorization["maximum_runtime_seconds_per_pod"]
        == ceiling["maximum_runtime_seconds_per_pod"]
        == 21600,
        (
            approval["bible_content_hash"],
            approval["review_manifest_sha256"],
            authorization["proposal_identity"],
        )
        == identities,
        (
            authorization["bible_content_hash"],
            authorization["review_manifest_sha256"],
            authorization["proposal_identity"],
        )
        == identities,
        approval["approval_identity"]
        == authorization["approval_identity"]
        == approval_identity,
        approval["approval_text"] == authorization["approval_text"]
        == request["approval_text"],
        approval["approval_text_sha256"]
        == authorization["approval_text_sha256"]
        == text_sha256(request["approval_text"]),
    )
    if not all(checks):
        raise AuthorizationError("recorded approval evidence is stale or inconsistent")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("request", "record", "validate"))
    parser.add_argument("--bible-content-hash")
    parser.add_argument("--review-manifest-sha256")
    parser.add_argument("--proposal-identity")
    parser.add_argument("--approved-by", default="Brian")
    parser.add_argument("--approved-at")
    args = parser.parse_args()
    if args.command == "request":
        print(json.dumps(current_request(), indent=2))
    elif args.command == "validate":
        validate()
        print(json.dumps({"status": "approved", **current_request()}, indent=2))
    else:
        missing = [
            name
            for name, value in (
                ("--bible-content-hash", args.bible_content_hash),
                ("--review-manifest-sha256", args.review_manifest_sha256),
                ("--proposal-identity", args.proposal_identity),
            )
            if not value
        ]
        if missing:
            parser.error("record requires " + ", ".join(missing))
        approved_at = args.approved_at or datetime.now(timezone.utc).isoformat()
        result = record(
            bible_content_hash=args.bible_content_hash,
            review_manifest_sha256=args.review_manifest_sha256,
            proposal_identity=args.proposal_identity,
            approved_by=args.approved_by,
            approved_at=approved_at,
        )
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "authorization_id": result["authorization_id"],
                    "approval_identity": result["approval_identity"],
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
