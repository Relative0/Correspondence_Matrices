"""Independent saved-structure replay and complete ledger verification."""
import argparse
from collections import Counter, defaultdict
import functools
import hashlib
import json
import math
import operator
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.cm_fair_feature_model_benchmark import columns, scalar, sha, write


def replay(bundle):
    assert set(bundle)=={'schema','arm','k','variable_universe','structure'}
    assert bundle['schema']=='cm-fair-fm-structure/v1'
    k=bundle['k']
    assert type(k) is int and 8<=k<=16
    assert bundle['variable_universe']==[f'x{i}' for i in range(k)]
    full,pats=columns(k)
    data=bundle['structure']
    arm=bundle['arm']
    if arm=='cnf':
        assert set(data)=={'clauses'}
        # Separate scalar verifier, rather than calling the producer's CNF loop.
        return scalar({'k':k,'clauses':data['clauses']})
    if arm in ('cm','cse'):
        assert set(data)=={'n_slots','root_slot','loads','ops'}
        values={}
        for slot,kind,value in data['loads']:
            assert slot not in values and kind in ('const','var')
            if kind=='const':
                assert type(value) is int and value in (0,1)
                values[slot]=full if value else 0
            else:
                assert value in bundle['variable_universe']
                values[slot]=pats[int(value[1:])]
        for slot,opcode,args in data['ops']:
            assert slot not in values and args and all(a in values for a in args)
            a=[values[i] for i in args]
            if opcode==0:
                assert len(a)==1
                value=full^a[0]
            elif opcode==1: value=functools.reduce(operator.and_,a)
            elif opcode==2: value=functools.reduce(operator.or_,a)
            elif opcode==3: value=functools.reduce(operator.xor,a)
            elif opcode==4:
                assert len(a)==2
                value=(full^a[0])|a[1]
            elif opcode==5:
                assert len(a)==2
                value=full^(a[0]^a[1])
            else: raise AssertionError('unknown opcode')
            values[slot]=value
        assert set(values)==set(range(data['n_slots']))
        return values[data['root_slot']]
    assert arm in ('cudd_fixed','cudd_sift')
    assert set(data)=={'nodes','root','order'}
    assert sorted(data['order'])==sorted(bundle['variable_universe'])
    if arm=='cudd_fixed': assert data['order']==bundle['variable_universe']
    levels={v:i for i,v in enumerate(data['order'])}
    values={-1:0,-2:full}
    for index,(name,low,high) in enumerate(data['nodes']):
        assert name in levels and low in values and high in values
        for child in (low,high):
            if child>=0: assert levels[data['nodes'][child][0]]>levels[name]
        pat=pats[int(name[1:])]
        values[index]=(values[low]&(full^pat))|(values[high]&pat)
    return values[data['root']]


def verify(output, protocol_path, destination):
    protocol=json.loads(protocol_path.read_bytes())
    rows=[json.loads(s) for s in (output/'ledger.jsonl').read_bytes().splitlines()]
    assert len(rows)==len(protocol['schedule'])
    cases={c['id']:c for c in protocol['cases']}
    oracles=json.loads((output/'oracles.json').read_bytes())
    assert set(oracles)==set(cases)
    # Recompute each scalar oracle locally without importing any measured backend.
    for cid,case in cases.items():
        assert sha(scalar(case).to_bytes((1<<case['k'])//8,'little'))==oracles[cid]
    timings=defaultdict(lambda:defaultdict(list))
    cache={}
    verified=0
    file_manifest=[]
    for index,(row,planned) in enumerate(zip(rows,protocol['schedule'])):
        assert row['index']==index and all(row[k]==v for k,v in planned.items())
        folder=output/'cells'/f'{index:04d}'
        case=cases[row['case_id']]
        assert json.loads((folder/'case.json').read_bytes())==case
        if row['status']!='ok': continue
        assert len(row['processes'])==2
        raw=(folder/'artifact.json').read_bytes()
        artifact=json.loads(raw)
        assert artifact['arm']==row['arm'] and artifact['k']==case['k']
        digest=sha(raw)
        if digest not in cache:
            cache[digest]=sha(replay(artifact).to_bytes((1<<case['k'])//8,'little'))
        assert cache[digest]==oracles[row['case_id']]
        parts=[]
        for mode,process in zip(('build','reload'),row['processes']):
            result=json.loads((folder/(mode+'.json')).read_bytes())
            assert not (folder/(mode+'.log')).read_bytes(), 'nonempty worker diagnostic log'
            assert process['mode']==mode and process['exit_code']==0 and not process['timed_out']
            assert result['pid']==process['pid'] and result['mode']==mode
            assert result['case_id']==row['case_id'] and result['arm']==row['arm']
            assert result['result_sha256']==oracles[row['case_id']]
            assert result['artifact_sha256']==digest and result['artifact_bytes']==len(raw)
            assert result['cold_total_ns']==sum(result[f] for f in
                ('parse_ns','artifact_read_ns','construct_ns','first_query_ns'))
            assert len(result['warm_ns'])==5 and all(type(v) is int and v>=0 for v in result['warm_ns'])
            assert 0<result['rss_baseline_kib']<=result['rss_highwater_kib']
            if row['arm'].startswith('cudd'): assert result['configuration']['reordering'] is False
            for field in ('cold_total_ns','construct_ns','first_query_ns','rss_highwater_kib'):
                timings[(row['case_id'],row['arm'])][mode+'_'+field].append(result[field])
            timings[(row['case_id'],row['arm'])][mode+'_warm_median_ns'].append(statistics.median(result['warm_ns']))
            timings[(row['case_id'],row['arm'])][mode+'_parent_wall_ns'].append(process['parent_wall_ns'])
            parts.append(result)
        assert parts[0]['pid']!=parts[1]['pid']
        timings[(row['case_id'],row['arm'])]['save_reload_lifecycle_ns'].append(
            parts[0]['cold_total_ns']+parts[0]['serialize_ns']+parts[1]['cold_total_ns']+
            parts[0]['cleanup_ns']+parts[1]['cleanup_ns'])
        timings[(row['case_id'],row['arm'])]['artifact_bytes'].append(len(raw))
        verified+=1
    medians=[dict(case_id=c,arm=a,**{f:statistics.median(v) for f,v in fields.items()},
        completed_blocks=len(fields['build_cold_total_ns'])) for (c,a),fields in sorted(timings.items())]
    lookup={(r['case_id'],r['arm']):r for r in medians if r['completed_blocks']==5}
    comparisons=[]
    for arm in ('cse','cnf','cudd_fixed','cudd_sift'):
        for field in ('build_cold_total_ns','build_warm_median_ns','reload_cold_total_ns','save_reload_lifecycle_ns',
                      'build_parent_wall_ns','reload_parent_wall_ns'):
            histories=defaultdict(list)
            for case in protocol['cases']:
                cm,other=lookup.get((case['id'],'cm')),lookup.get((case['id'],arm))
                if cm and other:
                    histories[case['history']].append(other[field]/cm[field])
            gm=lambda xs:math.exp(statistics.fmean(math.log(x) for x in xs))
            if histories: comparisons.append(dict(baseline=arm,metric=field,
                baseline_over_cm_equal_history_geomean=gm([gm(v) for v in histories.values()]),
                histories=len(histories),cases=sum(map(len,histories.values()))))
    for path in sorted(output.rglob('*')):
        if path.is_file(): file_manifest.append(dict(path=path.relative_to(output).as_posix(),
            bytes=path.stat().st_size,sha256=sha(path.read_bytes())))
    write(destination,dict(schema='cm-fair-fm-verification/v1',protocol_sha256=sha(protocol_path.read_bytes()),
        scheduled=len(rows),verified_cells=verified,independently_replayed_unique_structures=len(cache),
        status_counts=dict(Counter(r['status'] for r in rows)),medians=medians,comparisons=comparisons,
        evidence_files=file_manifest,interpretation='Descriptive within-host results; ratios above 1 favor CM. No general winner or production promotion.'))
    print(json.dumps(dict(scheduled=len(rows),verified_cells=verified,unique_structures=len(cache))))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    a=p.parse_args()
    verify(a.output,a.protocol,a.destination)
