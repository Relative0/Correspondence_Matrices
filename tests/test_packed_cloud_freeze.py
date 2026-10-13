"""Archive provenance must work without a checkout and reject altered sources."""
import hashlib
import json

import pytest

from scripts import cm_packed_cloud_freeze as adapter


@pytest.mark.parametrize('tampered', [False, True])
def test_archive_freeze_without_git(tmp_path, monkeypatch, tampered):
    source = b'fixture = 1\n'
    path = tmp_path / 'fixture.py'
    path.write_bytes(source + (b'# modified\n' if tampered else b''))
    manifest = dict(files={'fixture.py': hashlib.sha256(source).hexdigest()}, git_checkpoint='a' * 40)
    (tmp_path / 'SOURCE_MANIFEST.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(adapter.campaign, 'ROOT', tmp_path)
    original = adapter.campaign.subprocess.check_output
    def reject_git(command, *args, **kwargs):
        if isinstance(command, list) and command[0] == 'git':
            raise AssertionError('archive freeze must not request Git')
        return original(command, *args, **kwargs)
    monkeypatch.setattr(adapter.campaign.subprocess, 'check_output', reject_git)
    out = tmp_path / 'panels'
    if tampered:
        with pytest.raises(ValueError, match='source archive identity mismatch'):
            adapter.freeze(out)
        assert not out.exists()
    else:
        adapter.freeze(out)
        frozen = adapter.campaign.check_sources(out)
        assert frozen['source_parent_checkpoint'] == 'a' * 40
        assert len(frozen['schedule']) == 1224
        assert (out / 'source/fixture.py').read_bytes() == source
