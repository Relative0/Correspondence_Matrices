"""Export selected sealed scientific results; never publish operational receipts."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs/audits/2026-09-12-cm-final-public-evidence'
SEALS = {
    'execution': ('2026-09-12-cm-component-execution', '30d309367d64cb08fb10ab0cdd77f018fa513ba727116b5c96ed929c5814c015'),
    'windows': ('2026-09-12-cm-local-windows-replay', 'b296e0c1d8ab1efda45538e07df88ae66e895e3174af303272bc1b5d70bf8b8a'),
}


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def export(workspace):
    AUDIT.mkdir(parents=True, exist_ok=False)
    inputs = {}

    def source(audit, filename):
        name, seal = SEALS[audit]
        base = workspace / 'docs/audits' / name
        manifest = (base / 'FINAL-MANIFEST.json').read_bytes()
        if sha(manifest) != seal:
            raise ValueError('input audit seal changed')
        row = next(r for r in json.loads(manifest)['artifacts'] if r['path'] == filename)
        payload = (base / filename).read_bytes()
        if sha(payload) != row['sha256'] or len(payload) != row['bytes']:
            raise ValueError('input identity changed: ' + filename)
        relative = 'inputs/' + audit + '-' + filename
        path = AUDIT / relative
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(payload)
        inputs[relative] = dict(original_path='docs/audits/' + name + '/' + filename,
                                original_audit_seal=seal, **row)
        return json.loads(payload)

    analysis = source('execution', 'COMPONENT-ANALYSIS.json')
    interpretation = source('execution', 'COMPONENT-INTERPRETATION.json')
    closure = source('execution', 'INDEPENDENT-COUNT-CLOSURE.json')
    history = source('windows', 'HISTORICAL-STATUS.json')
    local = source('windows', 'VERIFICATION.json')
    assert analysis['cells'] == 180 and analysis['all_completed_outputs_match_bound_reference']
    outputs = sum(r['completed_cold_queries'] + r['completed_warm_queries'] for r in analysis['arms'].values())
    assert outputs == 1344 and len(interpretation['case_table']) == 7
    assert closure['now_independently_agreed_contexts'] == 120
    assert not closure['proof_certificate_produced']
    assert history['cumulative_historical_ids_passed'] == len(history['rows']) == 21
    assert local['tests_verified'] == local['junit_passes'] == 10 and local['cleanup_verified_for_all']
    assert all(r['status'] in ('passed', 'passed_previous_preparation') for r in history['rows'])
    public = dict(schema='cm-final-public-evidence/v1', reviewed='2026-09-12',
        status='verified_with_explicit_limitations',
        disposition='All 120 fixed admitted contexts now have agreement between independently implemented counters, and all 21 original historical test IDs have passing restored snapshots. The single-pass component candidate reduces counting lifecycle time on seven completed development cases, but coverage remains 7/15. Production defaults remain unchanged.',
        independent_count=closure,
        component=dict(cells=analysis['cells'], outputs_checked=outputs, repeats=3, arms=analysis['arms'],
            case_table=interpretation['case_table'],
            lifecycle_reduction_range_percent=interpretation['call_lifecycle_reduction_range_percent'],
            clock_overhead_percent=interpretation['clock_instrumentation_all_cells_parent_overhead_percent'],
            note='Single-host exposed development study: 15 cases, four arms, three repeats. The candidate combines clause satisfaction and residual construction in one scan. Exact projected semantics, fresh per-query caches and conservative work accounting are preserved. Seven cases complete in every arm; two still hit node caps and six hit work caps. No prospective validation or production promotion.',
            timing_note='Lifecycle includes setup, cold calls and cleanup; parent wall time also includes process/input startup, journal IO and warm replay. Reductions are medians of paired ratios, not ratios of the displayed medians. End-to-end gains are below 0.1% on the two smallest cases. Peak RSS does not improve uniformly. Refused cases have no speed ratio.'),
        historical=dict(passed=21, total=21, new_local_passes=10, previous_passes=11,
            local_elapsed_s=local['elapsed_s'], cleanup_verified=True,
            local_runtime='Windows 10.0.19045 x64; Python 3.13.5; NumPy 2.3.2',
            rows=[dict(test=r['nodeid'], status=r['status'], phase=r['phase'],
                       runtime=r.get('runtime', 'Previously retained historical preparation pass')) for r in history['rows']],
            note='These are passing restored historical snapshots, not a rerun or reclassification of the broad current-code suite. Three earlier passes used Linux Python 3.13.15 for source compatibility, not the original Python 3.13.5 runtime. All ten new local checks passed with unchanged 60-second, 2 GiB Job Object and 32-process limits; interpreter identity and descendant cleanup were verified.'),
        remaining=dict(required_execution=[], natural_consumer_sessions=0,
            recommendation='No further count retries or historical replays are required. Stop repeated measurements on these exposed cases.',
            conditional=[
                'Capture backend use only when an independently needed consumer job exists; presentation-only video builds do not establish backend demand.',
                'If broader performance claims are needed, freeze fresh independent workloads before collecting prospective validation evidence.',
                'If a real workload needs one of the eight refused cases, use retained phase/work counters to choose one bounded algorithm change, then freeze a new paired protocol.',
                'Unsupported original feature mappings remain explicit refusals; revisit them only when that application contract is needed.'
            ],
            production_default_changed=False, agreement_is_proof_certificate=False),
        input_provenance=inputs)
    (AUDIT / 'PUBLIC-RESULTS.json').write_text(json.dumps(public, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    manifest = dict(artifacts={p.relative_to(AUDIT).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
                              for p in sorted(AUDIT.rglob('*')) if p.is_file()},
                    input_seals={key: value[1] for key, value in SEALS.items()},
                    exporter_sha256=sha(Path(__file__).read_bytes()),
                    scope='Selected scientific evidence and authored remaining-work assessment; operational receipts excluded.')
    payload = (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode()
    (AUDIT / 'FINAL-MANIFEST.json').write_bytes(payload)
    print(json.dumps(dict(public_audit=str(AUDIT), seal=sha(payload), outputs_checked=outputs)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    export(parser.parse_args().workspace.resolve())
