"""Assemble pinned Linux payload and a scoped successor transport controller."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'docs/audits/2026-09-13-cm-fair-feature-model'


def main():
    deps=[]
    for name,version in [('numpy','2.3.2'),('dd','0.6.0'),('networkx','3.5'),
                         ('setuptools','80.9.0'),('wheel','0.45.1'),('astutils','0.0.6'),('ply','3.10')]:
        data=json.load(urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json',timeout=20))
        rows=data['urls']
        selected=[r for r in rows if ('cp313-cp313-manylinux' in r['filename'] and 'x86_64' in r['filename'])
                  or r['filename'].endswith('py3-none-any.whl')]
        if not selected: selected=[r for r in rows if r['filename'].endswith('.tar.gz')]
        assert len(selected)==1,(name,selected)
        r=selected[0]
        deps.append(dict(name=name,version=version,filename=r['filename'],bytes=r['size'],
                         sha256=r['digests']['sha256'],url=r['url']))
    (AUDIT/'source-v3/DEPENDENCIES.json').write_text(json.dumps(deps,indent=2)+'\n')
    prior=(ROOT/'scripts/cm_component_execution_remote.py').read_text()
    remote=prior[:prior.index('def main():')].replace('cm-component-execution','cm-fair-fm').replace('cm-component-evidence','cm-fair-fm-evidence')
    remote+='''def main():
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
        assert 'AssertionError' not in (OUT/'transport/contract-tests.log').read_text()
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
'''
    (ROOT/'scripts/cm_fair_feature_model_remote_v3.py').write_text(remote)
    controller=(ROOT/'scripts/runpod_component_diagnostics_controller_v2.py').read_text()
    replacements={
        "2026-09-12-cm-component-execution":"2026-09-13-cm-fair-feature-model",
        "component-historical-v2":"fair-feature-model-v3",
        "cm_component_execution_remote.py":"cm_fair_feature_model_remote_v3.py",
        "BUDGET = 5.00":"BUDGET = 2.00",
        "LIFETIME = 4800":"LIFETIME = 2700",
        "HORIZON = 5100":"HORIZON = 3000",
        "prior != 10.0":"prior != 13.0",
    }
    for old,new in replacements.items():
        assert old in controller,old
        controller=controller.replace(old,new)
    (ROOT/'scripts/runpod_fair_feature_model_controller_v3.py').write_text(controller)
    packages=AUDIT/'packages'
    packages.mkdir(exist_ok=True)
    bundle=packages/'fair-feature-model-v3.zip'
    with zipfile.ZipFile(bundle,'x',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((AUDIT/'source-v3').rglob('*')):
            if path.is_file(): archive.write(path,path.relative_to(AUDIT/'source-v3').as_posix())
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    freeze=dict(bundle_sha256=digest(bundle),
        controller_sha256=digest(ROOT/'scripts/runpod_fair_feature_model_controller_v3.py'),
        remote_sha256=digest(ROOT/'scripts/cm_fair_feature_model_remote_v3.py'),
        transport_sha256=digest(ROOT/'scripts/runpod_query_ladder_q64_second_host_v3_controller.py'),
        bootstrap_sha256=digest(ROOT/'scripts/runpod_frontier_bootstrap.py'))
    (packages/'fair-feature-model-v3-FREEZE.json').write_text(json.dumps(freeze,indent=2)+'\n')
    print(json.dumps(dict(bundle_bytes=bundle.stat().st_size,**freeze)))

if __name__=='__main__': main()
