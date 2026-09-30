"""Verify copied-source provenance and unchanged archived Phase 4/5 package."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
PROBE = PROJECT / 'live_vtree_probe_2026-09-29'
ARCHIVE = PROJECT / 'phase5b_output/STRUCTURED_FACTORIZATION_PHASE5B_2026-09-29.zip'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run():
    before = json.loads((PROBE / 'archive_before.json').read_text())
    spec = importlib.util.spec_from_file_location('probe_provenance', PROBE / 'provenance.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    now = module.inventory()  # Read-only; does not write to the probe.
    changed = sorted(k for k in before.keys() | now.keys() if before.get(k) != now.get(k))
    originals = {
        'reference/hybrid_core.py': PROJECT / 'phase5b_output/code/hybrid_core.py',
        'reference/benchmark.py': PROJECT / 'phase5b_output/code/benchmark.py',
        'live_moves.py': PROBE / 'live_moves.py',
        'dev_fixtures.py': PROBE / 'fixtures.py',
    }
    copied = {name: digest(ROOT / name) == digest(source) for name, source in originals.items()}
    result = {'status': 'PASS' if not changed and all(copied.values()) else 'FAIL',
              'protected_archive_files': len(before), 'archive_changes': changed,
              'copied_sources_match': copied, 'archive_zip_sha256': digest(ARCHIVE),
              'python': sys.version,
              'integration_source_sha256': {
                  p.name: digest(p) for p in sorted(ROOT.glob('*.py'))}}
    (ROOT / 'source_and_archive_verification.json').write_text(
        json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'protected_archive_files',
                                            'archive_changes', 'copied_sources_match')}, indent=2))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    run()
