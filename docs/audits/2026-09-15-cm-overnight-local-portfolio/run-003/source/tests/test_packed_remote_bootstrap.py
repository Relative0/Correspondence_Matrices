"""Offline transport checks; no credential access, network or pod creation."""
import hashlib
import json
import zipfile

import pytest

from scripts import cm_runpod_packed_remote as remote


@pytest.mark.parametrize('fail_command', [False, True])
def test_new_workspace_and_failure_archive(tmp_path, monkeypatch, capsys, fail_command):
    root = tmp_path / 'missing-workspace' / 'source'
    out = tmp_path / 'missing-evidence' / 'result'
    monkeypatch.setattr(remote, 'ROOT', root)
    monkeypatch.setattr(remote, 'OUT', out)
    payload = tmp_path / 'payload.zip'
    with zipfile.ZipFile(payload, 'x') as archive:
        archive.writestr('SOURCE_MANIFEST.json', json.dumps({'files': {}}))
        archive.writestr('DEPENDENCIES.json', '[]')
        archive.writestr('COMMANDS.json', '[]')
    for key, value in dict(CM_BUNDLE_PATH=str(payload),
                           CM_BUNDLE_SHA256=hashlib.sha256(payload.read_bytes()).hexdigest(),
                           CM_RUNPOD_MACHINE_ID='offline-fixture', CM_IMAGE_TAG='offline',
                           CM_IMAGE_DIGEST='offline').items():
        monkeypatch.setenv(key, value)
    original = remote.Path.read_text
    def read(path, *args, **kwargs):
        if str(path).replace('\\', '/') in ('/proc/cpuinfo', '/proc/meminfo'):
            return 'offline fixture'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(remote.Path, 'read_text', read)
    calls = []
    def command(label, args, timeout):
        calls.append(label)
        if fail_command: raise RuntimeError('offline command failure')
    monkeypatch.setattr(remote, 'run', command)
    remote.main()
    result = json.loads((out / 'transport/REMOTE_RESULT.json').read_text())
    assert result['status'] == ('failed' if fail_command else 'complete')
    assert calls
    assert root.is_dir()
    log = capsys.readouterr().out
    assert 'CM_EVIDENCE 0 ' in log
    assert 'evidence_start' in log and 'evidence_end' in log
