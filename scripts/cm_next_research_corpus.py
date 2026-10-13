"""Apply the prospectively recorded additional public-CNF selection rule."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/2026-09-11-cm-next-research'
REV='afa60ee2c836e7bdc4068e0f4f128ea31158d2ad'
REPO='SoftVarE-Group/feature-model-benchmark'

def get(url, limit):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CM-source-audit'}),timeout=45) as response:
        data=response.read(limit+1)
    assert len(data)<=limit
    return data

def main():
    assert (OUT/'CORPUS-PROTOCOL.md').is_file()
    assert not (OUT/'CORPUS.json').exists()
    old=json.loads((ROOT/'docs/audits/2026-09-11-cm-bucket-counts/CORPUS.json').read_text())
    excluded={str(PurePosixPath(f['path']).parent) for f in old['files']}
    tree=json.loads(get(f'https://api.github.com/repos/{REPO}/git/trees/{REV}?recursive=1',16<<20))
    assert tree.get('truncated') is False
    groups={}
    for item in tree['tree']:
        path=item['path']; directory=str(PurePosixPath(path).parent)
        if item['type']!='blob' or not path.startswith('feature_models/dimacs/') or not path.endswith('.dimacs') or directory in excluded: continue
        if directory not in groups or (item['size'],path)<(groups[directory]['size'],groups[directory]['path']): groups[directory]=item
    candidates=sorted(groups.values(),key=lambda r:(r['size'],r['path']))[:12]
    (OUT/'CANDIDATES.json').write_text(json.dumps({'protocol_sha256':hashlib.sha256((OUT/'CORPUS-PROTOCOL.md').read_bytes()).hexdigest(), 'excluded_systems':sorted(excluded),'candidates':candidates},indent=2)+'\n')
    directory=OUT/'corpus'; directory.mkdir(exist_ok=False)
    def retrieve(pair):
        i,item=pair
        record={'id':f'additional-{i:02}','source_path':item['path'],'source_git_blob':item['sha'],'bytes':item['size']}
        if item['size']>65536: return dict(record,admitted=False,reason='source byte limit exceeded')
        url=f'https://raw.githubusercontent.com/{REPO}/{REV}/'+urllib.parse.quote(item['path'],safe='/')
        payload=get(url,65536)
        assert len(payload)==item['size']
        assert hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()==item['sha']
        filename=record['id']+'.dimacs'; (directory/filename).write_bytes(payload)
        import sys
        if str(ROOT/'build/cm-next') not in sys.path: sys.path.insert(0,str(ROOT/'build/cm-next'))
        from cmbench.backends.bucket_counts import parse_dimacs
        record.update(filename=filename,url=url,sha256=hashlib.sha256(payload).hexdigest())
        try:
            n,clauses=parse_dimacs(payload.decode('utf-8-sig'),max_vars=512,max_clauses=3000)
            if n==0: raise ValueError('zero-variable source excluded')
            record.update(admitted=True,n=n,clauses=len(clauses))
        except ValueError as exc: record.update(admitted=False,reason=str(exc))
        return record
    with ThreadPoolExecutor(max_workers=4) as pool: files=list(pool.map(retrieve,enumerate(candidates,1)))
    license_item=next(item for item in tree['tree'] if item['path'].lower() in ('license','license.md','license.txt'))
    license_payload=get(f'https://raw.githubusercontent.com/{REPO}/{REV}/'+license_item['path'],65536)
    (directory/'UPSTREAM-LICENSE.txt').write_bytes(license_payload)
    result={'repository':REPO,'commit':REV,'files':files,'license_sha256':hashlib.sha256(license_payload).hexdigest()}
    (OUT/'CORPUS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'selected':len(files),'admitted':sum(f['admitted'] for f in files),'systems':[f['source_path'].split('/')[-2] for f in files]}))

if __name__=='__main__': main()
