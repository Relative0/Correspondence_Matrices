"""Load the dated, privacy-reviewed post-integration confirmation bundle."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RELATIVE = Path("results/2026-09-16/cm-post-integration-confirmation")
BASE = HERE / RELATIVE
MANIFEST_SHA256 = "46fa4d19f5d70d64398b3bcefd599fd2841882372379a68ebf3c224a73547a95"


def _digest(payload):
    return hashlib.sha256(payload).hexdigest()


def build_post_integration_evidence():
    manifest_payload = (BASE / "PUBLICATION-MANIFEST.json").read_bytes()
    if _digest(manifest_payload) != MANIFEST_SHA256:
        raise ValueError("Post-integration publication manifest changed")
    manifest = json.loads(manifest_payload)
    if manifest["artifact_count"] != len(manifest["artifacts"]):
        raise ValueError("Post-integration artifact count is inconsistent")

    files = {
        (RELATIVE / "PUBLICATION-MANIFEST.json").as_posix(): manifest_payload,
        (RELATIVE / "PUBLICATION-MANIFEST.sha256").as_posix():
            (BASE / "PUBLICATION-MANIFEST.sha256").read_bytes(),
    }
    for record in manifest["artifacts"]:
        path = BASE / record["path"]
        payload = path.read_bytes()
        if len(payload) != record["bytes"] or _digest(payload) != record["sha256"]:
            raise ValueError("Changed post-integration artifact: " + record["path"])
        href = (RELATIVE / record["path"]).as_posix()
        record["href"] = href
        files[href] = payload

    summary = json.loads(files[(RELATIVE / "PUBLIC-SUMMARY.json").as_posix()])
    if summary["status"] != "verified_multi_host_confirmation":
        raise ValueError("Post-integration confirmation is not accepted")
    if not summary["symmetric_wrapper"]["windows"]["all_exact"]:
        raise ValueError("Windows symmetric confirmation is not exact")
    if not summary["symmetric_wrapper"]["linux"]["all_exact"]:
        raise ValueError("Linux symmetric confirmation is not exact")
    if not summary["corrected_e3"]["windows"]["all_exact"]:
        raise ValueError("Windows corrected-E3 confirmation is not exact")
    if not summary["corrected_e3"]["linux"]["all_exact"]:
        raise ValueError("Linux corrected-E3 confirmation is not exact")

    evidence = dict(summary)
    evidence["manifest"] = manifest
    evidence["manifest_href"] = (RELATIVE / "PUBLICATION-MANIFEST.json").as_posix()
    evidence["manifest_sha256"] = MANIFEST_SHA256
    evidence["report_href"] = (RELATIVE / "PUBLIC-REPORT.md").as_posix()
    evidence["protocol_href"] = (RELATIVE / "PUBLIC-PROTOCOL.md").as_posix()
    evidence["verification_href"] = (RELATIVE / "VERIFICATION.json").as_posix()
    return evidence, files
