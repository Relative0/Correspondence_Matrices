"""Provider cleanup contracts using only exact fake-owned identities."""
import json
from types import SimpleNamespace
import pytest
from scripts import cm_benchmark_runpod_controller as controller

POD = 'fakeowned1234'

@pytest.fixture
def fake_cleanup(tmp_path, monkeypatch):
    state = dict(name='synthetic-test-owner', output=str(tmp_path))
    owned = dict(id=POD, name=state['name'], status='RUNNING')
    observation = dict(present=True, inventory_calls=0, fail_at=None)
    deletes = []
    def inventories(client):
        observation['inventory_calls'] += 1
        if observation['inventory_calls'] == observation['fail_at']:
            raise controller.requests.Timeout('SYNTHETIC_PRIVATE_CANARY')
        return dict(v1=[], v2=[owned] if observation['present'] else [])
    def delete(url, *, timeout, allow_redirects):
        assert timeout == 20 and allow_redirects is False
        assert url.endswith('/pods/' + POD)
        deletes.append(url)
        behavior = observation.get('delete_behavior', 'fallback')
        if url.startswith(controller.V1):
            if behavior == 'timeout':
                raise controller.requests.Timeout('SYNTHETIC_PRIVATE_CANARY')
            if behavior == 'accepted_still_live':
                return SimpleNamespace(status_code=202)
            return SimpleNamespace(status_code=404)
        observation['present'] = False
        return SimpleNamespace(status_code=204)
    monkeypatch.setattr(controller, 'inventories', inventories)
    monkeypatch.setattr(controller.time, 'sleep', lambda _: None)
    monkeypatch.setattr(controller, 'session', lambda: pytest.fail('no credentials'))
    monkeypatch.setattr(controller.requests, 'Session', lambda: pytest.fail('no network'))
    return state, observation, deletes, SimpleNamespace(delete=delete)

def test_v1_404_does_not_hide_v2_owned_resource(fake_cleanup):
    state, observation, deletes, client = fake_cleanup
    result = controller.cleanup(client, state, 'fake-test')
    assert deletes == [api+'/pods/'+POD for api in (controller.V1, controller.V2)]
    assert result['owned_pod_absent'] is True
    assert [r['http_status'] for r in result['attempts']] == [404, 204]

def test_delete_timeout_is_recorded_redacted_and_other_endpoint_attempted(fake_cleanup):
    state, observation, deletes, client = fake_cleanup
    observation['delete_behavior'] = 'timeout'
    result = controller.cleanup(client, state, 'fake-test')
    assert result['owned_pod_absent'] and len(deletes) == 2
    assert result['attempts'][0]['error_type'] == 'Timeout'
    assert 'SYNTHETIC_PRIVATE_CANARY' not in json.dumps(result)

def test_accepted_delete_is_not_verified_absence(fake_cleanup):
    state, observation, deletes, client = fake_cleanup
    observation['delete_behavior'] = 'accepted_still_live'
    result = controller.cleanup(client, state, 'fake-test')
    assert result['owned_pod_absent'] is False
    assert observation['inventory_calls'] == 6 and len(deletes) == 1

def test_already_absent_cleanup_is_idempotent_with_fresh_evidence(fake_cleanup):
    state, observation, deletes, client = fake_cleanup
    observation['present'] = False
    for _ in range(2):
        assert controller.cleanup(client, state, 'fake-test')['owned_pod_absent']
    assert not deletes and observation['inventory_calls'] == 4
    assert len((controller.Path(state['output'])/'cleanup-events.jsonl').read_text().splitlines()) == 2

@pytest.mark.parametrize('fail_at', [1, 2])
def test_failed_inventory_never_claims_absence_and_retains_attempts(fake_cleanup, fail_at):
    state, observation, deletes, client = fake_cleanup
    observation['fail_at'] = fail_at
    with pytest.raises(controller.requests.Timeout):
        controller.cleanup(client, state, 'fake-test')
    audit = controller.Path(state['output'])/'cleanup-events.jsonl'
    row = json.loads(audit.read_text().splitlines()[-1])
    assert row['owned_pod_absent'] is False and row['observation_error_type'] == 'Timeout'
    assert len(row['attempts']) == len(deletes)
    assert 'SYNTHETIC_PRIVATE_CANARY' not in audit.read_text()

@pytest.mark.parametrize('pinned', [False, True])
def test_conflicting_names_for_same_id_refuse_before_any_delete(fake_cleanup, monkeypatch, pinned):
    state, observation, deletes, client = fake_cleanup
    if pinned:
        (controller.Path(state['output'])/'POD-IDENTITY.json').write_text(json.dumps({'pod_id':POD}))
    monkeypatch.setattr(controller, 'inventories', lambda _: dict(
        v1=[dict(id=POD, name=state['name'])], v2=[dict(id=POD, name='unrelated')]))
    with pytest.raises(RuntimeError):
        controller.cleanup(client, state, 'fake-conflict')
    assert not deletes

def test_pinned_id_with_changed_name_does_not_claim_absence(fake_cleanup, monkeypatch):
    state, observation, deletes, client = fake_cleanup
    (controller.Path(state['output'])/'POD-IDENTITY.json').write_text(json.dumps({'pod_id':POD}))
    monkeypatch.setattr(controller, 'inventories', lambda _: dict(v1=[], v2=[dict(id=POD, name='unrelated')]))
    with pytest.raises(RuntimeError):
        controller.cleanup(client, state, 'fake-conflict')
    assert not deletes

@pytest.mark.parametrize('pinned', [None, '', 12345, True, '../fakeowned1234'])
def test_existing_invalid_pinned_identity_refuses_before_delete(fake_cleanup, pinned):
    state, observation, deletes, client = fake_cleanup
    (controller.Path(state['output'])/'POD-IDENTITY.json').write_text(json.dumps({'pod_id':pinned}))
    with pytest.raises(RuntimeError):
        controller.cleanup(client, state, 'fake-malformed')
    assert not deletes
