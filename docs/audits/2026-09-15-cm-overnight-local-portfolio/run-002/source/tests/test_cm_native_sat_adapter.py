from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from cmbench.backends.native_sat import parse_xor_dimacs, run_cryptominisat


def test_xor_dimacs_parser_and_cryptominisat_witness(tmp_path: Path, monkeypatch):
    source = tmp_path / "xor.cnf"
    source.write_text("p cnf 2 2\nx 1 2 0\n1 0\n", encoding="utf-8")
    instance = parse_xor_dimacs(source.read_text(encoding="utf-8"))
    assert instance.xor_clauses == ((1, 2),)

    def completed(command, **_kwargs):
        return CompletedProcess(command, 10, "s SATISFIABLE\nv 1 -2 0\n", "")

    monkeypatch.setattr("cmbench.backends.native_sat.subprocess.run", completed)
    result = run_cryptominisat(source, executable="/opt/pinned/cryptominisat5")
    assert result.status == "SATISFIABLE"
    assert result.assignment == (True, False)
    assert result.command[:5] == ("/opt/pinned/cryptominisat5", "--verb", "0", "--threads", "1")


def test_cryptominisat_adapter_rejects_bad_witness_and_header(tmp_path: Path, monkeypatch):
    source = tmp_path / "xor.cnf"
    source.write_text("p cnf 2 2\nx 1 2 0\n1 0\n", encoding="utf-8")

    def bad_witness(command, **_kwargs):
        return CompletedProcess(command, 10, "s SATISFIABLE\nv 1 2 0\n", "")

    monkeypatch.setattr("cmbench.backends.native_sat.subprocess.run", bad_witness)
    with pytest.raises(ValueError, match="does not satisfy"):
        run_cryptominisat(source)
    with pytest.raises(ValueError, match="incomplete"):
        parse_xor_dimacs("p cnf 2 1\nx 1 2 0\n1 0\n")
