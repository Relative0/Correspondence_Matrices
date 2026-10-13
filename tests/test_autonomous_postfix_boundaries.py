"""New post-fix boundary evidence: all provider/OS effects are synthetic."""
from dataclasses import replace
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import cm_runpod_config as config
from cm_remote_executor import RunPodCMRemoteExecutor
from cmbench.comparative import linux_supervisor as supervisor, p7_runner
from test_autonomous_cgroup_contract import cgroup_fs


@pytest.mark.parametrize('flag', ['1', 'true', 'yes', 'on', ' \tTrUe\n'])
def test_ambient_offline_flag_refuses_worker_before_any_network(flag):
    with patch.dict(config.os.environ, {'CM_RUNPOD_DISABLE_ENV_FILES': flag}, clear=True), \
            patch.object(config, 'default_env_paths', side_effect=AssertionError('no automatic files')), \
            patch.object(config, '_parse_env_file', side_effect=AssertionError('no credential reads')), \
            patch('requests.sessions.Session.send', side_effect=AssertionError('no network')):
        loaded = config.load_runpod_config()
        assert not loaded.is_worker_configured and not loaded.is_lifecycle_configured
        with pytest.raises(config.CMRunPodConfigError):
            loaded.require_lifecycle()
        with pytest.raises(config.CMRunPodConfigError):
            RunPodCMRemoteExecutor(loaded).execute(None)


def test_explicit_empty_paths_and_mapping_do_not_merge_ambient_configuration():
    with patch.dict(config.os.environ, {'RUNPOD_API_KEY': 'synthetic-ambient',
                                      'CM_RUNPOD_BASE_URL': 'https://invalid.example'}, clear=True), \
            patch.object(config, '_parse_env_file', side_effect=AssertionError('no file reads')):
        loaded = config.load_runpod_config(env={}, env_paths=[])
    assert not loaded.is_worker_configured and not loaded.is_lifecycle_configured


@pytest.mark.parametrize('events', ['populated 1\npopulated 0',
    'populated 0\npopulated malformed', 'populated 0\npopulated -1',
    'populated 0 extra', 'populated 2', 'frozen 0', None])
def test_untrusted_membership_never_proves_cleanup_and_can_retry(cgroup_fs, monkeypatch, events):
    scope = supervisor._CgroupScope(32 << 20, 4)
    scope.create()
    path = scope.path / 'cgroup.events'
    if events is None:
        path.unlink()
    else:
        path.write_text(events)
    original = Path.write_text
    kills = []
    def write(target, *args, **kwargs):
        if target.name == 'cgroup.kill':
            kills.append(target)
        return original(target, *args, **kwargs)
    monkeypatch.setattr(Path, 'write_text', write)
    with patch.object(supervisor.time, 'monotonic', side_effect=[0, 0, 3]), \
            patch.object(supervisor.time, 'sleep'):
        first = scope.close()
    assert not first['cgroup_cleanup_verified'] and not first['cgroup_removed']
    assert scope.path.exists() and not cgroup_fs[1]
    path.write_text('populated 0\nfrozen 0\nfuture_event 7\n')
    second = scope.close()
    assert second['cgroup_cleanup_verified'] and second['cgroup_removed']
    assert scope.close() == second
    assert len(kills) == 2 and len(cgroup_fs[1]) == 1


@pytest.mark.parametrize('events', ['oom_group_kill 1\noom_group_kill 0',
                                  'oom_group_kill malformed', 'oom -1'])
def test_invalid_oom_telemetry_invalidates_metrics_but_removes_empty_group(cgroup_fs, events):
    scope = supervisor._CgroupScope(32 << 20, 4)
    scope.create()
    (scope.path / 'memory.events').write_text(events)
    row = scope.close()
    assert row['cgroup_removed'] and row['cgroup_cleanup_verified']
    assert row['cgroup_metrics_error']


@pytest.mark.parametrize('cpu', [None, True, 100000, '100000 100000', {}, [], [1000],
    [1000, 1000, 1000], [True, 1000], [1000.0, 1000], ['1000', 1000]])
def test_frozen_cpu_policy_rejects_noncanonical_inputs(cpu):
    record = p7_runner.limits_record(replace(supervisor.Limits(), cgroup_memory_bytes=32 << 20))
    record['cgroup_cpu_max'] = cpu
    with pytest.raises(ValueError):
        p7_runner.limits_from_record(record)


@pytest.mark.parametrize('cpu', [(1000, 1000), (64000, 1000), (1000, 1000000), (64000000, 1000000)])
def test_cpu_quota_boundary_roundtrip_and_memory_identity(cpu):
    limits = replace(supervisor.Limits(), cgroup_memory_bytes=32 << 20, cgroup_cpu_max=cpu)
    record = p7_runner.limits_record(limits)
    assert p7_runner.limits_from_record(record) == limits
    changed = p7_runner.limits_record(replace(limits, cgroup_memory_bytes=64 << 20))
    assert p7_runner.record_sha256(record) != p7_runner.record_sha256(changed)


@pytest.mark.parametrize('stage', ['cgroup', 'killpg', 'wait', 'snapshot', 'join', 'poll_sleep', 'poll_clock', 'persistent_cgroup'])
def test_second_cancellation_cannot_skip_later_owned_cleanup(monkeypatch, stage):
    calls = []
    interrupted = False
    sampled = False
    cleanup_reads = 0
    def attempt(name):
        nonlocal interrupted
        calls.append(name)
        if (name == stage and not interrupted) or (stage == 'persistent_cgroup' and name == 'cgroup'):
            interrupted = True
            raise KeyboardInterrupt('second cancellation')
    def snapshot(*args):
        nonlocal sampled, cleanup_reads
        if not sampled:
            sampled = True
            raise KeyboardInterrupt('first cancellation')
        attempt('snapshot')
        cleanup_reads += 1
        pids = [100] if stage == 'poll_sleep' and cleanup_reads <= 2 else []
        return dict(pids=pids, rss_bytes=0, per_process_hwm_bytes={}, unreadable_group_entries=0,
                    proc_scan_races=0, proc_scan_errors=0)
    class Scope:
        def __init__(self, *args): pass
        def create(self): return {}
        def wrapped_command(self, command): return command
        def close(self):
            attempt('cgroup')
            return dict(cgroup_cleanup_verified=True, cgroup_removed=True)
    class Thread:
        def __init__(self, *args, **kwargs): pass
        def start(self): pass
        def join(self, *args, **kwargs): attempt('join')
        def is_alive(self): return False
    process = SimpleNamespace(pid=100, returncode=0, stdin=io.BytesIO(), stdout=io.BytesIO(),
                              stderr=io.BytesIO(), wait=lambda **kw: attempt('wait'))
    monkeypatch.setattr(supervisor, 'platform_supported', lambda: True)
    monkeypatch.setattr(supervisor, '_CgroupScope', Scope)
    monkeypatch.setattr(supervisor, 'group_snapshot', snapshot)
    monkeypatch.setattr(supervisor.threading, 'Thread', Thread)
    monkeypatch.setattr(supervisor.subprocess, 'Popen', lambda *a, **kw: process)
    monkeypatch.setattr(supervisor.os, 'getpgid', lambda pid: pid, raising=False)
    monkeypatch.setattr(supervisor.os, 'killpg', lambda *a: attempt('killpg'), raising=False)
    monkeypatch.setattr(supervisor.signal, 'SIGKILL', 9, raising=False)
    clock = supervisor.time.monotonic
    def monotonic():
        if sampled and stage == 'poll_clock': attempt('poll_clock')
        return clock()
    monkeypatch.setattr(supervisor.time, 'monotonic', monotonic)
    monkeypatch.setattr(supervisor.time, 'sleep', lambda _: attempt('poll_sleep'))
    with pytest.raises(KeyboardInterrupt):
        supervisor.run([str(Path(__file__).resolve())],
                       limits=replace(supervisor.Limits(), cgroup_memory_bytes=32 << 20))
    assert interrupted
    assert all(name in calls for name in ('cgroup', 'killpg', 'wait', 'snapshot', 'join'))
    if stage == 'persistent_cgroup':
        assert calls.count('cgroup') == 2
    else:
        assert calls.count(stage) >= 2
    assert all(pipe.closed for pipe in (process.stdin, process.stdout, process.stderr))
