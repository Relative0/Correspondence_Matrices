"""Reconcile retained local Windows results without rerunning test workloads."""
import json
import xml.etree.ElementTree as ET

from scripts.cm_local_historical_replay_20260912 import (
    AUDIT, EXPECTED, PACKAGES, SEALED, SNAPSHOTS, digest, snapshot_hashes, write,
)


def verify():
    assert digest(SEALED / 'FINAL-MANIFEST.json') == EXPECTED
    prior = json.loads((SEALED / 'HISTORICAL-STATUS.json').read_bytes())
    native = json.loads((AUDIT / 'native-001/RESULTS.json').read_bytes())
    reassessment = json.loads((AUDIT / 'reassessment-001/RESULT.json').read_bytes())
    rows = native['tests'] + [reassessment]
    assert len(rows) == len({r['test'] for r in rows}) == 10
    passed_statuses = {'passed', 'passed_previous_preparation'}
    pending = {r['nodeid'] for r in prior['rows'] if r['status'] not in passed_statuses}
    assert pending == {r['test'] for r in rows}
    evidence = {}
    for index, row in enumerate(rows):
        relative = f'native-001/test-{index:02d}.xml' if index < 9 else 'reassessment-001/test.xml'
        tree = ET.parse(AUDIT / relative)
        suites = list(tree.getroot().iter('testsuite'))
        cases = list(tree.getroot().iter('testcase'))
        assert len(suites) == len(cases) == 1
        assert suites[0].get('tests') == '1'
        assert all(suites[0].get(key) == '0' for key in ('errors', 'failures', 'skipped'))
        source, name = row['test'].split('::')
        assert cases[0].get('name') == name
        assert cases[0].get('classname') == source.removesuffix('.py').replace('/', '.')
        assert not any(cases[0].find(key) is not None for key in ('error', 'failure', 'skipped'))
        assert row['status'] == 'ok' and row['returncode'] == 0 and row['reason'] == 'completed'
        resources = row['resources']
        assert resources['cleanup_verified'] and resources['streams_closed']
        assert resources['active_processes'] == 0 and resources['attached_before_resume']
        assert resources['job_memory_limit_bytes'] == 2 << 30 and resources['process_limit'] == 32
        assert resources['peak_job_committed_bytes'] <= 2 << 30
        evidence[row['test']] = relative
    for name, filename, module in PACKAGES:
        before = json.loads((AUDIT / (name + '-snapshot-before.json')).read_bytes())
        after = json.loads((AUDIT / (name + '-snapshot-after.json')).read_bytes())
        assert before == after == snapshot_hashes(SNAPSHOTS / name)
    updated = []
    for row in prior['rows']:
        row = dict(row)
        if row['nodeid'] in evidence:
            row.update(status='passed', evidence=evidence[row['nodeid']],
                       runtime='Windows 10.0.19045 x64, Python 3.13.5, NumPy 2.3.2; local frozen snapshot replay',
                       phase='local_windows_execution')
        else:
            row['evidence_base'] = '../2026-09-12-cm-component-execution'
        updated.append(row)
    assert len(updated) == 21 and all(row['status'] in passed_statuses for row in updated)
    write(AUDIT / 'HISTORICAL-STATUS.json', dict(
        status='all_original_ids_have_passing_historical_snapshots', rows=updated,
        previous_passes=11, new_passes=10, cumulative_historical_ids_passed=21,
        original_issue_count=21, current_code_suite_rerun=False))
    summary = dict(tests_verified=10, junit_passes=10, failures=0, skipped=0,
                   cleanup_verified_for_all=True, snapshots_unchanged=True,
                   max_job_committed_bytes=max(r['resources']['peak_job_committed_bytes'] for r in rows),
                   elapsed_s=json.loads((AUDIT / 'CONTROLLER-RESULT.json').read_bytes())['elapsed_s'],
                   external_spending_usd=0, cumulative_historical_passes=21)
    write(AUDIT / 'VERIFICATION.json', summary)
    print(json.dumps(summary))


if __name__ == '__main__':
    verify()
