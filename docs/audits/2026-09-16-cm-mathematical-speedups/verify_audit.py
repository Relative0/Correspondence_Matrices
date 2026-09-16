"""Verify this research package without changing source or historical evidence."""
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'audit-verification.json'
    artifacts = [json.loads((HERE / name).read_text(encoding='utf-8')) for name in (
        'probe-results.json', 'probe-results-verified.json', 'probe-results-pack-control.json')]
    assert artifacts[0] == artifacts[1]
    last = artifacts[-1]
    for item in artifacts:
        assert item['fusion_checks'] == 5120
        assert item['substitution_checks'] == 1310720
        assert item['mismatches'] == 0
        for path, expected in item['source_sha256'].items():
            assert sha((ROOT / path).read_bytes()) == expected, path
    for a, b in zip(artifacts[0]['census'], last['census']):
        for key, value in a.items():
            if key != 'examples':
                assert b[key] == value, (a['id'], key)
    cohorts = {}
    for cohort in ('exposed_epfl', 'exposed_c36'):
        rows = [x for x in last['census'] if x['cohort'] == cohort]
        cohorts[cohort] = {
            'cases': len(rows), 'source_nodes': sum(x['nodes'] for x in rows),
            'cm_positive_cases': sum(x['residual_cuts'] > 0 for x in rows),
            'cm_residual_cuts': sum(x['residual_cuts'] for x in rows),
            'pack_positive_cases': sum(x['residual_after_one_pass_pack'] > 0 for x in rows),
            'pack_residual_cuts': sum(x['residual_after_one_pass_pack'] for x in rows),
        }
    assert cohorts['exposed_epfl'] == dict(cases=64, source_nodes=10146,
        cm_positive_cases=61, cm_residual_cuts=2310, pack_positive_cases=61, pack_residual_cuts=1821)
    assert cohorts['exposed_c36'] == dict(cases=18, source_nodes=1224,
        cm_positive_cases=0, cm_residual_cuts=0, pack_positive_cases=0, pack_residual_cuts=0)
    link_count = 0
    for path in HERE.glob('*.md'):
        content = path.read_text(encoding='utf-8')
        assert content.endswith('\n')
        assert all(line == line.rstrip() for line in content.splitlines()), path.name
        assert '\u2295' not in content and '\\oplus' not in content, path.name
        for target in re.findall(r'(?<![\w])\[[^\]\n]+\]\(([^)\n]+)\)', content):
            if target.startswith(('https://', 'http://', '#')):
                continue
            linked = path.parent / target.split('#')[0]
            assert linked.exists() or linked.resolve() == output_path.resolve(), (path.name, target)
            link_count += 1
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    corpus = 'deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl'
    work = (ROOT / corpus).read_bytes()
    blob = subprocess.check_output(['git', 'show', 'HEAD:' + corpus], cwd=ROOT)
    assert work.replace(b'\r\n', b'\n') == blob
    assert sha(blob) == 'bb98f14a5525a2d869a7ad80e25e879fd176e78ad6d01c51385edc947f2806ac'
    result = {
        'status': 'pass', 'scope': 'artifact consistency, current dependencies, local links, syntax, notation, corpus byte diagnosis',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'cohorts': cohorts, 'local_links_checked': link_count,
        'corpus': {'working_sha256': sha(work), 'git_blob_sha256': sha(blob), 'equal_after_lf_normalization': True},
        'files_sha256': {p.name: sha(p.read_bytes()) for p in sorted(HERE.iterdir())
                         if p.is_file() and not p.name.startswith('audit-verification')},
    }
    with output_path.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(json.dumps({'status': 'pass', 'local_links_checked': link_count, 'cohorts': cohorts}))


if __name__ == '__main__':
    main()
