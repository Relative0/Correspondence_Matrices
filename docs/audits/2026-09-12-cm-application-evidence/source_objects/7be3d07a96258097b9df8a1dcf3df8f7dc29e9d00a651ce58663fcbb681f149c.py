import pytest
from scripts.restore_cm_application_fixtures import apply_exact, sha, D4


def test_restore_is_exact_and_idempotent(tmp_path):
    rows = [(D4, b'historical', sha(b'historical'))]
    assert apply_exact(tmp_path, rows)['missing'] == 1
    assert apply_exact(tmp_path, rows, apply=True)['restored'] == 1
    assert apply_exact(tmp_path, rows, apply=True)['already_verified'] == 1


@pytest.mark.parametrize('name', ['../escape', '/external/escape', 'external\\escape',
                                 'external/d4v2/../../escape', 'scripts/elsewhere.py'])
def test_invalid_targets_are_refused(tmp_path, name):
    with pytest.raises(ValueError):
        apply_exact(tmp_path, [(name, b'x', sha(b'x'))], apply=True)


def test_all_files_validated_before_writing(tmp_path):
    rows = [(D4, b'x', sha(b'x')), ('external/logikbench-confirmation-20260830/LICENSE', b'bad', sha(b'good'))]
    with pytest.raises(ValueError):
        apply_exact(tmp_path, rows, apply=True)
    assert not (tmp_path/'external').exists()
    path = tmp_path/D4
    path.parent.mkdir(parents=True)
    path.write_bytes(b'newer')
    with pytest.raises(ValueError, match='differs'):
        apply_exact(tmp_path, rows[:1], apply=True)
    assert path.read_bytes() == b'newer'
