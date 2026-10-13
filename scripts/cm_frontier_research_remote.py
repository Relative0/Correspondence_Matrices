"""Fixed remote program for the authorized packed-query continuation."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import signal
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

ROOT = Path('/workspace/cm-packed-continuation')
OUT = Path('/workspace/cm-packed-evidence')
CAP = 32 << 20


def emit(kind, **values):
    print('CM_EVENT ' + json.dumps(dict(kind=kind, **values)), flush=True)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def run(label, command, timeout, allow_failure=False):
    emit('stage', name=label)
    start = time.monotonic()
    with (OUT / 'transport' / (label + '.log')).open('xb') as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            result = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
            raise RuntimeError(label + ' timeout')
    write(OUT / 'transport' / (label + '.json'), dict(command=command, exit_code=result,
                                                   elapsed_s=time.monotonic() - start))
    if result and not allow_failure:
        raise RuntimeError(label + ' exit ' + str(result))


def main():
    ROOT.mkdir(parents=True, exist_ok=False)
    (OUT / 'transport').mkdir(parents=True, exist_ok=False)
    result = dict(status='failed', started_epoch=time.time())
    try:
        # The existing public source revision supplies the broad test fixtures.
        # Fetch into a new checkout; the exact commit is pinned by the package.
        run('public-source', ['git', '-C', str(ROOT), 'init', '-q'], 30)
        run('public-fetch', ['git', '-C', str(ROOT), 'fetch', '--depth', '1',
            'https://github.com/Relative0/Correspondence_Matrices.git',
            'd7b94d1941266daddc3bb2a7cda8277e1d6595b0'], 300)
        run('public-checkout', ['git', '-C', str(ROOT), 'checkout', '--detach', 'FETCH_HEAD'], 120)
        raw = Path(os.environ['CM_BUNDLE_PATH']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == os.environ['CM_BUNDLE_SHA256']
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            assert sum(i.file_size for i in archive.infolist()) < 128 << 20
            for item in archive.infolist():
                path = PurePosixPath(item.filename)
                assert not path.is_absolute() and '..' not in path.parts and not item.is_dir()
                target = ROOT / path
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('wb') as stream: stream.write(archive.read(item))
        hydration = json.loads((ROOT / 'PUBLIC_FIXTURES.json').read_text())
        for item in hydration:
            path = PurePosixPath(item['path'])
            assert not path.is_absolute() and '..' not in path.parts and ':' not in item['path']
            assert item['url'].startswith('https://raw.githubusercontent.com/lsils/benchmarks/0060e156826e733d69bf5b3322d1bdd0d03a1f9a/')
            assert item['bytes'] < 32 << 20
            with urllib.request.urlopen(item['url'], timeout=60) as response:
                data = response.read(item['bytes'] + 1)
            assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
            target = ROOT/path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        write(OUT/'transport'/'PUBLIC_FIXTURE_VERIFICATION.json', hydration)
        source = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text())
        for name, expected in source['files'].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
        write(OUT / 'transport' / 'SOURCE_VERIFICATION.json', source)
        write(OUT / 'transport' / 'PLACEMENT.json', dict(
            runpod_machine_id=os.environ['CM_RUNPOD_MACHINE_ID'], image=os.environ['CM_IMAGE_TAG'],
            digest=os.environ['CM_IMAGE_DIGEST'], cpuinfo=Path('/proc/cpuinfo').read_text(),
            meminfo=Path('/proc/meminfo').read_text(), vm_allowed=True,
            api_credential_present=False, thread_limit=1))
        emit('stage', name='dependency-download')
        deps = json.loads((ROOT / 'DEPENDENCIES.json').read_text())
        downloads = ROOT / 'downloads'
        downloads.mkdir()
        for item in deps:
            with urllib.request.urlopen(item['url'], timeout=60) as response:
                data = response.read(item['bytes'] + 1)
            assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
            (downloads / item['filename']).write_bytes(data)
        # Install the pinned build support first; sdists are the upstream pure
        # Python astutils/ply releases. No implicit dependency resolution.
        support = [str(downloads / d['filename']) for d in deps if d['name'] in ('setuptools', 'wheel', 'packaging')]
        run('build-support', [sys.executable, '-m', 'pip', 'install', '--no-deps', *support], 120)
        paths = [str(downloads / d['filename']) for d in deps if d['name'] not in ('setuptools', 'wheel', 'packaging')]
        run('dependencies', [sys.executable, '-m', 'pip', 'install', '--no-deps', '--no-build-isolation',
                             '--report', str(OUT / 'transport' / 'pip-report.json'), *paths], 180)
        run('dependency-check', [sys.executable, '-m', 'pip', 'check'], 30)
        tool = json.loads((ROOT/'TOOLS.json').read_text())['node']
        with urllib.request.urlopen(tool['url'], timeout=60) as response:
            payload = response.read((64 << 20) + 1)
        assert len(payload) <= 64 << 20 and hashlib.sha256(payload).hexdigest() == tool['sha256']
        bindir = ROOT/'tools_bin'; bindir.mkdir()
        with tarfile.open(fileobj=io.BytesIO(payload), mode='r:xz') as archive:
            member = archive.getmember(tool['filename'].removesuffix('.tar.xz')+'/bin/node')
            assert member.isfile() and member.size < 200 << 20
            (bindir/'node').write_bytes(archive.extractfile(member).read())
        (bindir/'node').chmod(0o755)
        os.environ['PATH'] = str(bindir) + os.pathsep + os.environ['PATH']
        run('node-version', [str(bindir/'node'), '--version'], 10)
        commands = json.loads((ROOT / 'COMMANDS.json').read_text())
        for item in commands:
            run(item['name'], [sys.executable, '-B', *item['args']], item['timeout'], item.get('allow_failure', False))
        result['status'] = 'complete'
    except Exception as exc:
        result.update(error_type=type(exc).__name__, error=str(exc))
    finally:
        result['finished_epoch'] = time.time()
        write(OUT / 'transport' / 'REMOTE_RESULT.json', result)
        paths = sorted(p for p in OUT.rglob('*') if p.is_file())
        assert sum(p.stat().st_size for p in paths) < CAP // 2
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in paths: archive.write(path, path.relative_to(OUT).as_posix())
        raw = buffer.getvalue()
        encoded = base64.b64encode(raw).decode('ascii')
        chunks = [encoded[i:i+48000] for i in range(0, len(encoded), 48000)]
        digest = hashlib.sha256(raw).hexdigest()
        emit('evidence_start', bytes=len(raw), sha256=digest, chunks=len(chunks),
             uncompressed_bytes=sum(p.stat().st_size for p in paths))
        for index, chunk in enumerate(chunks): print(f'CM_EVIDENCE {index} {chunk}', flush=True)
        emit('evidence_end', sha256=digest)
        emit('done', status=result['status'])


if __name__ == '__main__':
    main()
