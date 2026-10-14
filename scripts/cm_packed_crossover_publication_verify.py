"""Bind published crossover summaries to all curated rows and frozen downloads."""
import hashlib
import json
from pathlib import Path
from statistics import median
import zipfile

RELATIVE='results/2026-10-14/packed-crossover'


def verify(site):
    site=Path(site); folder=site/RELATIVE
    load=lambda name:json.loads((folder/name).read_text(encoding='utf-8'))
    summary=load('summary.json');cases={c['id']:c for c in load('cases.json')['cases']};schedule=load('schedule.json')['cells']
    rows=[json.loads(line) for line in (folder/'trials.jsonl').read_text().splitlines()]
    if summary['schema']!='cm-packed-crossover/v1' or len(rows)!=112 or summary['matching_pairs']!=56:raise ValueError('crossover identity/count')
    if [r['cell'] for r in rows]!=schedule or not all(r['valid'] and r['status']=='ok' and r['returncode']==0 for r in rows):raise ValueError('crossover invalid schedule/row')
    if summary['post_exit_gate_passed'] or summary['native_route']['available'] or 'deletion cause unknown' not in summary['runtime_limitation']:raise ValueError('crossover claim boundary')
    pairs={}
    for row in rows:
        if set(row)!={'cell','status','returncode','wall_ns','valid','result','resource_summary'}:raise ValueError('unexpected operational data')
        c=row['cell'];pairs.setdefault((c['case'],c['lifecycle'],c['pair']),{})[c['arm']]=row
        r=row['resource_summary']
        if not r['cleanup_verified'] or not r['cgroup_removed'] or r['memory_events']['max'] or r['pids_events']['max']:raise ValueError('crossover resource failure')
        case=cases[c['case']]
        if case['q']==64 and (case['unique_restricted_functions']!=64 or len(set(row['result']['context_hashes']))!=64):raise ValueError('redundant restriction contexts')
    if len(pairs)!=56 or any(len(p)!=2 or len({r['result']['delivered_sha256'] for r in p.values()})!=1 for p in pairs.values()):raise ValueError('paired artifact mismatch')
    for result in summary['analyses']:
        a,b=result['denominator'],result['numerator']; expected=[]
        for key,pair in pairs.items():
            if key[:2]==(result['case'],result['lifecycle']):expected.append({'pair':key[2],'ratio_b_over_a':pair[b]['wall_ns']/pair[a]['wall_ns']})
        ratios=[p['ratio_b_over_a'] for p in expected]
        if expected!=result['paired_ratios'] or median(ratios)!=result['paired_median_ratio'] or sum(r<1 for r in ratios)!=result['candidate_wins']:raise ValueError('stale paired medians')
    for phase in load('phase-medians.json')['phase_medians']:
        for lifecycle in ('cold','prepared'):
            selected=[r for r in rows if (r['cell']['case'],r['cell']['arm'],r['cell']['lifecycle'])==(phase['case'],phase['arm'],lifecycle)]
            if median(r['wall_ns'] for r in selected)/1e6!=phase[lifecycle+'_full_median_ms']:raise ValueError('stale lifecycle median')
        for key,value in phase['prepared_phase_medians_ms'].items():
            if median(r['result']['phases_ns'].get(key,0) for r in selected)/1e6!=value:raise ValueError('stale phase median')
    with zipfile.ZipFile(folder/'frozen-source-and-controls.zip') as archive:
        hashes=load('source-sha256.json')['files']
        if set(archive.namelist())!=set(hashes):raise ValueError('source archive membership')
        if any(hashlib.sha256(archive.read(name)).hexdigest()!=digest for name,digest in hashes.items()):raise ValueError('frozen source drift')
    files={}
    for name,record in load('checksums.json')['files'].items():
        if Path(name).name!=name:raise ValueError('escaping download')
        data=(folder/name).read_bytes()
        if len(data)!=record['bytes'] or hashlib.sha256(data).hexdigest()!=record['sha256']:raise ValueError('stale crossover download: '+name)
        files[RELATIVE+'/'+name]=record
    for page in ('index.html','latest-results.html','data-downloads.html'):
        text=(site/page).read_text(encoding='utf-8')
        if RELATIVE+'/index.html' not in text or 'post-exit preservation gate failed' not in text:raise ValueError('crossover navigation/qualification missing')
    runtime=load('runtime-sha256.json')
    if len(runtime['files'])!=2056 or not runtime['in_service_preserved'] or runtime['post_exit_preserved']:raise ValueError('runtime preservation boundary')
    return {'status':'verified','trial_records':112,'matching_pairs':56,'post_exit_gate_passed':False,'files':files}


if __name__=='__main__':
    result=verify(Path(__file__).resolve().parents[1]/'deliverables_n22_24/master_explainer_2026_08_03')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))
