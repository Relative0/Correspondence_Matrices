"""Offline fault injection for declared limits and owned cleanup contracts."""
from dataclasses import replace
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cmbench.comparative import linux_supervisor as supervisor
from cmbench.comparative import p7_runner


@pytest.fixture
def cgroup_fs(tmp_path, monkeypatch):
    root = tmp_path / 'delegated'
    root.mkdir()
    (root / 'cgroup.controllers').write_text('memory pids cpu')
    original_mkdir, original_rmdir = Path.mkdir, Path.rmdir
    removed = []

    def mkdir(path, *args, **kwargs):
        original_mkdir(path, *args, **kwargs)
        if path.parent == root:
            for name, value in {'cgroup.events':'populated 0', 'memory.events':'oom_group_kill 0',
                                'memory.peak':'100', 'pids.peak':'1'}.items():
                (path/name).write_text(value)

    def rmdir(path):
        if path.parent == root:
            # Ordinary fixture files stand in for kernel virtual files.
            for child in path.iterdir():
                child.unlink()
            removed.append(path)
        return original_rmdir(path)

    monkeypatch.setattr(supervisor, 'CGROUP_ROOT', root)
    monkeypatch.setattr(Path, 'mkdir', mkdir)
    monkeypatch.setattr(Path, 'rmdir', rmdir)
    return root, removed


def test_declared_cpu_memory_and_pids_are_written_and_read_back(cgroup_fs):
    scope = supervisor._CgroupScope(32 << 20, 4, cpu_max=(100000,100000))
    row = scope.create()
    assert row['cgroup_settings'] == {'memory.max':str(32<<20), 'memory.swap.max':'0',
                                    'memory.oom.group':'1','pids.max':'4','cpu.max':'100000 100000'}
    assert row['cgroup_requested_settings'] == row['cgroup_settings']
    assert scope.close()['cgroup_removed']


@pytest.mark.parametrize('setting', ['memory.max','memory.swap.max','memory.oom.group','pids.max','cpu.max'])
def test_controller_readback_mismatch_refuses_before_worker_launch(cgroup_fs, monkeypatch, setting):
    original = Path.read_text
    def read(path, *args, **kwargs):
        if path.name == setting:
            return 'unexpected'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path,'read_text',read)
    monkeypatch.setattr(supervisor,'platform_supported',lambda:True)
    with patch.object(supervisor.subprocess,'Popen') as launch:
        result = supervisor.run([str(Path(__file__).resolve())], limits=replace(supervisor.Limits(),
            cgroup_memory_bytes=32<<20,cgroup_cpu_max=(100000,100000)))
    launch.assert_not_called()
    assert result.status == 'refused'
    assert cgroup_fs[1] and not cgroup_fs[1][0].exists()


def test_partial_setting_failure_cleans_owned_scope(cgroup_fs, monkeypatch):
    original = Path.write_text
    def write(path, *args, **kwargs):
        if path.name == 'pids.max':
            raise PermissionError('synthetic delegation denial')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'write_text',write)
    scope = supervisor._CgroupScope(32<<20,4)
    with pytest.raises(PermissionError):
        scope.create()
    assert cgroup_fs[1] and not cgroup_fs[1][0].exists()


@pytest.mark.parametrize('value', [None, 'malformed'])
def test_missing_or_malformed_peak_telemetry_does_not_prevent_removal(cgroup_fs, value):
    scope = supervisor._CgroupScope(32<<20,4)
    scope.create()
    peak=scope.path/'memory.peak'
    if value is None:
        peak.unlink()
    else:
        peak.write_text(value)
    row=scope.close()
    assert row['cgroup_cleanup_verified'] and row['cgroup_removed']
    assert row['cgroup_metrics_error']


def test_unreadable_live_owned_status_retains_membership(tmp_path, monkeypatch):
    process=tmp_path/'100'; process.mkdir()
    (process/'stat').write_text('100 (owned) S 1 100 100 0 0\n')
    original=Path.read_text
    def read(path,*args,**kwargs):
        if path.name=='status':
            raise PermissionError('synthetic unreadable status')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',read)
    row=supervisor.group_snapshot(tmp_path,100)
    assert row['pids']==[100] and row['unreadable_group_entries']==1


def test_repeated_close_retains_verified_cleanup(cgroup_fs):
    scope=supervisor._CgroupScope(32<<20,4)
    scope.create()
    first=scope.close()
    assert scope.close()==first and first['cgroup_removed']
    assert len(cgroup_fs[1])==1


def test_populated_group_is_never_reported_removed_after_cleanup_deadline(cgroup_fs, monkeypatch):
    scope=supervisor._CgroupScope(32<<20,4)
    scope.create()
    (scope.path/'cgroup.events').write_text('populated 1')
    with patch.object(supervisor.time,'monotonic',side_effect=[0,3]):
        row=scope.close()
    assert not row['cgroup_cleanup_verified'] and not row['cgroup_removed']
    assert scope.path.exists() and not cgroup_fs[1]
    # The fake worker can later empty; failed cleanup is retryable.
    (scope.path/'cgroup.events').write_text('populated 0')
    assert scope.close()['cgroup_removed']


def test_retry_status_disappearance_retains_known_live_member(tmp_path, monkeypatch):
    process=tmp_path/'100'; process.mkdir()
    (process/'stat').write_text('100 (owned) S 1 100 100 0 0\n')
    original=Path.read_text
    reads=0
    def read(path,*args,**kwargs):
        nonlocal reads
        if path.name=='status':
            reads+=1
            if reads==1: return 'Name:\towned\n'
            raise FileNotFoundError('synthetic lost status')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',read)
    row=supervisor.group_snapshot(tmp_path,100)
    assert row['pids']==[100] and row['unreadable_group_entries']==1


@pytest.mark.parametrize('cpu', [(True,100000),(0,100000),(100000,0),(1000,1000001),(64000001,1000000),'max 100000'])
def test_invalid_cpu_declaration_rejected_before_launch(cpu):
    with pytest.raises(ValueError):
        replace(supervisor.Limits(),cgroup_memory_bytes=32<<20,cgroup_cpu_max=cpu).validate()


def test_cpu_declaration_requires_owned_cgroup_memory_scope():
    with pytest.raises(ValueError):
        replace(supervisor.Limits(),cgroup_cpu_max=(100000,100000)).validate()


def test_frozen_limit_record_preserves_explicit_cgroup_policy():
    default=p7_runner.limits_record(supervisor.Limits())
    assert 'cgroup_memory_bytes' not in default and 'cgroup_cpu_max' not in default
    limits=replace(supervisor.Limits(),cgroup_memory_bytes=32<<20,cgroup_cpu_max=(100000,100000))
    record=p7_runner.limits_record(limits)
    assert p7_runner.limits_from_record(json.loads(json.dumps(record)))==limits
    changed=p7_runner.limits_record(replace(limits,cgroup_cpu_max=(50000,100000)))
    assert p7_runner.record_sha256(record)!=p7_runner.record_sha256(changed)
