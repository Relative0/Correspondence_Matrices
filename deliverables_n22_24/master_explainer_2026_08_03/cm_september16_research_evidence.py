"""Validate the public exact-count/decomposition source bundle before rendering."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RELATIVE = Path('results/2026-09-16/exact-count-and-decomposition')
MANIFEST_SHA256 = '73d1decbcdf6e1964f75019ddf9092d4456c7632c259eb3444b83acbfb9da24c'


def build_research_evidence():
    base = HERE / RELATIVE
    payload = (base / 'PUBLICATION-MANIFEST.json').read_bytes()
    if hashlib.sha256(payload).hexdigest() != MANIFEST_SHA256:
        raise ValueError('September 16 research publication manifest changed')
    manifest = json.loads(payload)
    files = {(RELATIVE / 'PUBLICATION-MANIFEST.json').as_posix(): payload}
    for record in manifest['artifacts']:
        path = (base / record['path']).resolve()
        if not path.is_relative_to(base.resolve()):
            raise ValueError('Research artifact escapes publication directory')
        contents = path.read_bytes()
        if len(contents) != record['bytes'] or hashlib.sha256(contents).hexdigest() != record['sha256']:
            raise ValueError('Changed research artifact: ' + record['path'])
        record['href'] = (RELATIVE / record['path']).as_posix()
        files[record['href']] = contents
    evidence = json.loads(files[(RELATIVE / 'PUBLIC-SUMMARY.json').as_posix()])
    evidence['artifacts'] = manifest['artifacts']
    evidence['manifest_sha256'] = MANIFEST_SHA256
    evidence['manifest_href'] = (RELATIVE / 'PUBLICATION-MANIFEST.json').as_posix()
    evidence['report_href'] = (RELATIVE / 'REPORT.md').as_posix()
    evidence['bundle_href'] = (RELATIVE / 'research-source-and-evidence.zip').as_posix()
    return evidence, files
