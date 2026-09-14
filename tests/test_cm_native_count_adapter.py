from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from cmbench.backends.native_count import (
    D4_CACHE_ADDITIONAL_PAGE_BYTES,
    D4_CACHE_FIRST_PAGE_BYTES,
    run_d4,
    run_ganak,
)


def _completed(command, **_kwargs):
    return CompletedProcess(command, 0, "s SATISFIABLE\nc s exact arb int 2\n", "")


def test_ganak_adapter_pins_deterministic_exact_flags_and_projection(tmp_path: Path, monkeypatch):
    source = tmp_path / "projected.cnf"
    source.write_text("c ind 1 0\np cnf 3 1\n2 3 0\n", encoding="utf-8")
    monkeypatch.setattr("cmbench.backends.native_count.subprocess.run", _completed)
    result = run_ganak(source, mode="projected", executable="/opt/pinned/ganak", threads=1)
    assert result.count == 2
    assert result.command[:9] == (
        "/opt/pinned/ganak", "--verb", "0", "--prob", "0", "--appmct", "-1", "--threads", "1",
    )
    assert "--appmct" in result.command and result.command[result.command.index("--appmct") + 1] == "-1"


def test_ganak_adapter_rejects_missing_projection_and_inconsistent_output(tmp_path: Path, monkeypatch):
    source = tmp_path / "plain.cnf"
    source.write_text("p cnf 1 1\n1 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="projection"):
        run_ganak(source, mode="projected")

    def inconsistent(command, **_kwargs):
        return CompletedProcess(command, 0, "s UNSATISFIABLE\nc s exact arb int 1\n", "")

    monkeypatch.setattr("cmbench.backends.native_count.subprocess.run", inconsistent)
    with pytest.raises(ValueError, match="mismatch"):
        run_ganak(source, mode="exact")


def test_d4_adapter_accepts_one_exact_integer_and_rejects_projection(tmp_path: Path, monkeypatch):
    source = tmp_path / "exact.cnf"
    source.write_text("p cnf 3 1\n1 0\n", encoding="utf-8")

    def completed(command, **_kwargs):
        return CompletedProcess(command, 0, "c diagnostic\ns 4\n", "")

    monkeypatch.setattr("cmbench.backends.native_count.subprocess.run", completed)
    result = run_d4(source, executable="/opt/pinned/d4-counter")
    assert result.count == 4
    assert result.status == "SATISFIABLE"
    assert result.command == (
        "/opt/pinned/d4-counter", "-i", str(source.resolve()),
        "--cache-size-first-page", str(D4_CACHE_FIRST_PAGE_BYTES),
        "--cache-size-additional-page", str(D4_CACHE_ADDITIONAL_PAGE_BYTES),
    )

    source.write_text("c ind 1 0\np cnf 3 1\n1 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="support/projection"):
        run_d4(source)


def test_d4_adapter_rejects_cache_pages_that_can_repeat_the_four_gib_failure(tmp_path: Path):
    source = tmp_path / "exact.cnf"
    source.write_text("p cnf 1 1\n1 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="cache page"):
        run_d4(source, cache_first_page_bytes=4 << 30)
    with pytest.raises(ValueError, match="cache page"):
        run_d4(source, cache_first_page_bytes=64 << 20, cache_additional_page_bytes=128 << 20)
