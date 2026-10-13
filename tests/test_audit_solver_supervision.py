"""Bounded solver lifecycle controls and independent output invariants."""
from dataclasses import replace
import json
import itertools
import os
from pathlib import Path
import sys
import threading
from unittest.mock import patch

import pytest

from cmbench.backends import native_count, native_sat, solver_process
from cmbench.comparative import linux_supervisor


def completed(stdout, returncode=0, stderr=''):
    return solver_process.SolverProcessResult(returncode, stdout, stderr, {})


@pytest.fixture
def cnf(tmp_path):
    source = tmp_path / 'input.cnf'
    source.write_text('p cnf 1 0\n', encoding='utf-8')
    return source


@pytest.mark.parametrize('kind', ['d4', 'ganak', 'projected'])
def test_counter_rejects_counts_above_assignment_space(cnf, monkeypatch, kind):
    if kind == 'projected':
        cnf.write_text('c ind 1 0\np cnf 3 0\n')
    output = 's 3\n' if kind == 'd4' else 's SATISFIABLE\nc s exact arb int 3\n'
    monkeypatch.setattr(native_count, 'run_solver', lambda *a, **kw: completed(output))
    with pytest.raises(ValueError, match='mathematical maximum'):
        if kind == 'd4':
            native_count.run_d4(cnf)
        else:
            native_count.run_ganak(cnf, mode='projected' if kind == 'projected' else 'exact')


@pytest.mark.parametrize('width', [0, 1, 65, 128])
def test_exact_counts_retain_arbitrary_integer_precision(cnf, monkeypatch, width):
    cnf.write_text(f'p cnf {width} 0\n')
    # An unconstrained formula has exactly 2**width assignments, including
    # the unique empty assignment at width zero.
    count = 1 << width
    monkeypatch.setattr(native_count, 'run_solver', lambda *a, **kw: completed(f's {count}\n'))
    assert native_count.run_d4(cnf).count == count


@pytest.mark.parametrize('output', ['s 1\ns 1\n', 's 1.0\n', 's -1\n', 'c partial\n'])
def test_counter_duplicate_malformed_partial_output_is_refused(cnf, monkeypatch, output):
    monkeypatch.setattr(native_count, 'run_solver', lambda *a, **kw: completed(output))
    with pytest.raises(ValueError):
        native_count.run_d4(cnf)


@pytest.mark.parametrize('model', ['-1 1 0', '1', '2 0', '1 0 -1', '00', '1 0\nv 1 0'])
def test_sat_witness_rejects_contradiction_range_and_termination(cnf, monkeypatch, model):
    monkeypatch.setattr(native_sat, 'run_solver', lambda *a, **kw: completed(f's SATISFIABLE\nv {model}\n', 10))
    with pytest.raises(ValueError):
        native_sat.run_cryptominisat(cnf)


def test_sat_accepts_wrapped_native_model_stream(cnf, monkeypatch):
    cnf.write_text('p cnf 128 1\n1 0\n')
    lines = ['v ' + ' '.join(str(i) for i in range(start, min(start + 10, 129)))
        for start in range(1, 129, 10)]
    lines[-1] += ' 0'
    monkeypatch.setattr(native_sat, 'run_solver', lambda *a, **kw:
        completed('s SATISFIABLE\n' + '\n'.join(lines) + '\n', 10))
    assert native_sat.run_cryptominisat(cnf).assignment == (True,) * 128


@pytest.mark.parametrize('method', ['d4', 'ganak', 'cms'])
@pytest.mark.parametrize('kwargs', [dict(timeout_seconds=True), dict(timeout_seconds=float('nan')),
    dict(timeout_seconds=float('inf')), dict(timeout_seconds=901), dict(max_output_bytes=True),
    dict(max_output_bytes=0), dict(max_output_bytes=2 << 20), dict(max_memory_bytes=0)])
def test_invalid_limits_refuse_before_input_or_process(method, kwargs):
    module = native_sat if method == 'cms' else native_count
    with patch.object(module, 'read_solver_input', side_effect=AssertionError('input opened')), \
            patch.object(module, 'run_solver', side_effect=AssertionError('launched')):
        with pytest.raises(ValueError):
            if method == 'd4':
                native_count.run_d4('missing.cnf', **kwargs)
            elif method == 'ganak':
                native_count.run_ganak('missing.cnf', mode='exact', **kwargs)
            else:
                native_sat.run_cryptominisat('missing.cnf', **kwargs)


@pytest.mark.parametrize('method', ['ganak', 'cms'])
def test_boolean_thread_count_is_not_an_integer_configuration(cnf, monkeypatch, method):
    module = native_sat if method == 'cms' else native_count
    monkeypatch.setattr(module, 'run_solver', lambda *a, **kw: pytest.fail('launched'))
    with pytest.raises(ValueError, match='thread count'):
        if method == 'cms':
            native_sat.run_cryptominisat(cnf, threads=True)
        else:
            native_count.run_ganak(cnf, mode='exact', threads=True)


def test_input_read_is_bounded_before_parser(cnf, monkeypatch):
    monkeypatch.setattr(solver_process, 'MAX_INPUT_BYTES', 10)
    with pytest.raises(ValueError, match='byte limit'):
        solver_process.read_solver_input(cnf)


def test_input_leaf_symlink_is_refused_before_resolution(cnf, tmp_path):
    link = tmp_path / 'linked.cnf'
    try:
        link.symlink_to(cnf)
    except OSError:
        pytest.skip('local Windows account cannot create symlinks')
    with pytest.raises(ValueError, match='linked'):
        solver_process.read_solver_input(link)


def test_linux_cgroup_oom_is_a_fail_closed_memory_error():
    with pytest.raises(MemoryError, match='cgroup memory'):
        solver_process.raise_if_cgroup_oom({'cgroup_memory_events': {'oom_group_kill': 1}})


def _late_stream_result(supervisor, tmp_path, monkeypatch, read_error=False):
    # Force stream completion only after the root-exit branch has selected
    # "ok". No actual process or process group is created or terminated.
    release = threading.Event()
    pipes = []
    for name in ('stdin', 'stdout', 'stderr'):
        pipe = (tmp_path / name).open('w+b')
        pipes.append(pipe)
    class Process:
        pid = 123
        returncode = 0
        stdin, stdout, stderr = pipes
        def poll(self):
            return 0
        def wait(self, **kwargs):
            release.set()
            return 0
    def late_read(self, pipe):
        assert release.wait(1)
        if pipe is pipes[1]:
            if read_error:
                self.error = 'injected_read_error'
            else:
                self.data.extend(b'abcd')
                self.exceeded = True
            self.stop.set()
    monkeypatch.setattr(supervisor, 'platform_supported', lambda: True)
    monkeypatch.setattr(supervisor.subprocess, 'Popen', lambda *a, **kw: Process())
    monkeypatch.setattr(supervisor.os, 'getpgid', lambda pid: pid, raising=False)
    monkeypatch.setattr(supervisor.os, 'killpg', lambda *a: None, raising=False)
    monkeypatch.setattr(supervisor.signal, 'SIGKILL', 9, raising=False)
    monkeypatch.setattr(supervisor.BoundedStream, 'read', late_read)
    monkeypatch.setattr(supervisor, 'group_snapshot', lambda *a: dict(pids=[], rss_bytes=0,
        per_process_hwm_bytes={}, unreadable_group_entries=0, proc_scan_races=0, proc_scan_errors=0))
    try:
        return supervisor.run([sys.executable, '-c', 'pass'])
    finally:
        release.set()
        for pipe in pipes:
            if not pipe.closed:
                pipe.close()


@pytest.mark.parametrize('read_error', [False, True])
def test_linux_late_stream_failure_cannot_be_reported_as_success(tmp_path, monkeypatch, read_error):
    result = _late_stream_result(linux_supervisor, tmp_path, monkeypatch, read_error)
    assert result.resources['cleanup_verified'] and result.resources['streams_closed']
    assert result.resources['stdout_truncated'] is not read_error
    assert result.status == ('error' if read_error else 'output_limit')


def test_linux_expired_cleanup_observation_refuses_without_unbound_state(tmp_path, monkeypatch):
    clock = itertools.count(0, 3)
    monkeypatch.setattr(linux_supervisor.time, 'monotonic', lambda: next(clock))
    result = _late_stream_result(linux_supervisor, tmp_path, monkeypatch)
    assert not result.resources['cleanup_verified']
    assert result.status == 'error' and result.reason == 'cleanup_or_streams_unverified'


WINDOWS = pytest.mark.skipif(os.name != 'nt', reason='real Windows Job Object control')


def command(code):
    return [getattr(sys, '_base_executable', sys.executable), '-B', '-c', code]


@WINDOWS
@pytest.mark.parametrize('exitcode', [0, 10, 20, 7])
def test_real_result_exit_and_cleanup_metadata(exitcode):
    result = solver_process.run_solver(command(f'print("ok"); raise SystemExit({exitcode})'), timeout_seconds=3)
    assert result.returncode == exitcode and result.stdout == 'ok\n'
    assert result.resources['cleanup_verified'] and result.resources['streams_closed']
    assert result.resources['active_processes'] == 0
    assert result.resources['attached_before_resume']


@WINDOWS
@pytest.mark.parametrize('fd', [1, 2])
def test_real_flood_terminates_owned_tree_and_bounds_retention(fd):
    code = f'import os\nwhile True: os.write({fd}, b"x"*8192)'
    with pytest.raises(ValueError, match='output exceeds limit'):
        solver_process.run_solver(command(code), timeout_seconds=3, max_output_bytes=1024)


@WINDOWS
def test_real_combined_limit_and_exact_boundary():
    assert solver_process.run_solver(command('import os; os.write(1,b"abcd")'), max_output_bytes=4).stdout == 'abcd'
    with pytest.raises(ValueError, match='combined limit'):
        solver_process.run_solver(command('import os; os.write(1,b"abc"); os.write(2,b"def")'), max_output_bytes=4)


@WINDOWS
def test_real_invalid_utf8_is_not_silently_replaced():
    with pytest.raises(UnicodeDecodeError):
        solver_process.run_solver(command('import os; os.write(1,b"\\xff")'), timeout_seconds=3)


@WINDOWS
def test_real_descendant_timeout_and_root_exit_cleanup():
    leaf = 'import time; time.sleep(3)'
    spawning = f'import subprocess,sys,time; subprocess.Popen([sys.executable,"-B","-c",{leaf!r}]); '
    with pytest.raises(TimeoutError):
        solver_process.run_solver(command(spawning + 'time.sleep(3)'), timeout_seconds=1)
    with pytest.raises(RuntimeError, match='descendants_survived_root_exit'):
        solver_process.run_solver(command(spawning + 'print("s 1")'), timeout_seconds=3)


@WINDOWS
def test_real_memory_limit_has_small_and_large_positive_controls():
    code = '''import ctypes,json
dll=ctypes.WinDLL('kernel32',use_last_error=True)
dll.VirtualAlloc.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_ulong,ctypes.c_ulong]
dll.VirtualAlloc.restype=ctypes.c_void_p
dll.VirtualFree.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_ulong]
dll.VirtualFree.restype=ctypes.c_int
small=dll.VirtualAlloc(None,1<<20,0x3000,4)
if small: dll.VirtualFree(small,0,0x8000)
large=dll.VirtualAlloc(None,64<<20,0x3000,4)
if large: dll.VirtualFree(large,0,0x8000)
print(json.dumps([bool(small),bool(large)]))
'''
    small = solver_process.run_solver(command(code), timeout_seconds=3, max_memory_bytes=32 << 20)
    large = solver_process.run_solver(command(code), timeout_seconds=3, max_memory_bytes=128 << 20)
    assert json.loads(small.stdout) == [True, False]
    assert json.loads(large.stdout) == [True, True]


@WINDOWS
@pytest.mark.parametrize('kind', ['d4', 'ganak', 'cms'])
def test_real_supervised_adapter_pipeline(cnf, monkeypatch, kind):
    module = native_sat if kind == 'cms' else native_count
    text = {'d4': 's 2\n', 'ganak': 's SATISFIABLE\nc s exact arb int 2\n',
        'cms': 's SATISFIABLE\nv 1 0\n'}[kind]
    exitcode = 10 if kind == 'cms' else 0
    def translated(_command, **kwargs):
        return solver_process.run_solver(command(f'print({text!r},end=""); raise SystemExit({exitcode})'), **kwargs)
    monkeypatch.setattr(module, 'run_solver', translated)
    result = (native_sat.run_cryptominisat(cnf) if kind == 'cms' else
        native_count.run_d4(cnf) if kind == 'd4' else native_count.run_ganak(cnf, mode='exact'))
    assert result.resources['cleanup_verified'] and result.resources['streams_closed']
    if kind == 'cms':
        assert result.assignment == (True,)
    else:
        assert result.count == 2
