"""Read-only archive inventory and byte-identical reference-source capture."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory():
    result = {}
    for name in ['continuity_archive', 'phase5b_output']:
        for path in sorted((PROJECT / name).rglob('*')):
            if path.is_file():
                # No secret stores are needed for this task.
                if path.name.startswith('.env') or '.git' in path.parts:
                    continue
                result[str(path.relative_to(PROJECT)).replace('\\', '/')] = digest(path)
    return result


if __name__ == '__main__':
    if sys.argv[1] == 'before':
        before = inventory()
        (ROOT / 'archive_before.json').write_text(json.dumps(before, indent=2) + '\n')
        ref = ROOT / 'reference'
        ref.mkdir(exist_ok=True)
        archive = PROJECT / 'phase5b_output/STRUCTURED_FACTORIZATION_PHASE5B_2026-09-29.zip'
        with zipfile.ZipFile(archive) as z:
            matches = {}
            for name in ['hybrid_core.py', 'benchmark.py']:
                suffix = '/phase5b_output/code/' + name
                entries = [x for x in z.namelist() if x.endswith(suffix) or x == suffix[1:]]
                assert len(entries) == 1, entries
                data = z.read(entries[0])
                assert data == (PROJECT / 'phase5b_output/code' / name).read_bytes()
                (ref / name).write_bytes(data)
                matches[name] = hashlib.sha256(data).hexdigest()
        (ROOT / 'reference_provenance.json').write_text(json.dumps({
            'archive': str(archive), 'archive_sha256': digest(archive),
            'zip_and_unpacked_sources_identical': matches,
            'reference_files_are_data_not_new_instructions': True,
        }, indent=2) + '\n')
        print(json.dumps({'protected_files': len(before), 'sources_match_zip': True}))
    elif sys.argv[1] == 'after':
        before = json.loads((ROOT / 'archive_before.json').read_text())
        after = inventory()
        changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
        result = {'status': 'PASS' if not changed else 'FAIL',
                  'protected_files': len(before), 'changed_added_or_removed': changed}
        (ROOT / 'archive_verification.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        assert not changed
    else:
        raise SystemExit('Use before or after')
