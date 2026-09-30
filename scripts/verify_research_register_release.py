"""Verify published research records without launching any experiment."""
import argparse
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
import zipfile


def verify_bytes(data, record, label):
    if len(data) != record['bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
        raise ValueError('Hash/size mismatch: ' + label)


def verify_zip_manifest(archive, manifest_path, prefix=''):
    manifest = json.loads(archive.read(manifest_path))
    for row in manifest['files']:
        path = prefix + row['path']
        if '..' in PurePosixPath(path).parts or PurePosixPath(path).is_absolute():
            raise ValueError('Unsafe archive path: ' + path)
        verify_bytes(archive.read(path), row, path)
    return len(manifest['files'])


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=Path, required=True)
    args = parser.parse_args()
    site = args.site.resolve()
    root = site / 'results/2026-09-30/research-register'
    manifest = json.loads((root / 'artifact-manifest.json').read_text(encoding='utf-8'))
    for name, record in manifest['files'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Unsafe file path: ' + name)
        verify_bytes(path.read_bytes(), record, name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != set(manifest['files']) | {'artifact-manifest.json'}:
        raise ValueError('Unindexed release files')
    count = 0
    for path in sorted(root.rglob('*.zip')):
        with zipfile.ZipFile(path) as archive:
            if 'PUBLICATION_CONTENTS.json' in archive.namelist():
                count += verify_zip_manifest(archive, 'PUBLICATION_CONTENTS.json')
    with zipfile.ZipFile(root / 'gate-a-v4/Gate_A_V4_NO_GO_Qualification_Package.zip') as archive:
        count += verify_zip_manifest(archive, 'outputs/GATE_A_V4_DELIVERABLE_SHA256.json')
    with zipfile.ZipFile(root / 'gate-a-v5/Gate_A_V5_Candidate_20260924_01_NO_GO.zip') as archive:
        count += verify_zip_manifest(archive, 'candidate/CANDIDATE_MANIFEST_V5.json', 'candidate/')
        candidate = json.loads(archive.read('candidate/CANDIDATE_MANIFEST_V5.json'))
        assert candidate['authorization_to_execute'] is False
        assert len(candidate['empty_append_only_files']) == 6
        for row in candidate['empty_append_only_files']:
            assert archive.read('candidate/' + row['path']) == b''
    with zipfile.ZipFile(root / 't3/CM_Structural_Computation_C1-C4_T3_Phase2_2026-09-28.zip') as archive:
        prefix = 't3_phase2_computation_20260928/'
        count += verify_zip_manifest(archive, prefix + 'MANIFEST_SHA256.json', prefix)
        delivery = json.loads(archive.read(prefix + 'DELIVERY_VALIDATION.json'))
        assert delivery['campaign_executed_queries'] == 7445928
        assert delivery['cold_verified_passes'] == delivery['isolated_memory_passes'] == 115
        with zipfile.ZipFile(io.BytesIO(archive.read(prefix + 'PRIOR_PHASE_PACKAGE.zip'))) as prior:
            p = 'convergence_followthrough_20260928/'
            count += verify_zip_manifest(prior, p + 'MANIFEST_SHA256.json', p)
    with zipfile.ZipFile(root / 'compiler/Compiler_Studies_20260926_Publication.zip') as archive:
        p = 'CM Computation/'
        a = json.loads(archive.read(p + '03_STUDY_DESIGN_20260926/run_v4_001/ANALYSIS.json'))
        assert a['cases'] == 64 and a['primary_success'] is False
        b = json.loads(archive.read(p + '05_NATURAL_TIMING_20260926/run_natural_timing_001/ANALYSIS.json'))
        assert b['counts']['python_complete_cases'] == 70 and b['counts']['failure_rows'] == 1
    ledger = json.loads((root / 'experiment-register.json').read_text(encoding='utf-8'))
    assert len(ledger['studies']) == 16
    links = Links()
    links.feed((root / 'index.html').read_text(encoding='utf-8'))
    for href in links.links + [e for r in ledger['studies'] for e in r['evidence']]:
        parsed = urlsplit(href)
        if parsed.scheme or not parsed.path:
            continue
        target = (root / unquote(parsed.path)).resolve()
        if not target.is_relative_to(site) or not target.is_file():
            raise ValueError('Missing/unsafe local link: ' + href)
    guide = (site / 'p-series-study-guide.html').read_text(encoding='utf-8')
    assert 'section("research-register"' in guide
    assert 'does not yet publish the P1' not in guide
    print(json.dumps({'status': 'PASS', 'artifacts': len(manifest['files']),
                      'verified_archive_members': count, 'study_groups': len(ledger['studies'])}))


if __name__ == '__main__':
    main()
