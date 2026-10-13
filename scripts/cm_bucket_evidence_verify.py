"""Read-only reconstruction of both bucket campaigns and earlier audit seals."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT/'docs/audits/2026-09-11-cm-bucket-counts'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    records = []
    for attempt, prefix, controller, folder, memory_count in (
            ('attempt-001', '', 'runpod_bucket_count_controller.py', 'bucket', 78),
            ('attempt-002', 'NUMPY-', 'runpod_bucket_numpy_controller.py', 'bucket-numpy', 90)):
        frozen = read(AUDIT/(prefix+'SOURCE_FREEZE.json'))
        payload = AUDIT/(prefix+'payload.zip')
        assert sha(payload) == frozen['bundle_sha256']
        assert sha(ROOT/'scripts'/controller) == frozen['controller_sha256']
        assert sha(ROOT/'scripts/cm_runpod_packed_remote.py') == frozen['remote_sha256']
        assert sha(ROOT/'scripts/runpod_query_ladder_q64_second_host_v3_controller.py') == frozen['transport_sha256']
        with zipfile.ZipFile(payload) as archive:
            source = json.loads(archive.read('SOURCE_MANIFEST.json'))
            assert source['files'] == frozen['files']
            for name, expected in source['files'].items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == expected == sha(ROOT/name)
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
        output = evidence/folder
        fixtures, schedule = read(AUDIT/(prefix+'FIXTURES.json')), read(AUDIT/(prefix+'SCHEDULE.json'))
        outcomes = read(output/'OUTCOMES.json')
        assert [o['case'] for o in outcomes] == [c['id'] for c in fixtures]
        assert all(o['status'] == 'complete' for o in outcomes)
        rows, oracles = [], {}
        for case in fixtures:
            target = output/case['id']
            group = [json.loads(line) for line in (target/'RAW.jsonl').read_text().splitlines()]
            assert read(target/'COMPLETE.json')['cells'] == len(group)
            expected = read(target/'ORACLE.json')
            for q, value in expected.items(): oracles[case['id'], int(q)] = value
            for row in group:
                assert row['status'] in ('complete', 'refused')
                if row['status'] == 'refused':
                    assert row['reason'] and row['admission_ns'] > 0
                    continue
                assert row['exact'] and row['result'] == expected[str(row['q'])]
                assert len(json.loads(row['result'])) == row['q']
                assert row['total_ns'] == row['setup_ns']+row['query_ns']+row['cleanup_ns']
                assert row['warm_ns'] > 0
            rows += group
        assert [{k: r[k] for k in ('case', 'q', 'repeat', 'method')} for r in rows] == schedule
        memory = read(output/'MEMORY.json')
        assert len(memory) == memory_count
        for row in memory:
            assert row['after']['VmHWM'] >= row['after']['VmRSS'] > 0
            if row['status'] == 'complete': assert row['result'] == oracles[row['case'], 1]
            else: assert row['status'] == 'refused' and row['reason']
        result = read(output/'RESULT.json')
        complete = sum(r['status'] == 'complete' for r in rows)
        asserted = 2*sum(r['q'] for r in rows if r['status'] == 'complete')
        assert result['scheduled_cells'] == result['accounted_cells'] == len(rows)
        assert result['complete_cells'] == complete and result['refused_cells'] == len(rows)-complete
        assert result['asserted_outputs'] == asserted and result['exact']
        records.append(dict(attempt=attempt, cases=len(fixtures), cells=len(rows), complete_cells=complete,
                            refused_cells=len(rows)-complete, timed_outputs=asserted, memory_children=len(memory),
                            junit_tests=int(suite.attrib['tests']), source_files=len(source['files'])))
    prior_artifacts = 0
    for name, check in read(AUDIT/'PRIOR-AUDITS-VERIFIED.json').items():
        base = ROOT/'docs/audits'/name
        assert sha(base/'FINAL-MANIFEST.json') == check['manifest_sha256']
        manifest = read(base/'FINAL-MANIFEST.json')
        for field in ('artifacts', 'current_sources', 'owned_sources'):
            for rel, entry in manifest.get(field, {}).items():
                path = base/rel if field == 'artifacts' else ROOT/rel
                if not path.is_file(): path = ROOT/rel
                assert sha(path) == (entry if isinstance(entry, str) else entry['sha256'])
                prior_artifacts += field == 'artifacts'
    return dict(exact=True, attempts=records, total_cells=sum(r['cells'] for r in records),
                total_timed_outputs=sum(r['timed_outputs'] for r in records),
                total_memory_children=sum(r['memory_children'] for r in records),
                prior_artifacts_unchanged=prior_artifacts)


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
