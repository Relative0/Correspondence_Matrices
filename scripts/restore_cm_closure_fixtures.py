"""Recover the 46 original public CNF fixtures named in the retained P6 freeze."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
FREEZE='docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json'
FREEZE_SHA='02038bad06f72da2b47a4f63a2857f484f141fa48e4842440e80464e777da2d0'
PINS={'d4v2':'15eff31962466804a48374826b9e5a746fc2766e','d4':'333370cc1e843dd0749c1efe88516e72b5239174'}
OLD_AUDIT='docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/continuation-20260829-125214'
EMPTY_RECORD=OLD_AUDIT+'/HTTP-NATIVE-SCOUT-PROCFS-V6-LOCAL-PREFLIGHT-FAILURE-20260829.json'
EMPTY_SHA='612baf08e19986d4a4ce74e6f3146b1d3599fa27081922c090917b424ab5c100'

def restore_empty_directory(root,apply):
    raw=(root/EMPTY_RECORD).read_bytes()
    if sha(raw)!=EMPTY_SHA:raise ValueError('historical empty-directory receipt drift')
    record=json.loads(raw)
    if not (record['output_directory_exists'] and record['output_directory_children']==0
            and record['creation_attempted'] is False and record['runpod_create_requests']==0):
        raise ValueError('historical empty-directory state differs')
    name=record['output_directory']
    if name!='http-native-scout-procfs-race-retry-execute-001':raise ValueError('unexpected directory')
    path=root/OLD_AUDIT/name
    if not path.resolve().is_relative_to(root.resolve()):raise ValueError('directory escapes root')
    if path.exists() and (not path.is_dir() or any(path.iterdir())):raise ValueError('existing historical output is not empty')
    existed=path.exists()
    if apply:path.mkdir(exist_ok=True)
    return dict(path=path.relative_to(root).as_posix(),receipt_sha256=EMPTY_SHA,
                previously_existed=existed,exists=path.exists(),empty=True,cloud_operation=False)

def sha(data):return hashlib.sha256(data).hexdigest()

def destination(root,name):
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or ':' in name or '\\' in name:
        raise ValueError('unsafe fixture path')
    if len(path.parts)<4 or path.parts[0]!='external' or path.parts[1] not in PINS or path.suffix!='.cnf':
        raise ValueError('fixture outside CNF allowlist')
    target=(root/path).resolve()
    if not target.is_relative_to(root.resolve()):raise ValueError('fixture symlink escapes root')
    return target

def recover_bytes(data,expected):
    if sha(data)==expected:return data,'identity'
    if b'\r' not in data:
        restored=data.replace(b'\n',b'\r\n')
        if sha(restored)==expected:return restored,'restore_crlf'
    raise ValueError('upstream bytes do not recover the frozen identity')

def restore(root,*,apply=False,download=False):
    restore_empty_directory(root,False)
    raw=(root/FREEZE).read_bytes()
    if sha(raw)!=FREEZE_SHA:raise ValueError('historical freeze drift')
    sources={}
    for case in json.loads(raw)['cases']:
        row=case['source'];name=row['path']
        if not name.endswith('.cnf'):continue
        if name in sources and sources[name]!=row:raise ValueError('conflicting fixture identity')
        sources[name]=row
    if len(sources)!=46 or sum(r['bytes'] for r in sources.values())>16<<20:
        raise ValueError('unexpected historical fixture set')
    pending=[];records=[]
    for name,row in sorted(sources.items()):
        target=destination(root,name);parts=PurePosixPath(name).parts;repo=parts[1];pin=PINS[repo]
        if pin not in row['provenance']:raise ValueError('unbound upstream revision')
        url=f'https://raw.githubusercontent.com/crillab/{repo}/{pin}/'+('/'.join(parts[2:]))
        result=dict(path=name,expected_sha256=row['sha256'],expected_bytes=row['bytes'],url=url,license=row['license'])
        if target.exists():
            if not target.is_file() or target.stat().st_size!=row['bytes'] or sha(target.read_bytes())!=row['sha256']:
                raise ValueError('existing fixture differs: '+name)
            result['status']='already_verified'
        elif not download:result['status']='missing'
        else:
            with urllib.request.urlopen(url,timeout=45) as response:data=response.read((16<<20)+1)
            if len(data)>16<<20:raise ValueError('upstream fixture too large')
            restored,transform=recover_bytes(data,row['sha256'])
            if len(restored)!=row['bytes']:raise ValueError('fixture byte count differs')
            pending.append((target,restored))
            result.update(status='restored' if apply else 'download_verified',upstream_sha256=sha(data),
                          upstream_bytes=len(data),transform=transform)
        records.append(result)
    # Verify every target and downloaded identity before writing any fixture.
    if apply:
        for target,data in pending:
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream:stream.write(data)
    directory=restore_empty_directory(root,apply)
    return dict(freeze=FREEZE,freeze_sha256=FREEZE_SHA,expected_files=46,empty_directory=directory,
                restored=len(pending) if apply else 0,
                complete=all(r['status'] in ('already_verified','restored') for r in records),files=records)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--restore',action='store_true')
    parser.add_argument('--download',action='store_true');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=restore(ROOT,apply=args.restore,download=args.download)
    with args.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))
    raise SystemExit(0 if result['complete'] else 1)
