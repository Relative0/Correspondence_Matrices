"""Verify sealed count-closure evidence and reaggregate its admitted graph values."""
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'docs/audits/2026-09-12-cm-count-closures'
PRIOR=ROOT/'docs/audits/2026-09-12-cm-application-evidence'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))

def verify(root=ROOT):
    audit=root/'docs/audits/2026-09-12-cm-count-closures'
    expected=(audit/'FINAL-MANIFEST.sha256').read_text().split()[0]
    if sha(audit/'FINAL-MANIFEST.json')!=expected:raise ValueError('seal mismatch')
    manifest=read(audit/'FINAL-MANIFEST.json')
    found={p.relative_to(audit).as_posix() for p in audit.rglob('*') if p.is_file()}
    if found!=set(manifest['artifacts'])|{'FINAL-MANIFEST.json','FINAL-MANIFEST.sha256'}:raise ValueError('artifact membership mismatch')
    for name,item in manifest['artifacts'].items():
        path=(audit/name).resolve()
        if not path.is_relative_to(audit.resolve()):raise ValueError('artifact escapes audit')
        if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise ValueError('artifact identity mismatch: '+name)
    for name,digest in manifest['current_sources'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()) or sha(path)!=digest:raise ValueError('source identity mismatch: '+name)
    for name,digest in manifest['prior_seals'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()) or sha(path)!=digest:raise ValueError('prior seal mismatch')
    public=read(audit/'PUBLIC-RESULTS.json')
    if public['regression']['new_failure_ids'] or public['consumer']['natural_sessions_admitted']:
        raise ValueError('unsupported regression or consumer admission')
    entries=public['closure_oracle']['entries']
    table={(r['case'],r['context_index']):r for r in entries}
    cohorts={'feature':read(root/'docs/audits/2026-09-12-cm-application-evidence/FEATURE-CASES.json'),
             'independent':read(root/'docs/audits/2026-09-12-cm-evidence-frontiers/INDEPENDENT-CASES.json')}
    contexts={(c['id'],i):(kind,context) for kind,cases in cohorts.items() for c in cases for i,context in enumerate(c['contexts'])}
    if set(table)!=set(contexts):raise ValueError('fixed context coverage mismatch')
    for key,(kind,context) in contexts.items():
        if table[key]['kind']!=kind or table[key]['context']!=context:raise ValueError('changed conditioning contract')
    if len(entries)!=len(table):raise ValueError('oracle entry duplication')
    if len(entries)!=120 or any(not r['counters'] or r['independently_cross_checked']!=(len(r['counters'])>=2) for r in entries):
        raise ValueError('oracle coverage mismatch')
    for kind in cohorts:
        rows=[r for r in entries if r['kind']==kind]
        if public['closure_oracle'][kind+'_completed']!=len(rows) or public['closure_oracle'][kind+'_cross_checked']!=sum(r['independently_cross_checked'] for r in rows):
            raise ValueError('count coverage headline mismatch')
    for row in public['closure_oracle']['attempts']:
        if row['status']=='complete' and row['value']!=table[(row['case'],row['context_index'])]['exact_value']:
            raise ValueError('counter disagreement')
    raw=read(audit/'attempt-004/evidence/component-study/RESULTS.json')
    expected={(c['id'],method,repeat) for cases in cohorts.values() for c in cases for method in ('component_count','array_min_fill','cudd_dynamic') for repeat in range(3)}
    if len(raw)!=len(expected) or {(r['case'],r['method'],r['repeat']) for r in raw}!=expected:
        raise ValueError('benchmark schedule coverage mismatch')
    checked=0
    for cell in raw:
        if cell['status']=='complete':
            if len(cell['values'])!=8:raise ValueError('query count mismatch')
            for index,value in enumerate(cell['values']):
                if str(value)!=table[(cell['case'],index)]['exact_value']:raise ValueError('timed output mismatch')
                checked+=1
    for kind in ('feature','independent'):
        for row in public['component_study'][kind]['methods']:
            group=[r for r in raw if r['case']==row['case'] and r['method']==row['method']]
            if len(group)!=3:raise ValueError('repetition coverage mismatch')
            if row['status']=='complete':
                if not row['independently_cross_checked'] or any(r['status']!='complete' for r in group):raise ValueError('unverified graph row')
                if row['median_total_ms']!=median(r['total_ns'] for r in group)/1e6:raise ValueError('median mismatch')
            elif 'median_total_ms' in row:raise ValueError('incomplete graph row has a time')
    if checked!=public['component_study']['timed_outputs_checked']:raise ValueError('timed-output count mismatch')
    origin=public['epfl_origin'];upstream=audit/'upstream/EPFL-0060e156826e733d69bf5b3322d1bdd0d03a1f9a.blif'
    data=upstream.read_bytes()
    if hashlib.sha256(data).hexdigest()!=origin['retained_sha256']:raise ValueError('EPFL byte identity mismatch')
    git_blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    if git_blob!=origin['rows'][0]['git_blob']:raise ValueError('EPFL Git identity mismatch')
    if not all(r['cleanup_verified'] for r in read(audit/'VERIFICATION.json')['attempts']):raise ValueError('cleanup incomplete')
    return dict(status='pass',artifacts=len(manifest['artifacts']),sources=len(manifest['current_sources']),
                oracle_contexts=120,timed_outputs=checked,science_sha256=expected,solvers_rerun=False)

if __name__=='__main__':print(json.dumps(verify(),indent=2))
