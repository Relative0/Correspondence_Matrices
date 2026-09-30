"""Verify the published structured-factorization evidence without rerunning it."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(site):
    root = (site / 'results/2026-09-30/structured-factorization').resolve()
    manifest = json.loads((root / 'artifact-manifest.json').read_text(encoding='utf-8'))
    if manifest['schema'] != 'cm-structured-factorization-evidence/v1':
        raise ValueError('Unexpected evidence schema')
    for relative, record in manifest['files'].items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Artifact escapes publication folder')
        payload = path.read_bytes()
        if len(payload) != record['bytes'] or hashlib.sha256(payload).hexdigest() != record['sha256']:
            raise ValueError('Changed evidence: ' + relative)
    campaign = root / 'prospective-campaign'
    analysis = json.loads((campaign / 'campaign_analysis.json').read_text())
    freeze = json.loads((campaign / 'campaign_freeze.json').read_text())
    for relative, expected in freeze['source_hashes'].items():
        if hashlib.sha256((campaign / relative).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen campaign source drift: ' + relative)
    for split, count in [('validation', 252), ('heldout', 504)]:
        payload = (campaign / (split + '_results.jsonl')).read_bytes()
        if hashlib.sha256(payload).hexdigest() != analysis[split + '_sha256']:
            raise ValueError('Raw-row provenance mismatch')
        rows = [json.loads(line) for line in payload.splitlines()]
        if len(rows) != count or not all(row['status'] == 'ok' and
                row['semantic_correct'] is True and row['carrier_correct'] is True for row in rows):
            raise ValueError('Campaign exactness record changed')
    if analysis['mechanism_go'] is not True or analysis['algorithmic_go'] is not False:
        raise ValueError('Campaign disposition changed')
    if (analysis['baseline'], analysis['challenger']) != ('B2', 'L1'):
        raise ValueError('Locked comparison changed')
    page = (site / 'p-series-study-guide.html').read_text(encoding='utf-8')
    if 'structured-factorization' not in page or '1.03798' not in page:
        raise ValueError('Study guide omits the evidence addendum')
    return {'status': 'PASS', 'verified_artifacts': len(manifest['files']),
            'mechanism_go': True, 'algorithmic_go': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    print(json.dumps(verify(parser.parse_args().site)))
