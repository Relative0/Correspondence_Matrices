from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cmbench.comparative import h6_freeze_portability as portability


ROOT = Path(__file__).resolve().parents[1]


def _record(path: str, payload: bytes) -> dict[str, object]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def test_real_h6_freeze_is_semantically_portable_without_rewriting() -> None:
    result = portability.audit_h6_freeze(ROOT)

    assert result["status"] == "verified_line_ending_equivalent"
    assert result["blockers"] == []
    assert result["semantic_or_binary_mismatches"] == []
    assert result["schedule_rows_verified"] == 708
    assert result["strict_h6_validator_replaced"] is False
    assert result["frozen_artifact_modified"] is False
    assert result["benchmark_executed"] is False
    assert result["match_modes"]["byte_exact"] > 0
    assert (
        result["match_modes"].get("lf_equivalent", 0)
        + result["match_modes"].get("crlf_equivalent", 0)
        > 0
    )


def test_text_record_accepts_only_line_ending_equivalence(tmp_path: Path) -> None:
    current = b"first\nsecond\n"
    frozen = b"first\r\nsecond\r\n"
    (tmp_path / "sample.py").write_bytes(current)

    result = portability.match_file_record(tmp_path, _record("sample.py", frozen))

    assert result["match"] is True
    assert result["match_mode"] == "crlf_equivalent"


def test_semantic_text_change_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "sample.json").write_text(
        json.dumps({"meaning": "changed"}), encoding="utf-8", newline="\n"
    )
    frozen = b'{"meaning": "frozen"}\r\n'

    result = portability.match_file_record(tmp_path, _record("sample.json", frozen))

    assert result["match"] is False
    assert result["match_mode"] == "semantic_or_binary_mismatch"


def test_binary_record_remains_byte_exact(tmp_path: Path) -> None:
    current = b"\x00\x01\n\x02"
    frozen = b"\x00\x01\r\n\x02"
    (tmp_path / "sample.dll").write_bytes(current)

    result = portability.match_file_record(tmp_path, _record("sample.dll", frozen))

    assert result["match"] is False
    assert result["text_line_endings_allowed"] is False
