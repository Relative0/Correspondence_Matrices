"""Small arm/oracle and filesystem preflight on the Linux campaign host."""
import hashlib

import pytest

from scripts import cm_packed_io_campaign as campaign
from scripts import cm_packed_queries_campaign as prior


@pytest.mark.parametrize('entangled', [False, True])
@pytest.mark.parametrize('method', ['cse_flat', 'independent_expr', 'independent_cm', 'bdd_cudd'])
def test_count_arms_match_independent_oracle(tmp_path, entangled, method):
    case = dict(id='small-count', task='count', n=8, entangled=entangled,
                document=prior.count_fixture(8, 4, 9301, entangled))
    path = tmp_path / 'fixture.json'
    prior.write(path, case['document'])
    results, files, measures = campaign.session(case, method, 8, path, tmp_path)
    assert not files
    assert results == [campaign.oracle(case, c)['count'] for c in campaign.contexts(case, 8)]
    assert measures['total_ns'] == measures['setup_ns'] + measures['query_delivery_ns'] + measures['cleanup_ns']


@pytest.mark.parametrize('method', ['complete', 'positional_full', 'stream_12', 'stream_16', 'stream_18'])
def test_file_arms_reload_and_reread(tmp_path, method):
    case = dict(id='small-file', task='file', n=9, document=prior.stream_fixture(9, 9421))
    path = tmp_path / 'fixture.json'
    prior.write(path, case['document'])
    results, files, measures = campaign.session(case, method, 8, path, tmp_path)
    campaign.reread(files, results)
    assert len(files) == 16
    for index, context in enumerate(campaign.contexts(case, 8)):
        target = campaign.oracle(case, context)
        assert results[index] == {k: target[k] for k in ('bytes', 'sha256')}
        assert hashlib.sha256(files[index].read_bytes()).hexdigest() == target['sha256']
    assert 0 < measures['first_chunk_ns'] <= measures['total_ns']
