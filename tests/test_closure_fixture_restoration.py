import hashlib
from pathlib import Path
import pytest
from scripts.restore_cm_closure_fixtures import destination,recover_bytes

@pytest.mark.parametrize('name',['../x.cnf','external/d4/../../x.cnf','external/d4/a.exe',
                                'external/other/a.cnf','external\\d4\\a.cnf','C:/x.cnf'])
def test_only_public_cnf_targets_are_allowed(tmp_path,name):
    with pytest.raises(ValueError):destination(tmp_path,name)

def test_original_hash_is_required_for_line_ending_recovery():
    original=b'p cnf 1 1\r\n1 0\r\n';expected=hashlib.sha256(original).hexdigest()
    assert recover_bytes(original,expected)==(original,'identity')
    assert recover_bytes(original.replace(b'\r\n',b'\n'),expected)==(original,'restore_crlf')
    with pytest.raises(ValueError):recover_bytes(b'p cnf 1 0\n',expected)

def test_target_symlink_escape_is_refused(tmp_path):
    outside=tmp_path.parent/(tmp_path.name+'-outside');outside.mkdir()
    link=tmp_path/'external';
    try:link.symlink_to(outside,target_is_directory=True)
    except OSError:pytest.skip('symlink capability unavailable')
    with pytest.raises(ValueError):destination(tmp_path,'external/d4/benchTest/a.cnf')
