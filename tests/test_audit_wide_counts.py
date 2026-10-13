"""Analytical and independent integer controls without exponential wide arrays."""
from pathlib import Path
import importlib.util
import sys
from unittest.mock import patch

import pytest
from cmbench.backends.native_count import run_d4, run_ganak
from cmbench.backends.solver_process import SolverProcessResult

PATH = Path(__file__).resolve().parents[1]/'docs/audits/2026-10-11-aggregate-count-batch/wide_cases.py'
SPEC = importlib.util.spec_from_file_location('audit_wide_cases', PATH)
CASES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CASES)


@pytest.mark.parametrize('module', ['dd.autoref', 'dd.cudd'])
def test_analytical_counts_and_independent_truth_tables(module):
    backend = pytest.importorskip(module)
    assert all(row['passed'] for row in CASES.analytical(backend.BDD))
    assert all(row['passed'] for row in CASES.exhaustive(backend.BDD))


def test_independent_integer_buckets_at_wide_widths():
    assert all(row['passed'] for row in CASES.integer_buckets())


def decimal_without_global_guard_change(value):
    chunks = []
    while value:
        value, tail = divmod(value, 1_000_000_000)
        chunks.append(tail)
    return str(chunks[-1]) + ''.join(f'{tail:09d}' for tail in reversed(chunks[:-1]))


@pytest.mark.parametrize('adapter', ['ganak', 'd4'])
@pytest.mark.parametrize('width', [2048, 14284, 14285])
def test_native_decimal_precision_and_explicit_runtime_guard(adapter, width, tmp_path):
    source = tmp_path/'free.cnf'
    source.write_text(f'p cnf {width} 0\n')
    expected = 1 << width
    decimal = decimal_without_global_guard_change(expected)
    output = f'c s exact arb int {decimal}\ns SATISFIABLE\n' if adapter == 'ganak' else f's {decimal}\n'
    completed = SolverProcessResult(0, output, '', {})
    limit = sys.get_int_max_str_digits()
    with patch('cmbench.backends.native_count.run_solver', return_value=completed):
        call = lambda: run_ganak(source, mode='exact') if adapter == 'ganak' else run_d4(source)
        # The bounded chunk parser admits exact counts above CPython's
        # global decimal guard without changing that process-wide policy.
        assert call().count == expected
    assert sys.get_int_max_str_digits() == limit
