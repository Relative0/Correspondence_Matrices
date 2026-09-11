from types import SimpleNamespace
import pytest
from cmbench.comparative.presentation_capture import capture_presentation
from cmbench.comparative.consumer_capture import verify_capture


def test_formatter_receipt_preserves_objects_and_does_not_admit_natural_use(tmp_path):
    active = {0, 3}
    def matrix(bits, *, active):
        assert active is original_set
        return '<table>'+bits+'</table>'
    original_set = active
    module = SimpleNamespace(matrix=matrix, mini_matrix=lambda bits: bits)
    path = tmp_path/'capture.jsonl'
    with capture_presentation(module, path, source_sha256='0'*64, purpose='controlled_replay') as result:
        assert module.matrix('1001', active=active) == '<table>1001</table>'
        assert module.mini_matrix('10') == '10'
        result['status'] = 'complete'
    assert module.matrix is matrix
    verified = verify_capture(path)
    assert verified['recorded_calls'] == 2
    assert verified['natural_use_admitted'] is False
    assert '1001' not in path.read_text()


def test_formatter_failure_is_retained_and_original_restored(tmp_path):
    def fail(*args):
        raise RuntimeError('private error text')
    module = SimpleNamespace(matrix=fail, mini_matrix=fail)
    path = tmp_path/'capture.jsonl'
    with pytest.raises(RuntimeError):
        with capture_presentation(module, path, source_sha256='0'*64, purpose='controlled_replay'):
            module.matrix('10')
    assert module.matrix is fail
    assert verify_capture(path)['status'] == 'failed'
    assert 'private error text' not in path.read_text()
