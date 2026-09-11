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
AUDIT = ROOT / 'docs/audits/2026-09-11-cm-bucket-counts'
PRIOR = ROOT / 'docs/audits/2026-09-11-cm-scalar-research'
CARRIED_RESERVATIONS = .54
PRIOR_MANIFEST = '3f2667a8c8dda1bcbafeef71662bba9c61ae6b6c8d96178801b2a724595c8a48'
spec = importlib.util.spec_from_file_location('prior_packed_transport', ROOT / 'scripts/runpod_query_ladder_q64_second_host_v3_controller.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
shared, preflight = transport.shared, transport.preflight
RESERVATION = 0.18
BUDGET = 5.0
LIFETIME = 5400
HORIZON = 5700
TESTS = [
    'test_bucket_numpy', 'test_bucket_counts', 'test_bucket_cudd_reference',
    'test_scalar_research',
    'test_packed_stream_io', 'test_packed_io_campaign', 'test_packed_remote_bootstrap', 'test_packed_cloud_freeze',
    'test_packed_queries', 'test_packed_queries_campaign',
    'test_packed_mask_construction', 'test_bitset_backend', 'test_bitset_cse',
    'test_prepared_flat_evaluation', 'test_bitset_engine_policy', 'test_context_caches',
    'test_build_memo', 'test_cm_persistent_ir_cache', 'test_persistent_path_consistency',
    'test_foreign_node_interning', 'test_share_aware_flatten', 'test_expr_serde_v2', 'test_output_budget',
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configure(attempt):
    if not re.fullmatch(r'attempt-[0-9]{3}', attempt): raise ValueError('invalid attempt')
    transport.OUT = AUDIT / attempt
    transport.BUNDLE = AUDIT / 'NUMPY-payload.zip'
    transport.EXPECTED_BUNDLE_BYTES = transport.BUNDLE.stat().st_size
    transport.EXPECTED_BUNDLE_SHA256 = digest(transport.BUNDLE)
    transport.REMOTE_CODE = (ROOT / 'scripts/cm_runpod_packed_remote.py').read_text()
    transport.HARD_LIFETIME_SECONDS = LIFETIME
    transport.RECONCILIATION_SECONDS = HORIZON
    transport.RATE_CAP_USD_PER_HOUR = .10
    transport.TOTAL_COST_CAP_USD = RESERVATION
    transport.CPU_FLAVOR = 'cpu3g'
    transport.configure_transport()
    return transport.OUT


def commands(profile='full'):
    out = '/workspace/cm-packed-evidence/bucket-numpy'
    return [dict(name='correctness', args=['-m', 'pytest', *['tests/' + n + '.py' for n in TESTS],
                 '-q', '-p', 'no:cacheprovider', '--basetemp', '/workspace/cm-pytest',
                 '--junitxml', '/workspace/cm-packed-evidence/TESTS.xml'], timeout=300),
            *[dict(name='bucket-' + action, args=['-m', 'scripts.cm_bucket_numpy_campaign', action,
                    '--output', out], timeout=2400 if action == 'run' else 600)
              for action in ('run', 'memory', 'verify')]]


def source_closure(initial):
    seen, pending = set(), list(initial)
    def add_module(name):
        parts = name.split('.')
        for i in range(1, len(parts) + 1):
            path = ROOT.joinpath(*parts[:i])
            for candidate in (path.with_suffix('.py'), path / '__init__.py'):
                if candidate.is_file() and candidate.relative_to(ROOT).as_posix() not in seen:
                    pending.append(candidate.relative_to(ROOT).as_posix())
    while pending:
        name = pending.pop()
        if name in seen: continue
        path = ROOT / name
        if path.suffix != '.py' or any(p.startswith('.') for p in path.relative_to(ROOT).parts):
            raise ValueError('non-source upload candidate')
        seen.add(name)
        package = list(Path(name).parent.parts)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node, ast.Import):
                for alias in node.names: add_module(alias.name)
            elif isinstance(node, ast.ImportFrom):
                prefix = package[:len(package) - node.level + 1] if node.level else []
                module = '.'.join(prefix + ([node.module] if node.module else []))
                if module: add_module(module)
                for alias in node.names:
                    if alias.name != '*': add_module('.'.join(filter(None, (module, alias.name))))
    return sorted(seen)


def prepare(profile='full'):
    initial = ['scripts/cm_bucket_numpy_campaign.py', 'tests/conftest.py',
               *['tests/' + name + '.py' for name in TESTS]]
    files = source_closure(initial)
    data = [AUDIT / name for name in ('CORPUS.json', 'FIXTURES.json', 'SCHEDULE.json', 'PROTOCOL.json', 'ADMISSION.json', 'NUMPY-FIXTURES.json', 'NUMPY-SCHEDULE.json', 'NUMPY-PROTOCOL.md')]
    data += sorted((AUDIT / 'corpus').iterdir())
    if any(not p.is_file() or p.suffix not in ('.json', '.dimacs', '.md', '') for p in data):
        raise ValueError('unapproved corpus upload candidate')
    files += [p.relative_to(ROOT).as_posix() for p in data]
    source = dict(schema='cm-packed-cloud-source/v1', files={name: digest(ROOT / name) for name in files},
                  git_checkpoint=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    payload = AUDIT / 'NUMPY-payload.zip'
    with zipfile.ZipFile(payload, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in files: archive.write(ROOT / name, name)
        archive.writestr('SOURCE_MANIFEST.json', json.dumps(source, indent=2))
        archive.writestr('COMMANDS.json', json.dumps(commands(profile), indent=2))
        archive.write(AUDIT / 'DEPENDENCIES.json', 'DEPENDENCIES.json')
    if payload.stat().st_size > 4 << 20: raise ValueError('payload cap exceeded')
    source.update(profile=profile, bundle_sha256=digest(payload), bundle_bytes=payload.stat().st_size,
                  controller_sha256=digest(Path(__file__)),
                  remote_sha256=digest(ROOT / 'scripts/cm_runpod_packed_remote.py'),
                  transport_sha256=digest(ROOT / 'scripts/runpod_query_ladder_q64_second_host_v3_controller.py'),
                  bootstrap_sha256=digest(transport.BOOTSTRAP))
    shared.write(AUDIT / 'NUMPY-SOURCE_FREEZE.json', source)
    shared.write(AUDIT / 'NUMPY-AUTHORIZATION.json', dict(
        user_instruction='Please continue with the remaining research, you have authorization for the $5 for Runpod again - across the board, retrying failed testing and all.',
        budget_usd=BUDGET, attempt_reservation_usd=RESERVATION, carried_reservations_usd=CARRIED_RESERVATIONS,
        continuation_instruction='Ok, great! Nicely done. Please continue on anything that is left.', prior_manifest_sha256=PRIOR_MANIFEST,
        source_export_and_owned_resource_cleanup=True, recorded_utc=preflight.utc_now(),
        bundle_sha256=source['bundle_sha256']))
    print(json.dumps(dict(source_files=len(files), bundle_bytes=source['bundle_bytes'], budget_usd=BUDGET)))


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
        proc = subprocess.Popen([sys.executable, '-B', str(Path(__file__)), 'watchdog', '--attempt', attempt],
                                stdout=stream, stderr=subprocess.STDOUT, close_fds=True,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) |
                                              getattr(subprocess, 'DETACHED_PROCESS', 0))
    for _ in range(200):
        if shared.READY.exists():
            ready = shared.load(shared.READY)
            if not ready.get('network_probe_passed') or any(ready['startup_inventories'].values()):
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


def run(attempt, out):
    # Exclusive reservations persist even after failures; no optimistic refund.
    previous = sorted(AUDIT.glob('attempt-*/RESERVATION.json'))
    assert digest(PRIOR / 'FINAL-MANIFEST.json') == PRIOR_MANIFEST
    prior_cost = shared.load(PRIOR / 'COST-AND-CLEANUP.json')
    assert prior_cost['reserved_usd'] == CARRIED_RESERVATIONS
    assert all(shared.load(p)['cleanup']['owned_pod_absent'] for p in PRIOR.glob('attempt-*/RUN.json'))
    total = CARRIED_RESERVATIONS + math.fsum(shared.load(p)['reserved_usd'] for p in previous) + RESERVATION
    if total > BUDGET: raise RuntimeError('campaign budget exhausted')
    for path in previous:
        receipt = path.parent / 'RUN.json'
        if not receipt.exists(): raise RuntimeError('previous attempt has unresolved ownership')
        old = shared.load(receipt)
        if old.get('creation_attempted') and (old.get('creation_uncertain') or not old.get('cleanup', {}).get('owned_pod_absent')):
            raise RuntimeError('previous resource cleanup unresolved')
    out.mkdir(exist_ok=False)
    shared.write(out / 'RESERVATION.json', dict(reserved_usd=RESERVATION, total_reserved_usd=total,
                                              budget_usd=BUDGET, recorded_utc=preflight.utc_now()))
    state = client = None
    record = dict(status='preflight', started_utc=preflight.utc_now(), creation_attempted=False,
                  creation_uncertain=False, total_reserved_usd=total)
    try:
        frozen = shared.load(AUDIT / 'NUMPY-SOURCE_FREEZE.json')
        assert digest(transport.BUNDLE) == frozen['bundle_sha256']
        assert digest(Path(__file__)) == frozen['controller_sha256']
        assert digest(ROOT / 'scripts/cm_runpod_packed_remote.py') == frozen['remote_sha256']
        assert digest(ROOT / 'scripts/runpod_query_ladder_q64_second_host_v3_controller.py') == frozen['transport_sha256']
        assert digest(transport.BOOTSTRAP) == frozen['bootstrap_sha256']
        offer = preflight.get_offer('cpu3g')
        if not offer['eligible'] or not 0 < offer['rate_usd_per_hour'] <= .10:
            raise RuntimeError('eligible CPU quote absent')
        client = preflight.session()
        inventory = shared.inventories(client)
        if any(inventory.values()): raise RuntimeError('expected zero-pod baseline changed')
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
        state = dict(name='cm-c7-linux-' + uuid.uuid4().hex[:12], created_epoch=created,
                     cleanup_epoch=created + LIFETIME, horizon_epoch=created + HORIZON)
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
            record['cost_upper_bound_usd'] = (rate + .01) * record['elapsed_since_create_s'] / 3600
        record['finished_utc'] = preflight.utc_now()
        shared.write(out / 'RUN.json', record)
        if client is not None: client.close()
    print(json.dumps(record, indent=2), flush=True)
    return int(record['status'] != 'complete' or not record.get('cleanup', {}).get('owned_pod_absent'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run', 'watchdog'))
    parser.add_argument('--attempt', default='attempt-002')
    parser.add_argument('--profile', choices=('full',), default='full')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.profile)
        return 0
    out = configure(args.attempt)
    with awake():
        return shared.watchdog() if args.action == 'watchdog' else run(args.attempt, out)


if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(json.dumps(dict(error_type=type(exc).__name__)), flush=True)
        raise SystemExit(2)
