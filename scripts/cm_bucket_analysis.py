"""Paired array ablations and process-memory summaries from sealed raw rows."""
import json
from pathlib import Path
import statistics

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT/'docs/audits/2026-09-11-cm-bucket-counts'


def analyze():
    output = AUDIT/'attempt-002/evidence/bucket-numpy'
    cases = json.loads((AUDIT/'NUMPY-FIXTURES.json').read_text())
    paired, timings = [], []
    for case in cases:
        rows = [json.loads(l) for l in (output/case['id']/'RAW.jsonl').read_text().splitlines()]
        for q in (1, 8):
            grouped = {m: sorted((r for r in rows if r['q'] == q and r['method'] == m), key=lambda r: r['repeat'])
                       for m in sorted({r['method'] for r in rows})}
            for method, group in grouped.items():
                if any(r['status'] != 'complete' for r in group):
                    timings.append(dict(case=case['id'], q=q, method=method, status='refused', reason=group[0]['reason']))
                    continue
                timings.append(dict(case=case['id'], q=q, method=method, status='complete',
                    medians={k: statistics.median(r[k] for r in group) for k in ('total_ns', 'setup_ns', 'query_ns', 'cleanup_ns', 'warm_ns')},
                    maximum_total_ns=max(r['total_ns'] for r in group), maximum_warm_ns=max(r['warm_ns'] for r in group),
                    plan_stats=group[0]['plan_stats']))
            for before, after in (('bucket_min_fill', 'numpy_min_fill'), ('bucket_cm', 'numpy_cm'),
                                  ('cudd_natural', 'numpy_min_fill'), ('cudd_natural', 'numpy_cm')):
                a, b = grouped[before], grouped[after]
                if any(r['status'] != 'complete' for r in a+b):
                    paired.append(dict(case=case['id'], q=q, before=before, after=after, status='refused'))
                    continue
                assert [r['repeat'] for r in a] == [r['repeat'] for r in b] == list(range(9))
                for metric in ('total_ns', 'warm_ns'):
                    logs = np.log(np.array([x[metric]/y[metric] for x, y in zip(a, b)]))
                    rng = np.random.default_rng(2026091162)
                    draws = np.sort(np.exp(logs[rng.integers(0, 9, size=(1000, 9))].mean(axis=1)))
                    paired.append(dict(case=case['id'], q=q, before=before, after=after, metric=metric, status='complete',
                        paired_speedup=float(np.exp(logs.mean())), ci95=[float(draws[24]), float(draws[974])]))
    memory = []
    for attempt, folder in (('attempt-001', 'bucket'), ('attempt-002', 'bucket-numpy')):
        rows = json.loads((AUDIT/attempt/'evidence'/folder/'MEMORY.json').read_text())
        for case, method in sorted({(r['case'], r['method']) for r in rows}):
            group = [r for r in rows if r['case'] == case and r['method'] == method]
            memory.append(dict(attempt=attempt, case=case, method=method, status=group[0]['status'],
                median_lifecycle_ns=statistics.median(r['lifecycle_ns'] for r in group),
                median_peak_bytes=1024*statistics.median(r['after']['VmHWM'] for r in group),
                median_rss_after_bytes=1024*statistics.median(r['after']['VmRSS'] for r in group)))
    return dict(paired=paired, timings=timings, memory=memory,
                inference='Within-host paired bootstrap only; reused public inputs are diagnostic. Nine repetitions do not estimate service tail latency.')


if __name__ == '__main__':
    print(json.dumps(analyze(), indent=2))
