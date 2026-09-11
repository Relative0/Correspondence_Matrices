"""Restore exact retained scientific fixtures; refuse differing existing files."""
import argparse
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import zipfile

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'tests/fixtures/cm_historical_restoration.json'

def sha(data):return hashlib.sha256(data).hexdigest()

def safe_target(root,name):
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or ':' in name or '\\' in name:
        raise ValueError('unsafe fixture path')
    if not name.startswith(('docs/recognition/','external/epfl-benchmarks/')):
        raise ValueError('fixture outside historical allowlist')
    target=root/path
    if not target.resolve().is_relative_to(root.resolve()):raise ValueError('fixture symlink escapes repository')
    return target


def restore(root,manifest,*,apply=False):
    if sum(x['bytes'] for x in manifest['files'])>160<<20:raise ValueError('fixture total bound exceeded')
    files=manifest['files'];targets=[r['target'] for r in files]
    if len(targets)!=len(set(targets)):raise ValueError('duplicate fixture target')
    pending=[];verified=0;written=0
    # Validate every archive, member, destination and byte identity before any
    # write. Existing files with different content remain untouched.
    for spec in manifest['archives']:
        archive_path=root/spec['path']
        if not archive_path.resolve().is_relative_to(root.resolve()):raise ValueError('archive outside repository')
        raw=archive_path.read_bytes()
        if len(raw)>32<<20 or sha(raw)!=spec['sha256']:raise ValueError('fixture archive hash mismatch')
        rows=[r for r in files if r['archive']==spec['path']]
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members=archive.infolist()
            if len(members)!=len(rows) or {x.filename for x in members}!={r['member'] for r in rows}:
                raise ValueError('fixture archive member mismatch')
            if sum(x.file_size for x in members)>128<<20:raise ValueError('fixture archive expansion exceeded')
            for row in rows:
                member=archive.getinfo(row['member'])
                if member.is_dir() or (member.external_attr>>16)&0o170000==0o120000:
                    raise ValueError('nonregular fixture archive member')
                data=archive.read(member)
                if len(data)!=row['bytes'] or sha(data)!=row['sha256']:raise ValueError('fixture member hash mismatch')
                target=safe_target(root,row['target'])
                if target.exists():
                    if not target.is_file() or sha(target.read_bytes())!=row['sha256']:
                        raise ValueError('existing fixture differs: '+row['target'])
                    verified+=1
                else:pending.append((target,data))
    if verified+len(pending)!=len(files):raise ValueError('unassigned fixture manifest member')
    if apply:
        for target,data in pending:
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream:stream.write(data)
            written+=1
    return dict(expected_files=len(files),already_verified=verified,restored=written,
                missing=len(pending)-written,complete=verified+written==len(files))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    result=restore(ROOT,json.loads(MANIFEST.read_text()),apply=args.restore)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['complete'] else 1)
