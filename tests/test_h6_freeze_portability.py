from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

from cmbench.comparative import h6_freeze_portability as portability


ROOT = Path(__file__).resolve().parents[1]


def _record(path: str, payload: bytes) -> dict[str, object]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _historical_root(destination: Path) -> Path:
    # This is the published H6 closure, not an assumption that live code has
    # stopped evolving. These sources and the binary are only read as bytes.
    archive = ROOT / 'tests/fixtures/h6_source_checkpoint.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == '6fb34b455c554679925e0b7ab262f7f61656bd8ce49e1ca347bdfc74e0dab63e'
    with zipfile.ZipFile(archive) as bundle:
        assert len(bundle.infolist()) == 32
        assert sum(info.file_size for info in bundle.infolist()) < 8 << 20
        for info in bundle.infolist():
            path = (destination / info.filename).resolve()
            assert path.is_relative_to(destination.resolve()) and not info.is_dir()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bundle.read(info))
    return destination


def test_real_h6_freeze_is_semantically_portable_without_rewriting(tmp_path: Path) -> None:
    result = portability.audit_h6_freeze(_historical_root(tmp_path))

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


def test_historical_audit_rejects_backend_and_task_source_edits(tmp_path: Path) -> None:
    root = _historical_root(tmp_path)
    frozen = (root / portability.DEFAULT_FREEZE).read_bytes()
    for relative in ('bitset_backend.py', 'cmbench/comparative/tasks.py'):
        path = root / relative
        original = path.read_bytes()
        path.write_bytes(original + b'\nSOURCE_CHANGED = True\n')
        result = portability.audit_h6_freeze(root)
        assert result['status'] == 'rejected'
        assert result['semantic_or_binary_mismatches'] == [relative]
        assert result['blockers'] == ['semantic_or_binary_binding_mismatch']
        path.write_bytes(original)
    assert (root / portability.DEFAULT_FREEZE).read_bytes() == frozen


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
