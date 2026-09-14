"""Retain a local replay of the frozen Windows packages without changing them."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SEALED = ROOT / 'docs/audits/2026-09-12-cm-component-execution'
AUDIT = ROOT / 'docs/audits/2026-09-12-cm-local-windows-replay'
SNAPSHOTS = ROOT / 'build/cm-local-windows-replay-20260912'
EXPECTED = '30d309367d64cb08fb10ab0cdd77f018fa513ba727116b5c96ed929c5814c015'
PACKAGES = (
    ('native', 'windows-supervised-replay.zip', 'scripts.cm_historical_windows_run'),
    ('reassessment', 'reassessment-supervised-replay.zip', 'scripts.cm_historical_reassessment_windows_run'),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')


def snapshot_hashes(snapshot):
    return {str(p.relative_to(snapshot)).replace('\\', '/'): digest(p)
            for p in sorted(snapshot.rglob('*')) if p.is_file()}


def run(snapshot, module, arguments, label):
    command = [sys.executable, '-X', 'utf8', '-B', '-m', module, *arguments]
    started = time.monotonic()
    with (AUDIT / (label + '.stdout.log')).open('xb') as out, \
            (AUDIT / (label + '.stderr.log')).open('xb') as err:
        completed = subprocess.run(command, cwd=snapshot, stdout=out, stderr=err)
    receipt = dict(command=command, cwd=str(snapshot), returncode=completed.returncode,
                   elapsed_s=time.monotonic() - started)
    write(AUDIT / (label + '.json'), receipt)
    print(json.dumps(dict(step=label, **receipt)), flush=True)
    return receipt


def main():
    started = time.monotonic()
    manifest_path = SEALED / 'FINAL-MANIFEST.json'
    if digest(manifest_path) != EXPECTED:
        raise ValueError('sealed manifest identity changed')
    manifest = json.loads(manifest_path.read_bytes())
    bindings = {r['path']: r for r in manifest['artifacts']}
    AUDIT.mkdir(exist_ok=False)
    SNAPSHOTS.mkdir(exist_ok=False)
    write(AUDIT / 'AUTHORIZATION-AND-ESTIMATE.json', dict(
        authorization='User authorized local tests if estimated below half an hour.',
        estimated_minutes='12-15', per_id_execution_cap_seconds=60, total_ids=10,
        aggregate_job_committed_memory_bytes=2 << 30, process_cap=32,
        external_spending_usd=0, original_manifest_sha256=EXPECTED,
        runner_source_sha256=digest(Path(__file__))))
    before = {}
    for name, filename, module in PACKAGES:
        archive = SEALED / 'packages' / filename
        binding = bindings['packages/' + filename]
        if archive.stat().st_size != binding['bytes'] or digest(archive) != binding['sha256']:
            raise ValueError('archive identity changed: ' + filename)
        snapshot = SNAPSHOTS / name
        snapshot.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                if not (snapshot / member.filename).resolve().is_relative_to(snapshot.resolve()):
                    raise ValueError('archive path escapes snapshot')
            bundle.extractall(snapshot)
        before[name] = snapshot_hashes(snapshot)
        write(AUDIT / (name + '-snapshot-before.json'), before[name])
        receipt = run(snapshot, module, [], name + '-preflight')
        if receipt['returncode']:
            raise RuntimeError(name + ' preflight failed; see retained logs')
    receipts = []
    for name, filename, module in PACKAGES:
        snapshot = SNAPSHOTS / name
        output = AUDIT / (name + '-001')
        receipts.append(run(snapshot, module, ['--execute', '--output', str(output)], name + '-execution'))
        after = snapshot_hashes(snapshot)
        write(AUDIT / (name + '-snapshot-after.json'), after)
        if after != before[name]:
            raise RuntimeError(name + ' snapshot changed; stop before further execution')
        result_path = output / ('RESULTS.json' if name == 'native' else 'RESULT.json')
        result = json.loads(result_path.read_bytes())
        rows = result['tests'] if name == 'native' else [result]
        if any(not row.get('resources', {}).get('cleanup_verified') for row in rows):
            raise RuntimeError('cleanup not verified; stop before further execution')
    write(AUDIT / 'CONTROLLER-RESULT.json', dict(
        elapsed_s=time.monotonic() - started, executions=receipts,
        snapshots_unchanged=True, sealed_manifest_unchanged=digest(manifest_path) == EXPECTED,
        external_spending_usd=0, performance_claims=False))


if __name__ == '__main__':
    main()
