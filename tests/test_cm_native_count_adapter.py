from __future__ import annotations

from pathlib import Path
from cmbench.backends.solver_process import SolverProcessResult

import pytest

from cmbench.backends.native_count import (
    DEFAULT_MAX_COUNT_DIGITS,
    D4_CACHE_ADDITIONAL_PAGE_BYTES,
    D4_CACHE_FIRST_PAGE_BYTES,
    parse_bounded_decimal_count,
    run_d4,
    run_ganak,
)


def _completed(command, **_kwargs):
    return SolverProcessResult(0, "s SATISFIABLE\nc s exact arb int 2\n", "", {})


def test_ganak_adapter_pins_deterministic_exact_flags_and_projection(tmp_path: Path, monkeypatch):
    source = tmp_path / "projected.cnf"
    source.write_text("c ind 1 0\np cnf 3 1\n2 3 0\n", encoding="utf-8")
    monkeypatch.setattr("cmbench.backends.native_count.run_solver", _completed)
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
        return SolverProcessResult(0, "s UNSATISFIABLE\nc s exact arb int 1\n", "", {})

    monkeypatch.setattr("cmbench.backends.native_count.run_solver", inconsistent)
    with pytest.raises(ValueError, match="mismatch"):
        run_ganak(source, mode="exact")


def test_d4_adapter_accepts_one_exact_integer_and_rejects_projection(tmp_path: Path, monkeypatch):
    source = tmp_path / "exact.cnf"
    source.write_text("p cnf 3 1\n1 0\n", encoding="utf-8")

    def completed(command, **_kwargs):
        return SolverProcessResult(0, "c diagnostic\ns 4\n", "", {})

    monkeypatch.setattr("cmbench.backends.native_count.run_solver", completed)
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


def _power_of_two_decimal(exponent: int) -> str:
    # Keep this independent from the adapter and avoid str(huge_int), whose
    # process-wide guard is the compatibility boundary under test.
    chunks = [1]
    base = 10 ** 9
    for _ in range(exponent):
        carry = 0
        for index, chunk in enumerate(chunks):
            value = chunk * 2 + carry
            chunks[index], carry = value % base, value // base
        if carry:
            chunks.append(carry)
    return str(chunks[-1]) + ''.join(f'{chunk:09d}' for chunk in reversed(chunks[:-1]))


def test_bounded_decimal_parser_accepts_4301_digit_exact_count_without_changing_global_guard():
    import sys
    before = sys.get_int_max_str_digits()
    decimal = _power_of_two_decimal(14285)
    assert len(decimal) == 4301
    assert parse_bounded_decimal_count(decimal, max_digits=DEFAULT_MAX_COUNT_DIGITS,
                                       maximum_exponent=14285) == 1 << 14285
    assert sys.get_int_max_str_digits() == before


@pytest.mark.parametrize('value', ['00', '1x', '', '1' + '0' * 20])
def test_bounded_decimal_parser_refuses_malformed_or_oversized_counts(value):
    with pytest.raises(ValueError):
        parse_bounded_decimal_count(value, max_digits=20, maximum_exponent=100)


def test_adapters_apply_configured_decimal_limit_and_mathematical_maximum(tmp_path: Path, monkeypatch):
    source = tmp_path / 'wide.cnf'
    source.write_text('p cnf 14285 0\n', encoding='utf-8')
    count = _power_of_two_decimal(14285)
    monkeypatch.setattr('cmbench.backends.native_count.run_solver',
                        lambda *a, **kw: SolverProcessResult(0, f's {count}\n', '', {}))
    assert run_d4(source).count == 1 << 14285
    with pytest.raises(ValueError, match='oversized'):
        run_d4(source, max_count_digits=4300)
    monkeypatch.setattr('cmbench.backends.native_count.run_solver',
                        lambda *a, **kw: SolverProcessResult(0, f's {"9" * 4301}\n', '', {}))
    with pytest.raises(ValueError, match='mathematical maximum'):
        run_d4(source)

    monkeypatch.setattr('cmbench.backends.native_count.run_solver', lambda *a, **kw:
                        SolverProcessResult(0, f's SATISFIABLE\nc s exact arb int {count}\n', '', {}))
    assert run_ganak(source, mode='exact').count == 1 << 14285
    with pytest.raises(ValueError, match='oversized'):
        run_ganak(source, mode='exact', max_count_digits=4300)
