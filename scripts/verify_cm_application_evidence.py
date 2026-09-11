"""Verify sealed bytes and admission gates without rerunning cloud computations."""
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'docs/audits/2026-09-12-cm-application-evidence'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(root, name):
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        raise ValueError('unsafe sealed path')
    target=root/path
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('sealed path escapes root')
    return target


def verify():
    expected=(AUDIT/'FINAL-MANIFEST.sha256').read_text().split()[0]
    if sha(AUDIT/'FINAL-MANIFEST.json')!=expected:
        raise ValueError('seal checksum mismatch')
    manifest=json.loads((AUDIT/'FINAL-MANIFEST.json').read_text())
    found={p.relative_to(AUDIT).as_posix() for p in AUDIT.rglob('*') if p.is_file()}
    if found!=set(manifest['artifacts'])|{'FINAL-MANIFEST.json','FINAL-MANIFEST.sha256'}:
        raise ValueError('artifact membership mismatch')
    for name, record in manifest['artifacts'].items():
        path=safe(AUDIT,name)
        if path.stat().st_size!=record['bytes'] or sha(path)!=record['sha256']:
            raise ValueError('artifact identity mismatch: '+name)
    for name, digest in manifest['current_sources'].items():
        if sha(safe(ROOT,name))!=digest:
            raise ValueError('current source identity mismatch: '+name)
    profiles=json.loads((AUDIT/'SOURCE-PROFILES.json').read_text())
    for profile in profiles.values():
        for member in profile['members'].values():
            path=safe(AUDIT,member['object'])
            if sha(path)!=member['sha256'] or path.stat().st_size!=member['bytes']:
                raise ValueError('frozen source object mismatch')
    public=json.loads((AUDIT/'PUBLIC-RESULTS.json').read_text())
    verification=json.loads((AUDIT/'VERIFICATION.json').read_text())
    if not all(row['cleanup_verified'] for row in verification['attempts']):
        raise ValueError('cleanup is incomplete')
    if public['regression']['new_failure_ids'] or public['consumer']['natural_sessions_admitted']:
        raise ValueError('unsupported regression or consumer admission')
    for kind in ('feature','independent'):
        for row in public[kind+'_methods']:
            if row['status']=='complete' and not row['independently_cross_checked']:
                raise ValueError('unverified performance point')
            if row['status']!='complete' and 'median_total_ms' in row:
                raise ValueError('incomplete row carries a plotted time')
    return dict(status='pass',artifacts=len(manifest['artifacts']),sources=len(manifest['current_sources']),
                profiles=len(profiles),science_sha256=expected,solvers_rerun=False)


if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
