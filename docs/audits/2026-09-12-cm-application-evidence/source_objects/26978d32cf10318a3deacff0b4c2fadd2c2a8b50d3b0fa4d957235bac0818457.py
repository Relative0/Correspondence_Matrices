"""Pinned independent integer-projection controls and unchanged QIF contexts."""
from __future__ import annotations

import argparse
import hashlib
import io
from itertools import product
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import subprocess
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs/audits/2026-09-12-cm-application-evidence'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')


def dimacs(case, fixed):
    """Translate zero-based caller names to explicit one-based CNF projection."""
    n = case['n']
    units = []
    for name, value in fixed.items():
        if not re.fullmatch(r'x[0-9]+', name) or type(value) not in (int, bool) or value not in (0, 1):
            raise ValueError('invalid fixed assignment')
        i = int(name[1:])
        if not 0 <= i < n: raise ValueError('fixed variable outside basis')
        units.append([i + 1 if value else -i - 1])
    selected = case['projected']
    if len(set(selected)) != len(selected) or any(type(v) is not int or not 0 <= v < n for v in selected):
        raise ValueError('invalid projection')
    clauses = [*case['clauses'], *units]
    if any(type(lit) is not int or not 1 <= abs(lit) <= n for c in clauses for lit in c):
        raise ValueError('invalid clause')
    lines = ['c t pmc', f'p cnf {n} {len(clauses)}', 'c p show ' + ' '.join(str(v+1) for v in selected) + ' 0']
    lines += [' '.join(map(str, c)) + ' 0' for c in clauses]
    return ('\n'.join(lines) + '\n').encode()


def exhaustive(case, fixed):
    answers = set()
    for values in product((0, 1), repeat=case['n']):
        if any(values[int(k[1:])] != v for k, v in fixed.items()): continue
        if all(any(values[abs(l)-1] == (l > 0) for l in clause) for clause in case['clauses']):
            answers.add(tuple(values[i] for i in case['projected']))
    return len(answers)


def install(output):
    record = json.loads((AUDIT / 'ORACLE-PROTOCOL.json').read_text())['release']
    with urllib.request.urlopen(record['url'], timeout=120) as response:
        payload = response.read(record['bytes'] + 1)
    assert len(payload) == record['bytes'] and hashlib.sha256(payload).hexdigest() == record['sha256']
    destination = ROOT / 'build/application-ganak'; destination.mkdir(parents=True, exist_ok=False)
    members = []
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        assert sum(x.size for x in archive.getmembers()) < 256 << 20
        for item in archive:
            name = PurePosixPath(item.name)
            if name.is_absolute() or '..' in name.parts or ':' in item.name: raise ValueError('unsafe release member')
            if item.isdir(): continue
            if not item.isfile(): raise ValueError('nonregular release member')
            path = destination / name; path.parent.mkdir(parents=True, exist_ok=True)
            data = archive.extractfile(item).read()
            with path.open('xb') as stream: stream.write(data)
            if item.mode & 0o111: path.chmod(0o755)
            members.append(dict(path=name.as_posix(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    candidates = [destination / x['path'] for x in members if PurePosixPath(x['path']).name == 'ganak']
    assert len(candidates) == 1
    binary = candidates[0]; binary.chmod(0o755)
    help_result = subprocess.run([str(binary), '--help'], capture_output=True, timeout=20)
    (output / 'GANAK-HELP.log').write_bytes(help_result.stdout + help_result.stderr)
    assert b'--prob' in help_result.stdout + help_result.stderr
    write(output / 'ORACLE-INSTALL.json', dict(release=record, members=members, binary=str(binary.relative_to(ROOT))))
    return binary


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def count(binary, case, fixed, output, key, timeout=60):
    path = output / (key + '.cnf'); payload = dimacs(case, fixed); path.write_bytes(payload)
    command = [str(binary), '--prob', '0', '--mode', '0', '--fast', str(path)]
    start = time.perf_counter_ns()
    result = dict(case=case['id'], context=fixed, input_sha256=hashlib.sha256(payload).hexdigest(),
                  command=command, deterministic=True, limit_s=timeout)
    try:
        child = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=timeout, preexec_fn=limits)
        (output / (key + '.log')).write_bytes(child.stdout)
        text = child.stdout.decode(errors='replace')
        # Ganak's competition-format integer output must be present exactly once.
        matches = re.findall(r'^c s exact arb int ([0-9]+)\s*$', text, re.M)
        result.update(exit_code=child.returncode, status='complete' if child.returncode in (0, 10, 20) and len(matches)==1 else 'failed')
        if result['status'] == 'complete': result['value'] = int(matches[0])
    except subprocess.TimeoutExpired as exc:
        (output / (key + '.log')).write_bytes(exc.stdout or b'')
        result['status'] = 'timeout'
    result['elapsed_ns'] = time.perf_counter_ns() - start
    write(output / (key + '.json'), result)
    return result


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    binary = install(output)
    controls = json.loads((AUDIT / 'ORACLE-PROTOCOL.json').read_text())['controls']
    rows = []
    for i, case in enumerate(controls):
        for j, fixed in enumerate(case['contexts']):
            row = count(binary, case, fixed, output, f'control-{i}-{j}', 15)
            row['expected'] = exhaustive(case, fixed)
            rows.append(row)
    write(output / 'CONTROL-RESULTS.json', rows)
    assert all(r['status']=='complete' and r['value']==r['expected'] for r in rows), 'independent oracle contract control failed'
    cases = json.loads((ROOT / 'docs/audits/2026-09-12-cm-evidence-frontiers/INDEPENDENT-CASES.json').read_text())
    results = []
    for case in cases:
        if case['id'] not in ('independent-01', 'independent-02'): continue
        for i, fixed in enumerate(case['contexts']):
            row = count(binary, case, fixed, output, case['id'] + '-' + str(i))
            results.append(row)
            print(json.dumps({k:v for k,v in row.items() if k not in ('command','context')}), flush=True)
    write(output / 'QIF-RESULTS.json', results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
