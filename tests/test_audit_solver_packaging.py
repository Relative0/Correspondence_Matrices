"""Verify source bundles retain the solver supervisor's runtime dependencies."""
import ast
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
DEPENDENCIES = {
    'cmbench/__init__.py', 'cmbench/backends/__init__.py',
    'cmbench/backends/native_count.py', 'cmbench/backends/native_sat.py',
    'cmbench/backends/projected_count.py', 'cmbench/backends/solver_process.py',
    'cmbench/comparative/__init__.py', 'cmbench/comparative/linux_supervisor.py',
    'cmbench/comparative/contracts.py',
    'scripts/cm_process_supervisor.py',
}


@pytest.mark.parametrize('script,variable', [('cm_benchmark_prelaunch.py', 'code_paths'),
    ('cm_benchmark_successor_prelaunch.py', 'CODE_PATHS')])
def test_source_list_includes_solver_supervision_dependencies(script, variable):
    tree = ast.parse((ROOT / 'scripts' / script).read_text(encoding='utf-8'))
    values = [ast.literal_eval(node.value) for node in ast.walk(tree) if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == variable for target in node.targets)]
    assert len(values) == 1 and DEPENDENCIES <= set(values[0])


@pytest.mark.skipif(os.name != 'nt', reason='standalone Windows package control')
def test_minimal_source_package_executes_supervised_solver_child(tmp_path):
    for name in DEPENDENCIES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    # Isolated interpreter plus a temporary package root prevents a missing
    # copied module from being supplied by the repository's import path.
    code = (f'import sys; sys.path.insert(0,{str(tmp_path)!r}); '
        'from cmbench.backends import native_count,native_sat,solver_process; '
        'from cmbench.comparative import linux_supervisor; '
        'r=solver_process.run_solver([sys.executable,"-B","-c","print(42)"],timeout_seconds=3); '
        'assert r.stdout=="42\\n" and r.resources["cleanup_verified"]; print("PASS")')
    result = subprocess.run([getattr(sys, '_base_executable', sys.executable), '-I', '-B', '-c', code],
        cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout == 'PASS\n'


def test_benchmark_record_keeps_native_resource_policy(tmp_path, monkeypatch):
    from scripts import cm_benchmark_core_screen as screen
    from cmbench.backends import native_count
    source = tmp_path / 'input.cnf'
    source.write_text('p cnf 1 0\n')
    resources = dict(job_memory_limit_bytes=32 << 20, cleanup_verified=True)
    monkeypatch.setattr(native_count, 'run_d4', lambda *a, **kw:
        native_count.NativeCountResult(2, 'SATISFIABLE', 'exact', ('fake',), 's 2\n', '', resources))
    row = screen.execute(dict(root=str(tmp_path), case=dict(path='input.cnf', input_sha256=screen.digest(source)),
        cell=dict(lane='exact_count', arm='d4')))
    assert row['value'] == '2' and row['native_resources'] == resources
