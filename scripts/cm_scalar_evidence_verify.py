"""Read-only reconstruction of scalar campaign source and exactness receipts."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT/'docs/audits/2026-09-11-cm-scalar-research'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def verify():
    attempts = [('attempt-001', '', 'runpod_scalar_research_controller.py', 'scalar'),
                ('attempt-002', 'M4RI-', 'runpod_scalar_m4ri_controller.py', 'm4ri'),
                ('attempt-003', 'BINDING-', 'runpod_scalar_binding_controller.py', 'binding')]
    records = []
    for attempt, prefix, controller, folder in attempts:
        frozen = read(AUDIT/(prefix+'SOURCE_FREEZE.json'))
        payload = AUDIT/(prefix.lower()+'payload.zip')
        assert sha(payload) == frozen['bundle_sha256']
        assert sha(ROOT/'scripts'/controller) == frozen['controller_sha256']
        assert sha(ROOT/'scripts/cm_runpod_packed_remote.py') == frozen['remote_sha256']
        assert sha(ROOT/'scripts/runpod_query_ladder_q64_second_host_v3_controller.py') == frozen['transport_sha256']
        changed = []
        with zipfile.ZipFile(payload) as archive:
            source = json.loads(archive.read('SOURCE_MANIFEST.json'))
            assert source['files'] == frozen['files']
            for name, expected in source['files'].items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == expected
                if sha(ROOT/name) != expected: changed.append(name)
        expected_changes = [] if prefix == 'BINDING-' else ['cmbench/backends/affine_constraints.py']
        assert sorted(changed) == expected_changes
        base = AUDIT/attempt; evidence = base/'evidence'
        receipt = read(base/'RUN.json')
        assert receipt['status'] == 'complete' and receipt['cleanup']['owned_pod_absent']
        assert not any(receipt['cleanup']['inventories'].values())
        assert sha(base/'evidence.zip') == receipt['evidence']['sha256']
        with zipfile.ZipFile(base/'evidence.zip') as archive:
            for member in archive.infolist():
                assert hashlib.sha256(archive.read(member)).hexdigest() == sha(evidence/member.filename)
        assert read(evidence/'transport/SOURCE_VERIFICATION.json') == source
        suite = ET.parse(evidence/'TESTS.xml').getroot()[0]
        assert all(int(suite.attrib[k]) == 0 for k in ('errors', 'failures', 'skipped'))
        rows = [json.loads(line) for line in (evidence/folder/'RAW.jsonl').read_text().splitlines()]
        if folder == 'scalar': schedule = read(AUDIT/'SCHEDULE.json')
        elif folder == 'binding': schedule = read(AUDIT/'BINDING-SCHEDULE.json')
        else: schedule = read(evidence/folder/'FREEZE.json')['schedule']
        assert [{k: r[k] for k in ('case', 'q', 'repeat', 'method')} for r in rows] == schedule
        grouped = {}
        for row in rows:
            assert row['exact'] and row['total_ns'] == row['setup_ns']+row['query_ns']+row['cleanup_ns']
            assert row['warm_ns'] > 0
            key = (row['case'], row['q'])
            grouped.setdefault(key, row['result'])
            assert grouped[key] == row['result']
        if folder != 'm4ri':
            oracle = {(r['case'], r['q']): r['result'] for r in read(evidence/folder/'ORACLES.json')}
            assert grouped == oracle
        memory = read(evidence/folder/'MEMORY.json')
        assert len(memory) == {'scalar': 96, 'm4ri': 9, 'binding': 12}[folder]
        assert all(m['after']['VmHWM'] >= m['after']['VmRSS'] > 0 for m in memory)
        for m in memory:
            case = m.get('case', 'n_1800_k_0902_gap_28' if folder == 'm4ri' else 'fresh-binding-n2048')
            assert m['result'] == grouped[(case, 8 if folder == 'binding' else 1)]
        records.append(dict(attempt=attempt, cells=len(rows), timed_outputs=2*sum(r['q'] for r in rows),
                            memory_children=len(memory), junit_tests=int(suite.attrib['tests']),
                            source_files=len(source['files']), preserved_prior_version_differences=changed))
    original = AUDIT/'revisions/pre-binding/affine_constraints.py'
    assert sha(original) == read(AUDIT/'SOURCE_FREEZE.json')['files']['cmbench/backends/affine_constraints.py']
    for name, check in read(AUDIT/'PRIOR-AUDITS-VERIFIED.json').items():
        base = ROOT/'docs/audits'/name; p = base/'FINAL-MANIFEST.json'
        assert sha(p) == check['manifest_sha256']
        manifest = read(p)
        for field in ('artifacts', 'current_sources', 'owned_sources'):
            for rel, entry in manifest.get(field, {}).items():
                target = base/rel if field == 'artifacts' else ROOT/rel
                if not target.is_file(): target = ROOT/rel
                assert sha(target) == (entry if isinstance(entry, str) else entry['sha256'])
    return dict(exact=True, attempts=records, total_cells=sum(r['cells'] for r in records),
                total_timed_outputs=sum(r['timed_outputs'] for r in records),
                total_memory_children=sum(r['memory_children'] for r in records), prior_artifacts_unchanged=490)


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
