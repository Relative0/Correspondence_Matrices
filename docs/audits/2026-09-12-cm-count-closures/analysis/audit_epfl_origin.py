"""Check the retained EPFL bytes against declared and historical upstream blobs."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2];OUT=AUDIT/'upstream'
name='best_results/size/int2float_size_2025.blif'
raw=(ROOT/'external/epfl-benchmarks'/name).read_bytes()
assert hashlib.sha256(raw).hexdigest()=='6d6e8253b30010fe5b2f574e55e19fd9ce35a7872cd8012a246b716f143121c2'
pins=['0060e156826e733d69bf5b3322d1bdd0d03a1f9a','8c0ee0d0748ede5ce0afe48efe123668274ff120','374ad2b142a7331bffc6a9d378dac75917d9e793']
def get(pin):
    url='https://raw.githubusercontent.com/lsils/benchmarks/'+pin+'/'+name
    path=OUT/('EPFL-'+pin+'.blif')
    if path.exists():data=path.read_bytes()
    else:
        try:
            with urllib.request.urlopen(url,timeout=30) as response:data=response.read()
        except urllib.error.HTTPError as exc:
            return dict(pin=pin,url=url,status='http_error',http_status=exc.code)
        path.write_bytes(data)
    return dict(pin=pin,url=url,status='downloaded',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
        git_blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
        crlf=data.count(b'\r\n'),crcrlf=data.count(b'\r\r\n'),
        retained_matches_added_cr_before_lf=(data.replace(b'\n',b'\r\n')==raw),retained_exact=data==raw)
rows=list(ThreadPoolExecutor(max_workers=3).map(get,pins))
prior_path=ROOT/'build/cm-closures/docs/audits/2026-09-12-cm-evidence-frontiers/EPFL-UPSTREAM-COMPARISON.json'
prior=json.loads(prior_path.read_text())
old=next(r for r in prior['files'] if r['path']=='external/epfl-benchmarks/'+name)
normalized=raw.replace(b'\r\n',b'\n')
normalized_blob=hashlib.sha1(b'blob '+str(len(normalized)).encode()+b'\0'+normalized).hexdigest()
assert rows[0]['retained_exact'] and rows[0]['git_blob']==old['upstream_git_blob']
assert normalized_blob==old['normalized_git_blob'] and normalized_blob!=old['upstream_git_blob']
result=dict(retained_path='external/epfl-benchmarks/'+name,retained_sha256=hashlib.sha256(raw).hexdigest(),
    retained_bytes=len(raw),retained_crcrlf=raw.count(b'\r\r\n'),rows=rows,
    retained_bytes_changed=False,historical_conversion_process_proven=False,
    prior_comparison_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest(),
    prior_normalized_retained_git_blob=normalized_blob,
    prior_error='Retained CRLF bytes were normalized to LF before comparison with the upstream Git blob, which already contains CRLF. Raw retained and raw upstream bytes are identical.',
    disposition='Declared source origin verified by exact bytes and Git blob; prior asymmetric-normalization mismatch was a false positive')
(OUT/'EPFL-BYTE-COMPARISON.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
