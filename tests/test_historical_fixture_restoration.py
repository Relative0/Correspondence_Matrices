import hashlib
import zipfile
import pytest
from scripts.restore_cm_historical_fixtures import restore


def fixture(tmp_path):
    data=b'original\r\n'
    archive=tmp_path/'fixture.zip'
    with zipfile.ZipFile(archive,'x') as z:z.writestr('evidence.json',data)
    return dict(archives=[dict(path='fixture.zip',sha256=hashlib.sha256(archive.read_bytes()).hexdigest())],
        files=[dict(archive='fixture.zip',member='evidence.json',target='docs/recognition/runs/example/data.json',
                    bytes=len(data),sha256=hashlib.sha256(data).hexdigest())])


def test_restoration_is_exact_idempotent_and_preserves_conflicting_files(tmp_path):
    manifest=fixture(tmp_path)
    assert restore(tmp_path,manifest)['missing']==1
    assert restore(tmp_path,manifest,apply=True)['restored']==1
    assert restore(tmp_path,manifest,apply=True)['already_verified']==1
    target=tmp_path/manifest['files'][0]['target'];target.write_bytes(b'newer local data')
    with pytest.raises(ValueError,match='differs'):restore(tmp_path,manifest,apply=True)
    assert target.read_bytes()==b'newer local data'


def test_restoration_rejects_traversal_and_mutated_archive_before_writing(tmp_path):
    manifest=fixture(tmp_path)
    manifest['files'][0]['target']='docs/recognition/../../../escape'
    with pytest.raises(ValueError,match='unsafe'):restore(tmp_path,manifest,apply=True)
    manifest['files'][0]['target']='docs/recognition/runs/example/data.json'
    with (tmp_path/'fixture.zip').open('ab') as stream:stream.write(b'tampering')
    with pytest.raises(ValueError,match='hash'):restore(tmp_path,manifest,apply=True)
    assert not (tmp_path/'docs').exists()
