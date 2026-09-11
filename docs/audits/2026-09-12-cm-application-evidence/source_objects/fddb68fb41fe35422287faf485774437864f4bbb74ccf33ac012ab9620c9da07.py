"""Recover pinned d4 and LogikBench dependencies without changing old manifests.

The historical executable is downloaded from its original immutable upstream;
it is never executed by this restorer or redistributed in a new archive.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/continuation-20260829-125214')
MANIFEST = BASE/'RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-MANIFEST-V2-20260830.json'
ARCHIVE = BASE/'RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-BUNDLE-V2-20260830.zip'
MANIFEST_SHA = '5365b4362fc42790bf7107c6b8da29ec61b79faf8d69ac40bcfeb77a87640354'
ARCHIVE_SHA = '1b3796d6ded0f6d1b0d6266c5e783f1b0687aae9c7ecfdac901ad625c6e6ff95'
D4 = 'external/d4v2/scripts/d4ScriptsCompetition/bin/d4'
D4_SHA = '29cb30f351ed92b02343e5e7a98b082e949d9838245f37c0bcdecf68a57ffd39'
D4_BYTES = 5054920
D4_URL = 'https://raw.githubusercontent.com/crillab/d4v2/15eff31962466804a48374826b9e5a746fc2766e/scripts/d4ScriptsCompetition/bin/d4'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def target(root, name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or ':' in name or '\\' in name:
        raise ValueError('unsafe fixture target')
    if name != D4 and not name.startswith('external/logikbench-confirmation-20260830/'):
        raise ValueError('fixture outside allowlist')
    result = root/path
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError('fixture symlink escapes repository')
    return result


def apply_exact(root, rows, *, apply=False):
    pending = []
    seen = set()
    verified = 0
    for name, data, expected in rows:
        if name in seen or sha(data) != expected:
            raise ValueError('duplicate fixture or byte identity mismatch')
        seen.add(name)
        destination = target(root, name)
        if destination.exists():
            if not destination.is_file() or sha(destination.read_bytes()) != expected:
                raise ValueError('existing fixture differs: '+name)
            verified += 1
        else:
            pending.append((destination, data))
    # All identities and destinations pass before the first write.
    if apply:
        for destination, data in pending:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as stream:
                stream.write(data)
    return dict(expected_files=len(seen), already_verified=verified,
                restored=len(pending) if apply else 0,
                missing=0 if apply else len(pending), complete=apply or not pending)


def restore(root, *, apply=False, download_d4=False):
    raw = (root/MANIFEST).read_bytes()
    packed = (root/ARCHIVE).read_bytes()
    if sha(raw) != MANIFEST_SHA or sha(packed) != ARCHIVE_SHA:
        raise ValueError('historical manifest/archive hash mismatch')
    rows = []
    with zipfile.ZipFile(io.BytesIO(packed)) as archive:
        for item in json.loads(raw)['files']:
            if item['provenance'] != 'public-logikbench':
                continue
            data = archive.read(item['target'])
            if len(data) != item['bytes']:
                raise ValueError('historical fixture size mismatch')
            rows.append((item['source'], data, item['sha256']))
    if len(rows) != 156:
        raise ValueError('unexpected LogikBench file count')
    binary = target(root, D4)
    if binary.is_file():
        data = binary.read_bytes()
    elif download_d4:
        with urllib.request.urlopen(D4_URL, timeout=60) as response:
            data = response.read(D4_BYTES+1)
    else:
        raise ValueError('d4 missing; use --download-d4 for the pinned public binary')
    if len(data) != D4_BYTES or sha(data) != D4_SHA:
        raise ValueError('d4 historical identity mismatch')
    rows.append((D4, data, D4_SHA))
    result = apply_exact(root, rows, apply=apply)
    result.update(manifest_sha256=MANIFEST_SHA, archive_sha256=ARCHIVE_SHA,
                  d4_sha256=D4_SHA, d4_url=D4_URL, historical_expectations_changed=False)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', action='store_true')
    parser.add_argument('--download-d4', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = restore(ROOT, apply=args.restore, download_d4=args.download_d4)
    if args.output:
        with args.output.open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['complete'] else 1)
