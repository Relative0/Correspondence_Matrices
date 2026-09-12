"""Current task-specific website results, bound to sealed research evidence.

Only selected numerical summaries are copied into the public site. Operational
receipts, cloud bundles and credentials are outside this publication surface.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

_next_spec = importlib.util.spec_from_file_location('cm_next_results_evidence', Path(__file__).with_name('cm_next_results_evidence.py'))
_next_module = importlib.util.module_from_spec(_next_spec)
_next_spec.loader.exec_module(_next_module)
append_next_results = _next_module.append_next_results

ROOT = Path(__file__).resolve().parents[2]
REVIEWED = '2026-09-12'
AUDITS = {
    'closures': ('2026-09-12-cm-count-closures', 'df889ae125afc114917460a32ede7e82f6145d7dfb559dacbc6b72f3258d5548'),
    'performance': ('2026-09-11-cm-performance', '7a4be6eee0e50523d2c68571b34d4627778b0366e325f97fdc0721f102490dc2'),
    'continuation': ('2026-09-11-cm-continuation', '5d50a22b3f24dc8542f35bc1e9d9103e83fcb597444ec9e4c1799d778ecdbebb'),
    'cloud': ('2026-09-11-cm-runpod-continuation', '8b3ecb37c6baccbd99610e566c334cae3edfdf7003938deaaeed551fb6f16e93'),
    'scalar': ('2026-09-11-cm-scalar-research', '3f2667a8c8dda1bcbafeef71662bba9c61ae6b6c8d96178801b2a724595c8a48'),
    'bucket': ('2026-09-11-cm-bucket-counts', 'ca698d98296905f81f8bf06f95e2997fd84925acf833ab9d9daef88bfd9a506f'),
    'next': ('2026-09-11-cm-next-research', 'aecf0d003d970ae72eb7b529479c2a60f29fffe713d672aee3b24ef2f167308b'),
    'frontiers': ('2026-09-12-cm-evidence-frontiers', '78e9e12d848aaf24c22696e7c56d261695206a8a98265a17f22e79b841c79442'),
    'applications': ('2026-09-12-cm-application-evidence', '1ded06d3d710203ed050c8f729edfb71653f09fe339234af2ee5352fc8ed47e7'),
}
LABELS = {
    'cse': 'Structural CSE', 'cse_flat': 'Structural CSE-flat', 'direct': 'Direct BitSet',
    'cm_public': 'Public packed CM', 'cm_flat': 'CM flat kernel', 'cm_words': 'CM word kernel',
    'dense': 'Dense CM', 'and_only': 'AND-only counter', 'factor_expr': 'Factorized expression',
    'factor_cm': 'Factorized CM', 'cudd_natural': 'CUDD natural order', 'cudd_dynamic': 'CUDD dynamic order',
    'cudd_grouped': 'CUDD grouped order', 'bucket_natural': 'Python natural order',
    'bucket_min_fill': 'Python min-fill', 'bucket_cm': 'Python through CM',
    'numpy_min_fill': 'Exact arrays, min-fill', 'numpy_cm': 'Exact arrays through CM',
    'rows_indexed': 'Current indexed Python', 'rows_legacy': 'Original Python (ablation)',
    'm4ri_indexed': 'Current indexed M4RI', 'm4ri_legacy': 'Original M4RI (ablation)',
    'bdd_cudd': 'CUDD fixed order', 'complete': 'Complete packed output', 'positional_full': 'Positional complete output',
    'independent_expr': 'Independent expression count', 'independent_cm': 'Independent CM count',
    'stream_8': '32-byte chunks', 'stream_12': '512-byte chunks', 'stream_16': '8 KiB chunks',
    'stream_18': '32 KiB chunks', 'named_lru': 'Named LRU cache', 'positional': 'Bounded positional cache',
    'uncached': 'No cache',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build_chart_freshness(site, data):
    """Inventory every shared figure, its data identity and measurement date.

    A new scalar/output contract does not overwrite an older bare-kernel or
    circuit experiment. Dates remain measurement dates, never relabelled reruns.
    """
    library = (site/'cm_master_shared.js').read_text(encoding='utf-8')
    figures = {}
    for name, body in re.findall(r'FIG\.(\w+) = \(\) => \{(.*?)(?=\nFIG\.|\nfunction pageFooter)', library, re.S):
        keys = sorted(set(re.findall(r'DATA\.(\w+)', body)))
        ids = re.findall(r'id: "([^"]+)"', body)
        for figure_id in ids:
            sources = []
            for key in keys:
                for item in data[key].get('provenance', []) if isinstance(data[key], dict) else []:
                    if isinstance(item, str):
                        path = ROOT/item.split(' :: ')[0]
                        if path.is_file():
                            # Git may check these older text sources out with CRLF
                            # on Windows and LF on Linux. Hash their text content
                            # consistently; sealed current downloads below still
                            # require exact, unmodified artifact bytes.
                            sources.append(dict(path=path.relative_to(ROOT).as_posix(),
                                sha256=digest(path.read_bytes().replace(b'\r\n', b'\n')),
                                hash_mode='text_lf_line_endings'))
            dates = [f'{y}-{m}-{d}' for src in sources for y, m, d in re.findall(r'(2026)[-_]?(\d{2})[-_]?(\d{2})', src['path'])]
            definition = name in ('assignmentGrowth', 'frontierMap', 'roadmap', 'auditLadder')
            if not sources and not definition: raise ValueError('Figure lacks a concrete evidence file: '+figure_id)
            figures[figure_id] = dict(figure=name, datasets=keys, sources=sources,
                data_sha256=digest(json.dumps(json.loads(json.dumps({key:data[key] for key in keys}, ensure_ascii=False)), sort_keys=True, ensure_ascii=False).encode()),
                measured=None if definition else max(dates), reviewed=REVIEWED,
                status='definition_or_authored_plan' if definition else 'latest_accepted_for_this_contract',
                note='Definition or authored research plan; not a benchmark.' if definition else
                     'Latest accepted measurement of this named study and its implementation at the measurement date. September 11 implementation changes and distinct scalar/file-output tasks are reported separately; this is not a timing claim for the updated code.')
    if len(figures) < 22: raise ValueError('Shared chart inventory is incomplete')
    return dict(reviewed=REVIEWED, figures=figures,
        controlling_successors={'affine_current': 'scalar/attempt-003/evidence/binding/SUMMARY.json',
            'file_process_memory': 'cloud/attempt-005/evidence/memory/SUMMARY.json',
            'bucket_current': 'bucket/ARRAY-ANALYSIS.json (attempt-002 only for current memory)',
            'native_batch': 'continuation/native-run/INDEPENDENT_VERIFICATION.json'})


def site_snapshots(data):
    """Export every chart's data, including the dated earlier study panels."""
    return {
        f'results/{REVIEWED}/full-site-data.json': (json.dumps(data, indent=2, ensure_ascii=False)+'\n').encode('utf-8'),
        f'results/{REVIEWED}/chart-freshness.json': (json.dumps(data['_freshness'], indent=2, ensure_ascii=False)+'\n').encode('utf-8'),
    }


def build_latest_results():
    sources, files, manifests = {}, {}, {}

    def source(key, audit, relative, role):
        name, expected = AUDITS[audit]
        base = ROOT/'docs/audits'/name
        if audit not in manifests:
            payload = (base/'FINAL-MANIFEST.json').read_bytes()
            if digest(payload) != expected: raise ValueError('Research seal changed: '+name)
            manifests[audit] = json.loads(payload)
        path = base/relative
        payload = path.read_bytes()
        entries = manifests[audit]['artifacts']
        entry = entries.get(relative, entries.get(path.relative_to(ROOT).as_posix()))
        if entry is None or digest(payload) != (entry if isinstance(entry, str) else entry['sha256']):
            raise ValueError('Unsealed or changed website source: '+str(path))
        href = f'results/{name[:10]}/{key}.json'
        sources[key] = dict(path=path.relative_to(ROOT).as_posix(), href=href,
                            sha256=digest(payload), bytes=len(payload), role=role,
                            audit_seal=expected, measured=name[:10])
        files[href] = payload
        return json.loads(payload)

    panels = []

    def panel(key, title, contract, scope, note, rows, default_case, default_q=1, metrics=None):
        if not rows: raise ValueError('Empty current result panel: '+key)
        ids = [(r['case'], r['q'], r['method']) for r in rows]
        if len(ids) != len(set(ids)): raise ValueError('Duplicate current result cell: '+key)
        if not any(r['case'] == default_case and r['q'] == default_q for r in rows):
            raise ValueError('Missing default result cell: '+key)
        panels.append(dict(id=key, title=title, contract=contract, scope=scope, note=note,
                           rows=rows, default_case=default_case, default_q=default_q,
                           metrics=metrics or ['cold_ms', 'warm_ms'], measured=sources[rows[0]['source']]['measured']))

    def row(r, source_key):
        item = dict(case=r['case'], q=r.get('q', 1), method=r['method'],
                    label=LABELS.get(r['method'], r['method']), status=r.get('status', 'complete'),
                    source=source_key, selector=f"case={r['case']}; q={r.get('q', 1)}; method={r['method']}")
        if item['status'] == 'refused': item['reason'] = r['reason']
        else:
            values = r.get('medians', r)
            item.update(cold_ms=values.get('median_total_ns', values.get('total_ns'))/1e6,
                        warm_ms=values.get('median_warm_ns', values.get('warm_ns'))/1e6)
            if 'plan_stats' in r: item['plan_stats'] = r['plan_stats']
        return item

    mask = source('packed-mask-confirmation', 'performance', 'confirmation_summary.json', 'fresh synthetic confirmation; old/current ablation')
    mask_rows = []
    for r in mask:
        # Restricted queries are a different query shape and remain explicit.
        case = r['case']+(' / restricted' if r['restricted'] else '')
        for version in ('baseline', 'candidate'):
            mask_rows.append(dict(case=case, q=r['q'], method=r['backend']+'_'+version,
                label=LABELS.get(r['backend'], r['backend'])+(' Â· original' if version == 'baseline' else ' Â· current'),
                status='complete', cold_ms=r['total_ns'][version]/1e6, warm_ms=r['warm_ns'][version]/1e6,
                source='packed-mask-confirmation', selector=f"case={r['case']}; q={r['q']}; restricted={r['restricted']}; backend={r['backend']}; {version}"))
    panel('packed-masks', 'Packed input construction', 'Complete Boolean output; fully charged resident requests',
          'Windows; fresh synthetic confirmation; all seven backend paths',
          'The shared packed-mask constructor benefits direct BitSet and CSE too. Original bars are an explicit ablation, not a current backend. Warm results and regressions remain available.',
          mask_rows, 'confirmation-n18-s0')

    cache = source('cache-confirmation', 'cloud', 'attempt-004/evidence/panels/confirmation-SUMMARY.json', 'latest Linux replay of consumed cache fixtures')
    panel('bounded-cache', 'Cache reuse and changing names', 'Repeated complete-output requests with bounded retained masks',
          'Linux EPYC 7702P; consumed portability panel; 2 MiB cache / 64 KiB pressure case',
          'Same-basis reuse, changing names, phases and pressure are separate cases. A gain on renamed inputs does not establish a default cache policy.',
          [row(r, 'cache-confirmation') for r in cache if '-cache-' in r['case']], 'confirmation-cache-n18-renamed', 32)

    io = source('file-and-independent-count', 'cloud', 'attempt-004/evidence/io/SUMMARY.json', 'latest full file-delivery and independent-count panel')
    panel('streaming', 'Complete output delivered to a file', 'Parse, prepare, deliver all bytes, flush/fsync, close and verify',
          'Linux EPYC 7702P; fresh synthetic n22/n24 outputs; q1/q8',
          'Every arm pays the same file-delivery obligations. Small chunks and warm batches can regress. No measured chunk size was installed as a default.',
          [row(r, 'file-and-independent-count') for r in io if '-stream-' in r['case']], 'cloud-stream-n24')
    panel('independent-count', 'Counts from independent components', 'Exact scalar count; no complete output requested',
          'Linux EPYC 7702P; fresh synthetic AND components and OR fallback control',
          'The entangled1 identifier is an OR root that this AND-only plan does not decompose. The separate factorized and bucket panels test broader mechanisms; do not mix their timings across hosts.',
          [row(r, 'file-and-independent-count') for r in io if '-count-' in r['case']], 'cloud-count-n24-entangled0')

    memory = source('file-memory-corrected', 'cloud', 'attempt-005/evidence/memory/SUMMARY.json', 'controlling fresh process VmHWM diagnostic')
    mem_rows = [dict(case=r['case'], q=1, method=r['method'], label=LABELS.get(r['method'], r['method']),
                     status='complete', peak_mib=r['median_after']['VmHWM_KiB']/1024,
                     source='file-memory-corrected', selector=f"case={r['case']}; method={r['method']}; median_after.VmHWM_KiB / 1024") for r in memory]
    panel('file-memory', 'Fresh-process peak memory', 'Process high-water mark including interpreter and libraries',
          'Separate Linux EPYC 7713 memory diagnostic; three fresh children per method',
          'This later /proc VmHWM diagnostic supersedes the equal inherited-rusage counters in the earlier file run. Its host differs from the timing panel; it is not a latency comparison.',
          mem_rows, 'file-n24', metrics=['peak_mib'])

    scalar = source('factorized-counts', 'scalar', 'attempt-001/evidence/scalar/SUMMARY.json', 'factorized count panel; earlier affine entries are not selected as current')
    panel('factorized-count', 'Factorized OR, XOR and mixed counts', 'Exact scalar counts through expression or CM ingress',
          'Linux EPYC 7713; development n12/n16 and confirmation n22/n24',
          'All three CUDD orders and the inseparable-cycle regression are retained. The cycle has a later bucket-mechanism comparison on its own host; this panel measures the factorized implementation.',
          [row(r, 'factorized-counts') for r in scalar if not r['case'].startswith('n_')], 'confirmation-or-n24')

    binding = source('affine-final-indexed', 'scalar', 'attempt-003/evidence/binding/SUMMARY.json', 'controlling final indexed affine implementation and matched M4RI control')
    source('affine-indexed-paired', 'scalar', 'BINDING-PAIRED-COMPARISONS.json', 'paired uncertainty for the final indexed affine ablation')
    panel('affine-count', 'Current affine counts and native control', 'Exact count after fixed assignments; packed-row ingress',
          'Linux EPYC 7713; eight public coding matrices and fresh n1024/n2048 controls',
          'The current indexed Python and indexed M4RI arms are compared on the same host. Original versions are labelled ablation controls. These final values supersede the earlier unindexed timings; no dense-FLINT ratio is presented as a general native win.',
          [row(r, 'affine-final-indexed') for r in binding], 'n_1800_k_0902_gap_28', 8)

    bucket = source('bucket-final-array-analysis', 'bucket', 'ARRAY-ANALYSIS.json', 'controlling same-host bucket/array/native timing and memory comparisons')
    bucket_fixtures = source('bucket-final-fixtures', 'bucket', 'NUMPY-FIXTURES.json', 'all declared full-CNF and synthetic input contracts')
    # Publish fixture identities/clauses already deliberately admitted to the
    # public research corpus; no application requests or credentials are present.
    panel('bucket-count', 'Overlapping CNF constraints: Python, arrays and CUDD', 'Exact counts over every declared CNF variable; not projected feature products',
          'Linux EPYC 9654; all 35 final-panel cases; q1/q8; nine paired repetitions',
          'Ten of eleven admitted full public CNFs fit the bucket limits. All resource refusals are shown without zero-height bars. Arrays help larger factors but lose on many narrow cases; both natural and dynamic CUDD remain strong controls. Public inputs in this follow-up are reused diagnostics.',
          [row(r, 'bucket-final-array-analysis') for r in bucket['timings']], 'model-09', 8)
    current_mem = [dict(case=r['case'], q=1, method=r['method'], label=LABELS.get(r['method'], r['method']),
                        status=r['status'], peak_mib=r['median_peak_bytes']/2**20,
                        reason='Plan exceeds frozen admission bounds' if r['status'] == 'refused' else None,
                        source='bucket-final-array-analysis', selector=f"memory: attempt=attempt-002; case={r['case']}; method={r['method']}; median_peak_bytes / 1048576")
                   for r in bucket['memory'] if r['attempt'] == 'attempt-002']
    panel('bucket-memory', 'Current bucket and native process memory', 'Fresh child process high-water mark; q1',
          'Linux EPYC 9654; three children per method and selected case',
          'These values include interpreter and import costs. Refused plans are labelled and are not ranked as successful low-memory counters. Reused-service and simultaneous-query memory need separate measurement.',
          current_mem, 'model-09', metrics=['peak_mib'])

    native = source('native-batch-final-gate', 'continuation', 'native-run/INDEPENDENT_VERIFICATION.json', 'controlling completed q8/q32/q96 native batch gate')
    if native['status'] != 'local_gate_failed_no_go': raise ValueError('Unexpected native batch disposition')
    native_rows = []
    for q, result in native['query_counts'].items():
        for method, field in (('native_scalar', 'scalar_sum_of_case_medians_ns'), ('native_batch', 'batch_sum_of_case_medians_ns')):
            native_rows.append(dict(case='prospective native batch workload', q=int(q), method=method,
                label='Scalar native' if method == 'native_scalar' else 'Batched native', status='complete',
                cold_ms=result[field]/1e6, source='native-batch-final-gate', selector=f'query_counts.{q}.{field} / 1000000'))
    panel('native-batch', 'Completed native batch gate', 'Sum of fully charged case medians, not one request latency',
          'Windows; independently frozen prospective workload; q8/q32/q96',
          'The q96 gain is below its frozen 1.10× materiality requirement. The candidate is a completed no-go for this workload; the earlier functional-only status is superseded. No learned router is promoted.',
          native_rows, 'prospective native batch workload', 96, metrics=['cold_ms'])

    verification = source('bucket-final-verification', 'bucket', 'LOCAL-EVIDENCE-VERIFICATION.json', 'both completed campaigns; complete schedules, outputs and previous-seal checks')
    numbers = {}

    def number(key, value, fmt, source_key, selector):
        numbers['latest.'+key] = dict(value=value, fmt=fmt, prov=sources[source_key]['path']+' :: '+selector)

    def one(rows, case, method, q):
        matches = [r for r in rows if (r['case'], r['method'], r['q']) == (case, method, q)]
        if len(matches) != 1: raise ValueError('Missing or duplicate headline selector')
        return matches[0]

    for label, method in (('bucket.before_ms', 'bucket_min_fill'), ('bucket.current_ms', 'numpy_min_fill')):
        result = one(bucket['timings'], 'model-09', method, 8)
        number(label, result['medians']['total_ns']/1e6, 'num1s', 'bucket-final-array-analysis', f'timings[model-09,q8,{method}].medians.total_ns / 1000000')
    for label, method in (('affine.before_ms', 'rows_legacy'), ('affine.current_ms', 'rows_indexed')):
        result = one(binding, 'n_1800_k_0902_gap_28', method, 8)
        number(label, result['median_total_ns']/1e6, 'num1s', 'affine-final-indexed', f'[n_1800_k_0902_gap_28,q8,{method}].median_total_ns / 1000000')
    number('batch.speedup', native['query_counts']['96']['fully_charged_sum_speedup'], 'x3', 'native-batch-final-gate', 'query_counts.96.fully_charged_sum_speedup')
    number('bucket.outputs', verification['total_timed_outputs'], 'int', 'bucket-final-verification', 'total_timed_outputs')
    number('bucket.cells', verification['total_cells'], 'int', 'bucket-final-verification', 'total_cells')
    disposition = append_next_results(source, panel, number)
    source('frontier-research-summary', 'frontiers', 'PUBLIC-RESULTS.json',
           'prior frontier study; superseded where the application study repeats the same contract')
    applications = source('application-research-summary', 'applications', 'PUBLIC-RESULTS.json',
                       'earlier September 11 five-method timings, mappings and actual video evidence')
    sources['application-research-summary']['measured'] = applications['measured_utc']
    frontiers = source('count-closures-summary', 'closures', 'PUBLIC-RESULTS.json',
                       'current exact counts, component benchmarks, restored fixtures and corrected EPFL origin')
    sources['count-closures-summary']['measured'] = frontiers['latest_research_utc']
    if frontiers['status'] != 'verified_with_explicit_limitations':
        raise ValueError('Frontier research has not been verified')
    number('next.final_passed_tests', frontiers['regression']['counts']['passed'], 'int',
           'count-closures-summary', 'regression.counts.passed')
    number('next.final_failed_or_error_tests', frontiers['fixtures']['remaining_failure_ids'], 'int',
           'count-closures-summary', 'fixtures.remaining_failure_ids')
    number('next.new_regressions', len(frontiers['regression']['new_failure_ids']), 'int',
           'count-closures-summary', 'regression.new_failure_ids.length')
    method_labels = {'bucket_min_fill': 'Python min-fill', 'array_min_fill': 'Exact arrays, min-fill',
                     'cudd_natural': 'CUDD natural order', 'cudd_dynamic': 'CUDD dynamic order',
                     'simplified_bucket': 'Condition + simplify + Python bucket'}
    for kind, title, default in (
            ('feature', 'Counts of concrete feature selections', 'additional-02'),
            ('independent', 'Independent application projected counts', 'independent-01')):
        rows = []
        for record in applications[kind+'_methods']:
            result = dict(case=record['case'], q=8, method=record['method'],
                          label=method_labels[record['method']], status=record['status'],
                          source='application-research-summary',
                          selector=f"{kind}_methods[case={record['case']};method={record['method']}] (median of three repetitions)")
            if record['status'] == 'complete':
                if not record['independently_cross_checked']:
                    raise ValueError('Unverified application timing')
                result.update(cold_ms=record['median_total_ms'])
            else:
                result['reason'] = record['reason']
            rows.append(result)
        panel('application-'+kind, 'Earlier five-method study: '+title, 'Exact projected count; eight generated application-derived contexts',
              'Linux RunPod; three fresh-process repetitions; 15-second worker limit; 2 GiB address-space limit',
              applications[kind+'_note']+' Each plotted output matches independent nonprobabilistic Ganak counts. '
              'Only complete three-repetition results are plotted. Setup, cold requests and cleanup are charged; '
              'the simplifier recompiles every request. Different hosts and earlier deadlines are not paired speedup comparisons.',
              rows, default, 8, metrics=['cold_ms'])
        panels[-1]['measured'] = applications['measured_utc']
        if kind == 'feature':
            panels[-1]['case_labels'] = {r['id']:r['name'] for r in applications['models']}
    for kind, title, default in (
            ('feature', 'Component counting: concrete feature selections', 'additional-02'),
            ('independent', 'Component counting: independent applications', 'independent-01')):
        rows = []
        for record in frontiers['component_study'][kind]['methods']:
            result = dict(case=record['case'], q=8, method=record['method'],
                          label='Component counting' if record['method'] == 'component_count' else method_labels[record['method']],
                          status=record['status'], source='count-closures-summary',
                          selector=f"component_study.{kind}.methods[case={record['case']};method={record['method']}] (median of three repetitions)")
            if record['status'] == 'complete':
                if not record['independently_cross_checked']:
                    raise ValueError('Unverified component timing')
                result['cold_ms'] = record['median_total_ms']
            else:
                result['reason'] = record['reason']
            rows.append(result)
        panel('component-'+kind, title, 'Exact projected count; eight application-derived contexts',
              'Linux RunPod; three fresh-process repetitions; 15-second worker limit; 2 GiB address-space limit',
              frontiers['component_study']['note']+' Only complete three-repetition results are plotted. '
              'These three methods share a host and schedule; earlier five-method timings remain separately dated.',
              rows, default, 8, metrics=['cold_ms'])
        if kind == 'feature':
            panels[-1]['case_labels'] = {r['id']:r['name'] for r in frontiers['models']}
    disposition = frontiers['disposition']
    evidence = dict(schema='cm-current-website-results/v1', reviewed=REVIEWED, panels=panels,
                    frontiers=frontiers,
                    continuation_disposition=disposition,
                    sources=sources, audit_seals={k:v[1] for k,v in AUDITS.items()},
                    public_cnf_ids=[c['id'] for c in bucket_fixtures if c['cohort'] == 'public full CNF'],
                    final_bucket_junit_records=verification['attempts'][-1]['junit_tests'],
                    scope='Separate tasks, hosts and timing windows; current defaults are not selected from observed winners.')
    snapshot = 'results/2026-09-11/current-results.json'
    files[snapshot] = (json.dumps(evidence, indent=2, ensure_ascii=False)+'\n').encode('utf-8')
    return evidence, numbers, files
