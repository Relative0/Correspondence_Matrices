"""Budgeted continuation, reusing the reviewed token transport and ownership cleanup.

The existing API credential loader is used only by authenticated controller
sessions. Never serialize those sessions, config objects or pod environments.
"""
from __future__ import annotations

import argparse
import ast
import base64
from contextlib import contextmanager
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import subprocess
import sys
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs/audits/2026-09-12-cm-component-execution'
CHECKOUT = ROOT / 'build/cm-diag'
PROFILE = 'component-historical-v2'
spec = importlib.util.spec_from_file_location('prior_packed_transport', ROOT / 'scripts/runpod_query_ladder_q64_second_host_v3_controller.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
shared, preflight = transport.shared, transport.preflight
RESERVATION = 0.50
BUDGET = 5.00
LIFETIME = 4800
HORIZON = 5100
ORIGINAL_PROXY_REQUEST = shared.proxy_request


def resilient_proxy_request(client, method, url, **kwargs):
    """Retry transient proxy routing, reconciling the one immutable upload.

    The bootstrap accepts only the frozen payload and authenticates progress
    with the same ephemeral token. Its run endpoint is explicitly idempotent.
    This never retries pod creation, changes a payload, or prints request data.
    """
    for attempt in range(5):
        try:
            return ORIGINAL_PROXY_REQUEST(client, method, url, **kwargs)
        except (shared.requests.RequestException, RuntimeError) as exc:
            if isinstance(exc, RuntimeError) and str(exc) not in (
                    'proxy HTTP 404', 'proxy HTTP 409', 'proxy HTTP 502', 'proxy HTTP 503', 'proxy HTTP 504'):
                raise
            if method == 'POST' and url.endswith('/payload'):
                try:
                    progress = json.loads(ORIGINAL_PROXY_REQUEST(client, 'GET', url[:-8]+'/progress', timeout=5))
                    if progress.get('uploaded'):
                        return json.dumps({'accepted_sha256':transport.EXPECTED_BUNDLE_SHA256}).encode()
                except (shared.requests.RequestException, RuntimeError, ValueError):
                    pass
            if attempt == 4: raise
            time.sleep(2 + attempt)



def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configure(attempt, profile):
    global PROFILE
    PROFILE = profile
    if not re.fullmatch(r'attempt-[0-9]{3}', attempt): raise ValueError('invalid attempt')
    transport.OUT = AUDIT / attempt
    transport.BUNDLE = AUDIT / 'packages' / (profile + '.zip')
    transport.EXPECTED_BUNDLE_BYTES = transport.BUNDLE.stat().st_size
    transport.EXPECTED_BUNDLE_SHA256 = digest(transport.BUNDLE)
    transport.REMOTE_CODE = (ROOT / 'scripts/cm_component_execution_remote.py').read_text()
    transport.HARD_LIFETIME_SECONDS = LIFETIME
    transport.RECONCILIATION_SECONDS = HORIZON
    transport.RATE_CAP_USD_PER_HOUR = .10
    transport.TOTAL_COST_CAP_USD = RESERVATION
    transport.CPU_FLAVOR = 'cpu3g'
    transport.BOOTSTRAP = ROOT / 'scripts/runpod_frontier_bootstrap.py'
    transport.configure_transport()
    shared.proxy_request = resilient_proxy_request
    return transport.OUT


def check_inventory(snapshot):
    states = {shared.load(p)['name']:p.parent for p in AUDIT.glob('attempt-*/controller-state.json')}
    for rows in snapshot.values():
        for row in rows:
            directory = states.get(row.get('name'))
            # Other projects share this account. Inventory is read-only; only
            # this campaign's exact name/ID pair is eligible for cleanup.
            if directory is None:
                continue
            if not (directory/'RESERVATION.json').is_file():
                raise RuntimeError('campaign pod lacks a budget reservation')
            identity = directory/'POD-IDENTITY.json'
            if identity.exists() and shared.load(identity)['pod_id'] != row['id']:
                raise RuntimeError('campaign pod identity mismatch')


def reserve(out):
    lock = AUDIT/'reservation.lock'
    handle = None
    for _ in range(100):
        try:
            handle = lock.open('x')
            break
        except FileExistsError:
            time.sleep(.1)
    if handle is None: raise RuntimeError('budget reservation lock unavailable')
    try:
        total = math.fsum(shared.load(p)['reserved_usd'] for p in AUDIT.glob('attempt-*/RESERVATION.json')) + RESERVATION
        if total > BUDGET: raise RuntimeError('campaign budget exhausted')
        authorization = shared.load(AUDIT/'AUTHORIZATION.json')
        if authorization['additional_runpod_budget_usd'] != BUDGET:
            raise RuntimeError('authorization mismatch')
        prior = authorization['prior_nonrefunded_reservations_usd']
        if prior != 10.0 or prior + total > 15.0:
            raise RuntimeError('cumulative authorized budget exhausted')
        if (.10 + .01) * HORIZON / 3600 > RESERVATION:
            raise RuntimeError('reservation does not cover bounded lifetime')
        out.mkdir(exist_ok=False)
        shared.write(out/'RESERVATION.json', dict(reserved_usd=RESERVATION, total_reserved_usd=total,
            budget_usd=BUDGET, cumulative_reserved_usd=prior + total, profile=PROFILE, recorded_utc=preflight.utc_now()))
        return total
    finally:
        handle.close()
        lock.unlink()


@contextmanager
def awake():
    if os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        if not kernel.SetThreadExecutionState(0x80000001): raise RuntimeError('wake guard failed')
    try: yield
    finally:
        if os.name == 'nt': kernel.SetThreadExecutionState(0x80000000)


def arm_watchdog(attempt, out):
    with (out / 'watchdog.log').open('xb') as stream:
        proc = subprocess.Popen([sys.executable, '-B', str(Path(__file__)), 'watchdog', '--attempt', attempt, '--profile', PROFILE],
                                stdout=stream, stderr=subprocess.STDOUT, close_fds=True,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) |
                                              getattr(subprocess, 'DETACHED_PROCESS', 0))
    for _ in range(200):
        if shared.READY.exists():
            ready = shared.load(shared.READY)
            check_inventory(ready['startup_inventories'])
            if not ready.get('network_probe_passed'):
                raise RuntimeError('watchdog inventory probe failed')
            shared.write(out / 'WATCHDOG-PROCESS-BINDING.json', shared.bind_watchdog(proc, ready))
            return proc
        if proc.poll() is not None: raise RuntimeError('watchdog exited before readiness')
        time.sleep(.2)
    raise RuntimeError('watchdog readiness timeout')


def evidence(log, out):
    # Preserve early bootstrap failures even when no archive markers exist.
    (out / 'container.log').write_text('\n'.join(l for l in log.splitlines() if not l.startswith('CM_EVIDENCE ')) + '\n')
    starts, ends, chunks = [], [], {}
    for line in log.splitlines():
        if line.startswith('CM_EVENT '):
            event = json.loads(line[9:])
            if event.get('kind') == 'evidence_start': starts.append(event)
            if event.get('kind') == 'evidence_end': ends.append(event)
        elif line.startswith('CM_EVIDENCE '):
            _, index, data = line.split(' ', 2)
            if int(index) in chunks: raise ValueError('duplicate result chunk')
            chunks[int(index)] = data
    assert len(starts) == len(ends) == 1
    start = starts[0]
    assert set(chunks) == set(range(start['chunks']))
    data = base64.b64decode(''.join(chunks[i] for i in range(start['chunks'])), validate=True)
    assert len(data) == start['bytes'] < 32 << 20
    assert hashlib.sha256(data).hexdigest() == start['sha256'] == ends[0]['sha256']
    with (out / 'evidence.zip').open('xb') as stream: stream.write(data)
    destination = out / 'evidence'
    destination.mkdir()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert sum(i.file_size for i in archive.infolist()) + len(data) < 32 << 20
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            assert not path.is_absolute() and '..' not in path.parts and ':' not in item.filename and not item.is_dir()
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream: stream.write(archive.read(item))
    return dict(sha256=start['sha256'], bytes=len(data),
                remote=shared.load(destination / 'transport/REMOTE_RESULT.json'))


def create_state(created):
    # The reused ownership watchdog accepts this exact prefix only.
    return dict(name='cm-c7-linux-' + uuid.uuid4().hex[:12], created_epoch=created,
                cleanup_epoch=created + LIFETIME, horizon_epoch=created + HORIZON)


def run(attempt, out):
    total = reserve(out)
    state = client = None
    record = dict(status='preflight', started_utc=preflight.utc_now(), creation_attempted=False,
                  creation_uncertain=False, total_reserved_usd=total)
    try:
        frozen = shared.load(AUDIT / 'packages' / (PROFILE + '-FREEZE.json'))
        assert digest(transport.BUNDLE) == frozen['bundle_sha256']
        assert digest(Path(__file__)) == frozen['controller_sha256']
        assert digest(ROOT / 'scripts/cm_component_execution_remote.py') == frozen['remote_sha256']
        assert digest(ROOT / 'scripts/runpod_query_ladder_q64_second_host_v3_controller.py') == frozen['transport_sha256']
        assert digest(transport.BOOTSTRAP) == frozen['bootstrap_sha256']
        offer = preflight.get_offer('cpu3g')
        if not offer['eligible'] or not 0 < offer['rate_usd_per_hour'] <= .10:
            raise RuntimeError('eligible CPU quote absent')
        client = preflight.session()
        inventory = shared.inventories(client)
        check_inventory(inventory)
        response = client.post('https://api.runpod.io/graphql',
                               json={'query':'query { myself { clientBalance currentSpendPerHr spendLimit } }'},
                               timeout=15, allow_redirects=False)
        if response.status_code != 200: raise RuntimeError('account check HTTP failure')
        body = response.json()
        if body.get('errors'): raise RuntimeError('account check failed')
        account = body['data']['myself']
        credit_ok = float(account['clientBalance']) >= RESERVATION
        spend_ok = float(account['spendLimit']) >= float(account['currentSpendPerHr']) + .11
        shared.write(out / 'PREFLIGHT.json', dict(offer=offer, inventories=inventory,
                                                credit_sufficient=credit_ok, spend_limit_sufficient=spend_ok))
        if not credit_ok or not spend_ok: raise RuntimeError('account funding limit failed')
        watchdog = arm_watchdog(attempt, out)
        created = time.time()
        state = create_state(created)
        token = secrets.token_urlsafe(32)
        payload = transport.create_payload(state['name'], offer, token, created)
        shared.write(shared.STATE, state)
        shared.confirm_watchdog(watchdog, state)
        record.update(creation_attempted=True, creation_uncertain=True, name=state['name'])
        print(json.dumps(dict(action='create CPU pod', rate_usd_per_hour=offer['rate_usd_per_hour'],
                              reserved_usd=RESERVATION)), flush=True)
        response = client.post(preflight.V1 + '/pods', json=payload, timeout=(10, 50), allow_redirects=False)
        record['creation_http_status'] = response.status_code
        if response.status_code not in (200, 201):
            record['creation_uncertain'] = not 400 <= response.status_code < 500
            raise RuntimeError('creation HTTP ' + str(response.status_code))
        pod = response.json()
        pod = pod.get('pod', pod)
        pod_id = pod.get('id')
        if not isinstance(pod_id, str) or not re.fullmatch(r'[a-z0-9]{8,40}', pod_id):
            raise RuntimeError('invalid assigned identity')
        shared.write(shared.IDENTITY, dict(pod_id=pod_id, name=state['name']))
        record.update(pod_id=pod_id, creation_uncertain=False)
        pod = shared.actual_pod(client, pod_id)
        resources = shared.validate_pod(pod, state, offer)
        if resources['ram_gb'] < 8: raise RuntimeError('assigned RAM below campaign requirement')
        machine_id = pod.get('machineId') or (pod.get('machine') or {}).get('id')
        if not isinstance(machine_id, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,200}', machine_id):
            raise RuntimeError('invalid machine placement identity')
        record['actual_resources'] = resources
        shared.write(out / 'RESOURCE_CHECK.json', dict(**resources, machine_id=machine_id))
        log = transport.execute_remote(pod_id, machine_id, token, created, record)
        record['evidence'] = evidence(log, out)
        if record['evidence']['remote']['status'] != 'complete': raise RuntimeError('remote campaign failed')
        record['status'] = 'complete'
    except Exception as exc:
        record.update(status='failed', error_type=type(exc).__name__)
        # Network exceptions can contain request details. Only our own simple
        # validation messages are saved; never API bodies, headers or environments.
        if type(exc) in (RuntimeError, AssertionError, ValueError): record['error'] = str(exc)
        if state is not None and not shared.ABORT.exists():
            shared.write(shared.ABORT, dict(reason=type(exc).__name__))
    finally:
        if state is not None and client is not None:
            try:
                record['cleanup'] = shared.cleanup_owned(client, state, 'controller')
                if record['cleanup']['owned_pod_absent'] and not record['creation_uncertain']:
                    shared.write(shared.DONE, dict(owned_pod_absent_verified=True, finished_utc=preflight.utc_now()))
            except Exception as exc: record['cleanup_error_type'] = type(exc).__name__
        elif not shared.DONE.exists(): shared.write(shared.DONE, dict(no_create_request=True))
        if state is not None:
            record['elapsed_since_create_s'] = time.time() - state['created_epoch']
            rate = record.get('actual_resources', {}).get('rate_usd_per_hour', .10)
            record['cost_upper_bound_usd'] = (rate + .01) * record['elapsed_since_create_s'] / 3600 if record['creation_attempted'] else 0.0
        record['finished_utc'] = preflight.utc_now()
        shared.write(out / 'RUN.json', record)
        if client is not None: client.close()
    print(json.dumps(record, indent=2), flush=True)
    return int(record['status'] != 'complete' or not record.get('cleanup', {}).get('owned_pod_absent'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('run', 'watchdog', 'preflight'))
    parser.add_argument('--attempt', default='attempt-001')
    parser.add_argument('--profile', default='component-historical-v2')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,60}', args.profile): raise ValueError('invalid profile')
    if args.action == 'preflight':
        client = preflight.session()
        try:
            inventory = shared.inventories(client)
            check_inventory(inventory)
            offers = {name:preflight.get_offer(name) for name in ('cpu3c','cpu3g')}
            result = dict(checked_utc=preflight.utc_now(), inventories=inventory, offers=offers, budget_usd=BUDGET)
            shared.write(AUDIT/'PREFLIGHT.json', result)
            print(json.dumps(result, indent=2))
        finally: client.close()
        return 0
    out = configure(args.attempt, args.profile)
    with awake():
        return shared.watchdog() if args.action == 'watchdog' else run(args.attempt, out)


if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(json.dumps(dict(error_type=type(exc).__name__)), flush=True)
        raise SystemExit(2)
