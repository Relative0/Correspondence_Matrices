import json
import pytest
from cmbench.comparative.consumer_capture import ConsumerCapture, verify_capture


def test_receipts_preserve_returns_errors_and_custody_without_admitting_natural_use(tmp_path):
    path=tmp_path/'capture.jsonl'
    capture=ConsumerCapture(path,caller_sha256='a'*64,purpose='controlled_replay')
    def consumer(value):
        if value=='error':raise ValueError('private detail')
        return {'sensitive_data':value}
    call=capture.wrap(consumer)
    assert call('private request')=={'sensitive_data':'private request'}
    with pytest.raises(ValueError,match='private detail'):call('error')
    capture.close(status='failed')
    result=verify_capture(path)
    assert result['recorded_calls']==2 and not result['natural_use_admitted']
    assert 'private' not in path.read_text() and 'sensitive_data' not in path.read_text()
    with pytest.raises(FileExistsError):ConsumerCapture(path,caller_sha256='a'*64,purpose='production')
    rows=path.read_text().splitlines();altered=json.loads(rows[1]);altered['status']='raised'
    rows[1]=json.dumps(altered);path.write_text('\n'.join(rows))
    with pytest.raises(ValueError,match='chain'):verify_capture(path)


def test_overflow_keeps_consumer_behavior_but_refuses_trace_admission(tmp_path):
    path=tmp_path/'capture.jsonl'
    capture=ConsumerCapture(path,caller_sha256='a'*64,purpose='production',max_events=1)
    call=capture.wrap(lambda x:x+1)
    assert [call(i) for i in range(3)]==[1,2,3]
    capture.close(status='complete')
    with pytest.raises(ValueError,match='truncated'):verify_capture(path)
