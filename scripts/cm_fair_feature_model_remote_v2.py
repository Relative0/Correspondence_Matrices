"""Bounded Linux execution of the sealed component and historical packages."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import signal
import subprocess
import sys
import time
import urllib.request
import zipfile

ROOT = Path('/workspace/cm-fair-fm')
OUT = Path('/workspace/cm-fair-fm-evidence')
CAP = 32 << 20


def emit(kind, **values):
    print('CM_EVENT ' + json.dumps(dict(kind=kind, **values)), flush=True)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def unpack(raw, destination):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert sum(i.file_size for i in archive.infolist()) < 128 << 20
        assert len(set(archive.namelist())) == len(archive.namelist())
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            assert not path.is_absolute() and '..' not in path.parts and ':' not in item.filename and not item.is_dir()
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(archive.read(item))


def run(label, command, timeout, cwd, allow_failure=False):
    emit('stage', name=label)
    start = time.monotonic()
    timed_out = False
    with (OUT / 'transport' / (label + '.log')).open('xb') as log:
        process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait(timeout=10)
    result = dict(command=command, cwd=str(cwd), exit_code=code, timed_out=timed_out,
                  elapsed_s=time.monotonic() - start)
    write(OUT / 'transport' / (label + '.json'), result)
    if (code or timed_out) and not allow_failure:
        raise RuntimeError(label + (' timeout' if timed_out else ' exit ' + str(code)))
    return result


def verify_files(root, rows):
    for row in rows:
        path = (root / row['path']).resolve()
        assert path.is_relative_to(root.resolve())
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], row['path']


def main():
    ROOT.mkdir(parents=True, exist_ok=False)
    (OUT/'transport').mkdir(parents=True, exist_ok=False)
    result=dict(status='failed',started_epoch=time.time())
    try:
        raw=Path(os.environ['CM_BUNDLE_PATH']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==os.environ['CM_BUNDLE_SHA256']
        unpack(raw,ROOT)
        manifest=json.loads((ROOT/'PROTOCOL.json').read_bytes())
        verify_files(ROOT,manifest['files'])
        deps=json.loads((ROOT/'DEPENDENCIES.json').read_bytes())
        downloads=ROOT/'downloads'
        downloads.mkdir()
        for item in deps:
            with urllib.request.urlopen(item['url'],timeout=60) as response:
                payload=response.read(item['bytes']+1)
            assert len(payload)==item['bytes'] and hashlib.sha256(payload).hexdigest()==item['sha256']
            with (downloads/item['filename']).open('xb') as stream: stream.write(payload)
        py=[sys.executable,'-X','utf8','-B']
        for names,label in [({'setuptools','wheel'},'build-tools'),
                            ({d['name'] for d in deps}-{'setuptools','wheel'},'dependencies')]:
            run(label,py+['-m','pip','install','--no-deps','--no-build-isolation','--no-index',
                '--report',str(OUT/'transport'/(label+'-pip.json')),
                *[str(downloads/d['filename']) for d in deps if d['name'] in names]],120,ROOT)
        run('dependency-check',py+['-m','pip','check'],30,ROOT)
        run('native-preflight',py+['-c',
            "from dd import cudd; import numpy; assert cudd.__file__.endswith('.so'); print(cudd.__file__); print(numpy.__version__)"],30,ROOT)
        run('contract-tests',py+['-m','unittest','discover','-s','tests',
            '-p','test_cm_fair_feature_model_benchmark.py','-v'],45,ROOT)
        write(OUT/'transport/PLACEMENT.json',dict(machine_id=os.environ['CM_RUNPOD_MACHINE_ID'],
            image=os.environ['CM_IMAGE_TAG'],digest=os.environ['CM_IMAGE_DIGEST'],python=sys.version,
            cpuinfo=Path('/proc/cpuinfo').read_text(),meminfo=Path('/proc/meminfo').read_text(),
            thread_limit=1,api_credential_present=False))
        # Pin every worker to the same logical CPU, while retaining the available mask.
        available=sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0,{available[0]})
        write(OUT/'transport/AFFINITY.json',dict(available=available,selected=available[0]))
        result['study']=run('study',py+['scripts/cm_fair_feature_model_benchmark.py','run',
            '--protocol',str(ROOT/'PROTOCOL.json'),'--output',str(OUT/'study')],1920,ROOT,True)
        verify_files(ROOT,manifest['files'])
        if result['study']['exit_code']==0 and not result['study']['timed_out']:
            result['status']='complete'
    except Exception as exc:
        result['error_type']=type(exc).__name__
        if type(exc) in (AssertionError,RuntimeError,ValueError): result['error']=str(exc)
    finally:
        result['finished_epoch']=time.time()
        write(OUT/'transport/REMOTE_RESULT.json',result)
        paths=sorted(p for p in OUT.rglob('*') if p.is_file())
        total=sum(p.stat().st_size for p in paths)
        assert total<CAP*3//4
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
            for path in paths: archive.write(path,path.relative_to(OUT).as_posix())
        raw=buffer.getvalue()
        assert len(raw)+total<CAP
        encoded=base64.b64encode(raw).decode('ascii')
        chunks=[encoded[i:i+48000] for i in range(0,len(encoded),48000)]
        digest=hashlib.sha256(raw).hexdigest()
        emit('evidence_start',bytes=len(raw),sha256=digest,chunks=len(chunks),uncompressed_bytes=total)
        for index,chunk in enumerate(chunks): print(f'CM_EVIDENCE {index} {chunk}',flush=True)
        emit('evidence_end',sha256=digest)
        emit('done',status=result['status'])

if __name__=='__main__': main()
