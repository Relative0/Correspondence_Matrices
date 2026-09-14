"""Verify delivered hashes; --freeze creates only this audit's new manifests."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE_PATHS = [
    'cmbench/biology_controls.py', 'cmbench/benchmark_contracts.py',
    'cmbench/backends/exact_controls_v2.py', 'scripts/cm_biology_control_audit.py',
    'tests/test_cm_biology_attribution_controls.py', 'tests/test_cm_benchmark_attribution_audit.py',
    'cmbench/biology_bnet.py', 'cmbench/backends/native_count.py',
    'cmbench/backends/native_sat.py', 'cmbench/backends/projected_count.py',
    'cmbench/backends/factorized_counts.py', 'cmbench/backends/bucket_counts.py',
    'cmbench/backends/packed_queries.py', 'cmbench/backends/packed_mask_cache.py',
    'bitset_backend.py', 'cm_ir.py', 'cm_exprlib.py',
]
REQUIRED = ['REPORT.md', 'CLAIM_EVIDENCE_REGISTER.json', 'BIOLOGY_CORPUS_AUDIT.json',
            'CONTROL_CONTRACT_AUDIT.md', 'STATISTICAL_INDEPENDENCE.md',
            'CM_BIOLOGY_EXPERIMENT_SPEC.md', 'TEST_RESULTS.md', 'HANDOFF.md']


def record(path):
    data = path.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def main(freeze=False):
    for name in REQUIRED:
        if not (HERE / name).is_file():
            raise ValueError(f'missing required deliverable: {name}')
    if freeze:
        dump('SOURCE_MANIFEST.json', {'schema': 'cm-attribution-sources/v1',
            'baseline_commit': 'b3f10bc582f0c2a59a0fe7513af88199a4f65c56',
            'status': 'local_uncommitted_audit_and_control_surface',
            'files': {name: record(ROOT / name) for name in SOURCE_PATHS}})
        files = {p.relative_to(ROOT).as_posix(): record(p) for p in sorted(HERE.rglob('*'))
                 if p.is_file() and p.suffix in {'.md', '.json', '.py', '.xml', '.bnet', '.cnf'}
                 and p.name != 'AUDIT_MANIFEST.json' and '__pycache__' not in p.parts}
        dump('AUDIT_MANIFEST.json', {'schema': 'cm-attribution-delivery/v1', 'files': files})
    checked = 0
    for name in ('SOURCE_MANIFEST.json', 'AUDIT_MANIFEST.json'):
        manifest = json.loads((HERE / name).read_text(encoding='utf-8'))
        for relative, expected in manifest['files'].items():
            if record(ROOT / relative) != expected:
                raise ValueError(f'manifest mismatch: {relative}')
            checked += 1
    register = json.loads((HERE / 'CLAIM_EVIDENCE_REGISTER.json').read_text(encoding='utf-8'))
    for artifact in register['artifacts'].values():
        actual = record(ROOT / artifact['path'])
        if actual['sha256'] != artifact['sha256'] or actual['bytes'] != artifact['bytes']:
            raise ValueError(f'claim evidence mismatch: {artifact["path"]}')
    stats = json.loads((HERE / 'STATISTICAL_REANALYSIS.json').read_text(encoding='utf-8'))
    for path, expected in stats['sources'].items():
        actual = record(ROOT / path)
        if actual['sha256'] != expected['sha256'] or actual['bytes'] != expected['bytes']:
            raise ValueError(f'statistical source mismatch: {path}')
    print(json.dumps({'status': 'passed', 'manifest_entries_verified': checked,
                      'claim_artifacts_verified': len(register['artifacts']),
                      'statistical_sources_verified': len(stats['sources']),
                      'claims': len(register['claims'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    main(parser.parse_args().freeze)
