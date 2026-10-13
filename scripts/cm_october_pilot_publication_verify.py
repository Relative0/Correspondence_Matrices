"""Verify all published October pilot numeric records and source downloads."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
from statistics import median
import zipfile

ROOT=Path(__file__).resolve().parents[1]
RELATIVE='results/2026-10-14/cpu-pilots'


def verify(site):
    site=Path(site);folder=site/RELATIVE
    summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    if summary['schema']!='cm-october-cpu-pilots/v1' or summary['reviewed']!='2026-10-14':raise ValueError('pilot summary identity')
    manifest=json.loads((folder/'checksums.json').read_text(encoding='utf-8'))['files']
    files={}
    for name,record in manifest.items():
        if Path(name).name!=name:raise ValueError('public file escaped release')
        payload=(folder/name).read_bytes()
        if len(payload)!=record['bytes'] or hashlib.sha256(payload).hexdigest()!=record['sha256']:raise ValueError('stale pilot download: '+name)
        files[RELATIVE+'/'+name]=record
    groups=defaultdict(list)
    for pilot in summary['pilots']:
        platform=pilot['platform'];rows=[json.loads(line) for line in (folder/pilot['trial_download']).read_text(encoding='utf-8').splitlines()]
        if len(rows)!=112 or [r['cell']['cell_id'] for r in rows]!=list(range(112)):raise ValueError('pilot rows incomplete/reordered')
        pairs=defaultdict(dict)
        for row in rows:
            if not row['valid'] or row['status']!='ok' or row['returncode']!=0:raise ValueError('pilot invalid row omitted from claims')
            if set(row)!={'cell','status','returncode','wall_ns','valid','result','resource_summary'}:raise ValueError('unexpected operational data in public record')
            cell=row['cell'];rep=row['result']['repetitions'][0]
            if len(row['result']['repetitions'])!=1:raise ValueError('pilot repetition contract')
            pairs[(cell['case'],cell['lifecycle'],cell['pair'])][cell['arm']]=rep['delivered_sha256']
            groups[(platform,cell['case'],cell['lifecycle'],cell['arm'])].append(row)
        if len(pairs)!=56 or any(len(p)!=2 or len(set(p.values()))!=1 for p in pairs.values()):raise ValueError('pilot pair mismatch')
    for phase in summary['phases']:
        records=groups[(phase['platform'],phase['case'],phase['lifecycle'],phase['arm'])]
        expected=3 if phase['lifecycle']=='cold' else 5
        if len(records)!=expected or phase['cells']!=expected:raise ValueError('pilot lifecycle incomplete')
        if median(r['wall_ns'] for r in records)/1e6!=phase['full_lifecycle_median_ms']:raise ValueError('pilot full lifecycle median stale')
        for key in ('compile','preparation','query','validation'):
            if median(r['result']['phases_ns'][key] for r in records)/1e6!=phase[key+'_median_ms']:raise ValueError('pilot phase median stale')
    csv_rows=list(csv.DictReader((folder/'phase-medians.csv').open(encoding='utf-8',newline='')))
    if len(csv_rows)!=len(summary['phases']):raise ValueError('pilot CSV row count')
    for csv_row,phase in zip(csv_rows,summary['phases']):
        for key,value in phase.items():
            if str(value)!=csv_row[key]:raise ValueError('pilot CSV stale')
    source=json.loads((folder/'source-subset-sha256.json').read_text(encoding='utf-8'))['files']
    with zipfile.ZipFile(folder/'frozen-wsl-source.zip') as archive:
        if len(archive.namelist())!=len(set(archive.namelist())) or set(archive.namelist())!=set(source):raise ValueError('source archive membership')
        for name,digest in source.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=digest:raise ValueError('source archive byte mismatch')
    for page in ('index.html','latest-results.html','layperson.html','investor.html','expert.html','usecases.html','findings.html','data-downloads.html'):
        text=(site/page).read_text(encoding='utf-8')
        if text.count('id: "october-cpu-pilots"') and RELATIVE+'/index.html' not in text:raise ValueError('pilot link missing')
        if 'CPU pilots completed — crossover thresholds remain open' not in text or RELATIVE+'/index.html' not in text:raise ValueError('pilot section missing: '+page)
    return {'status':'verified','pilots':2,'trial_records':224,'matching_pairs':112,'phase_rows':len(summary['phases']),
            'source_subset_files':len(source),'files':files}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--site',type=Path,default=ROOT/'deliverables_n22_24/master_explainer_2026_08_03');args=parser.parse_args()
    result=verify(args.site)
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))
