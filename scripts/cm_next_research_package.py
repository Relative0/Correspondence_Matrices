"""Freeze an explicit source overlay and pinned remote test dependencies."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT/'docs/audits/2026-09-11-cm-next-research'
CHECKOUT = ROOT/'build/cm-next'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def dependency(pair):
    name, version = pair
    with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json', timeout=30) as response:
        info = json.load(response)
    def score(item):
        filename = item['filename']
        if filename.endswith('.whl') and 'none-any' in filename: return 0
        if filename.endswith('.whl') and 'cp313-cp313-manylinux' in filename and 'x86_64' in filename: return 1
        if name == 'pyeda' and filename.endswith('.tar.gz'): return 2
        return 99
    candidates = sorted((item for item in info['urls'] if not item.get('yanked')), key=score)
    item = candidates[0]
    assert score(item) < 99, name
    return dict(name=name, version=version, filename=item['filename'], bytes=item['size'], sha256=item['digests']['sha256'], url=item['url'])

def dependencies():
    path = AUDIT/'DEPENDENCIES.json'
    if path.exists(): return
    previous = json.loads((ROOT/'docs/audits/2026-09-11-cm-bucket-counts/DEPENDENCIES.json').read_text())
    additional = {'sympy':'1.14.0', 'mpmath':'1.3.0', 'pandas':'2.3.2', 'python-dateutil':'2.9.0.post0',
        'pytz':'2025.2', 'tzdata':'2025.2', 'six':'1.17.0', 'pyeda':'0.29.0', 'requests':'2.32.5',
        'charset-normalizer':'3.4.3', 'idna':'3.10', 'urllib3':'2.5.0', 'certifi':'2025.8.3'}
    existing = {item['name'] for item in previous}
    with ThreadPoolExecutor(max_workers=6) as pool:
        previous.extend(pool.map(dependency, ((k,v) for k,v in additional.items() if k not in existing)))
    path.write_text(json.dumps(previous, indent=2)+'\n')
    node_version = 'v24.3.0'
    filename = 'node-'+node_version+'-linux-x64.tar.xz'
    with urllib.request.urlopen('https://nodejs.org/dist/'+node_version+'/SHASUMS256.txt', timeout=30) as response:
        sums = response.read().decode()
    digest = next(line.split()[0] for line in sums.splitlines() if line.split()[-1] == filename)
    (AUDIT/'TOOLS.json').write_text(json.dumps({'node':{'url':'https://nodejs.org/dist/'+node_version+'/'+filename, 'sha256':digest, 'filename':filename}}, indent=2)+'\n')

def package(profile):
    dependencies()
    sources = set(json.loads((AUDIT/'INTEGRATION-SOURCES.json').read_text())['sources'])
    native = json.loads((ROOT/'docs/audits/2026-09-11-cm-continuation/NATIVE_SOURCE.json').read_text())
    # These pre-existing native experiment sources have their own snapshot.
    extras = ['cmbench/comparative/gf2_native_slot_batch.py', 'scripts/build_cm_fused_slots_batch.py',
        'scripts/cm_native_slot_batch_campaign.py', 'scripts/cm_native_slot_batch_freeze.py',
        'scripts/crse_native_slot_batch_campaign_verify.py', 'scripts/crse_native_slot_batch_freeze_verify.py',
        'tests/test_cm_comparative_native_slot_batch.py', 'native/cm_fused_slots_batch/fused_slot_executor_batch.c',
        'native/cm_fused_slots_batch/build_msvc.cmd']
    for relative in extras:
        if relative in native:
            assert sha(ROOT/relative) == native[relative], relative
        target = CHECKOUT/relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/relative, target)
        sources.add(relative)
    addition = AUDIT/(profile+'-SOURCES.json')
    if addition.exists(): sources.update(json.loads(addition.read_text()))
    if profile == 'regression':
        commands = [dict(name='full-regression', args=['-m','pytest','tests','-q','--tb=short','--continue-on-collection-errors',
            '-p','no:cacheprovider','--basetemp','/workspace/cm-pytest',
            '--junitxml','/workspace/cm-packed-evidence/FULL-TESTS.xml'], timeout=2400, allow_failure=True)]
    else:
        commands = json.loads((AUDIT/(profile+'-COMMANDS.json')).read_text())
    destination = AUDIT/'packages'; destination.mkdir(exist_ok=True)
    bundle = destination/(profile+'.zip')
    manifest = {'base_commit':'d15cb618f4eb99b6621e4ab24773a00f03ae484e', 'files':{p:sha(CHECKOUT/p) for p in sorted(sources)}}
    for relative in sources:
        assert '..' not in Path(relative).parts and not any(part.startswith('.') for part in Path(relative).parts)
        assert (CHECKOUT/relative).suffix in ('.py','.md','.c','.cmd','.json','.dimacs','.txt','.zip'), relative
    with zipfile.ZipFile(bundle,'x',zipfile.ZIP_DEFLATED) as archive:
        for relative in sorted(sources): archive.write(CHECKOUT/relative,relative)
        archive.writestr('SOURCE_MANIFEST.json',json.dumps(manifest,indent=2))
        archive.writestr('COMMANDS.json',json.dumps(commands,indent=2))
        selected_dependencies = AUDIT/(profile+'-DEPENDENCIES.json')
        archive.write(selected_dependencies if selected_dependencies.exists() else AUDIT/'DEPENDENCIES.json','DEPENDENCIES.json')
        archive.write(AUDIT/'TOOLS.json','TOOLS.json')
    assert bundle.stat().st_size < 4 << 20
    freeze = dict(profile=profile, source=manifest, bundle_sha256=sha(bundle), bundle_bytes=bundle.stat().st_size,
        controller_sha256=sha(ROOT/'scripts/runpod_next_research_controller.py'),
        remote_sha256=sha(ROOT/'scripts/cm_next_research_remote.py'),
        transport_sha256=sha(ROOT/'scripts/runpod_query_ladder_q64_second_host_v3_controller.py'),
        bootstrap_sha256=sha(ROOT/'scripts/runpod_query_ladder_q64_bootstrap.py'))
    (destination/(profile+'-FREEZE.json')).write_text(json.dumps(freeze,indent=2)+'\n')
    print(json.dumps({'profile':profile,'overlay_files':len(sources),'bundle_bytes':freeze['bundle_bytes']}))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('profile'); args=parser.parse_args()
    assert re.fullmatch('[a-z0-9-]{1,60}',args.profile)
    package(args.profile)
