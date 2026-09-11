"""Stronger native GF(2) control on the already selected public corpus.

This is a post-panel diagnostic, not fresh confirmation or a default backend.
Build only on the disposable RunPod host; keep all provenance and failures.
"""
import argparse
import ctypes
import cProfile
import gc
import json
from pathlib import Path
import random
import pstats
import shutil
import statistics
import subprocess
import sys
import tarfile
import time

from scripts import cm_scalar_research_campaign as campaign
from cmbench.backends.affine_constraints import AffineConstraintPlan, parse_alist
from cmbench.backends.packed_queries import _fixed

AUDIT = campaign.AUDIT
BUILD = Path('/workspace/cm-m4ri-build')
SOURCE = BUILD/'m4ri-release-20240729'
LIBRARY = BUILD/'cm_m4ri_control.so'


def build(output):
    output.mkdir(parents=True, exist_ok=False)
    BUILD.mkdir(exist_ok=False)
    metadata = json.loads((AUDIT/'M4RI-UPSTREAM.json').read_text())
    archive = AUDIT/'m4ri-20240729.tar.gz'
    assert archive.stat().st_size == metadata['bytes'] and campaign.sha(archive) == metadata['sha256']
    with tarfile.open(archive) as tar:
        assert sum(m.size for m in tar.getmembers()) < 4 << 20
        tar.extractall(BUILD, filter='data')
    commands = [(['autoreconf', '-fi'], 120),
                (['./configure', '--disable-png', '--disable-openmp', '--disable-static', '--disable-cachetune'], 120),
                (['make', '-j2'], 240), (['make', 'check', '-j2'], 240),
                (['gcc', '-O3', '-fPIC', '-shared', str(campaign.ROOT/'native/cm_scalar_m4ri/control.c'),
                  '-I'+str(SOURCE), '-L'+str(SOURCE/'.libs'), '-Wl,-rpath,'+str(SOURCE/'.libs'),
                  '-lm4ri', '-o', str(LIBRARY)], 60)]
    records = []
    for i, (command, timeout) in enumerate(commands):
        start = time.monotonic()
        with (output/f'build-{i}.log').open('xb') as log:
            result = subprocess.run(command, cwd=SOURCE, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        records.append(dict(command=command, elapsed_s=time.monotonic()-start, exit_code=result.returncode))
        campaign.write(output/f'build-{i}.json', records[-1])
        if result.returncode: raise RuntimeError('M4RI build stage '+str(i)+' failed')
    shutil.copyfile(SOURCE/'COPYING', output/'M4RI-COPYING')
    shutil.copyfile(LIBRARY, output/LIBRARY.name)
    campaign.write(output/'BUILD.json', dict(upstream=metadata, commands=records,
                    library_sha256=campaign.sha(LIBRARY), wrapper_sha256=campaign.sha(campaign.ROOT/'native/cm_scalar_m4ri/control.c'),
                    compiler=subprocess.check_output(['gcc', '--version'], text=True),
                    shared_library_sha256=campaign.sha(SOURCE/'.libs/libm4ri.so')))


class M4riControl:
    def __init__(self, rows, rhs, basis):
        self.plan = AffineConstraintPlan(rows, rhs, basis)
        self.library = ctypes.CDLL(str(LIBRARY))
        self.rank_function = self.library.cm_m4ri_rank
        self.rank_function.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int]
        self.rank_function.restype = ctypes.c_int
        self.positions = {n: i for i, n in enumerate(basis)}

    def rank(self, rows, width):
        data = b''.join(row.to_bytes((width+7)//8, 'little') for row in rows)
        buffer = ctypes.create_string_buffer(data)
        rank = self.rank_function(buffer, len(data), len(rows), width)
        if rank < 0: raise ValueError('native rank refused input')
        return rank

    def count(self, fixed=None):
        context = _fixed(self.plan.basis, fixed)
        mask = sum(1 << self.positions[n] for n in context)
        ones = sum(1 << self.positions[n] for n, v in context.items() if v)
        rows = [r & ~mask for r in self.plan.rows]
        rhs = [b ^ ((r & ones).bit_count() & 1) for r, b in zip(self.plan.rows, self.plan.rhs)]
        n = len(self.plan.basis)
        rank = self.rank(rows, n)
        if any(rhs) and self.rank([r | (b << n) for r, b in zip(rows, rhs)], n+1) != rank: return 0
        return 1 << (n-len(context)-rank)


def correctness(output):
    rng = random.Random(campaign.SEED+77)
    checked = 0
    for n in (0, 1, 2, 6, 8, 63, 64, 65, 127, 128, 129, 512):
        basis = tuple(f'x{i}' for i in range(n))
        for _ in range(12):
            rows = [rng.getrandbits(n) for _ in range(rng.randrange(16))]
            rhs = [rng.randrange(2) for _ in rows]
            native, packed = M4riControl(rows, rhs, basis), AffineConstraintPlan(rows, rhs, basis)
            for count in (0, n//2, n):
                fixed = {basis[i]: rng.randrange(2) for i in rng.sample(range(n), count)}
                assert native.count(fixed) == packed.count(fixed)
                if n <= 8:
                    expected = sum(all((x & row).bit_count() % 2 == b for row, b in zip(rows, rhs))
                        for x in range(1 << n) if all((x >> i & 1) == fixed[name] for i, name in enumerate(basis) if name in fixed))
                    assert native.count(fixed) == expected
                checked += 1
    # ABI length and high padding refusal must not read beyond the supplied bytes.
    native = M4riControl([], [], ())
    buf = ctypes.create_string_buffer(b'\x80')
    assert native.rank_function(buf, 0, 1, 1) == -1
    assert native.rank_function(buf, 1, 1, 1) == -1
    assert native.rank_function(buf, 1, -1, 1) == -1
    campaign.write(output/'NATIVE-CORRECTNESS.json', dict(random_contexts=checked, abi_guards=3, exact=True))


def session(case, method, q, warm=True):
    if method != 'm4ri': return campaign.session(case, method, q, warm=warm)
    start = time.perf_counter_ns()
    n, rows = parse_alist(case['alist'])
    runner = M4riControl(rows, [0]*len(rows), tuple(f'x{i}' for i in range(n)))
    contexts = campaign.queries(case, q)
    setup = time.perf_counter_ns()-start
    start = time.perf_counter_ns()
    result = json.dumps([runner.count(c) for c in contexts], separators=(',', ':'))
    query = time.perf_counter_ns()-start
    warm_ns = None
    if warm:
        start = time.perf_counter_ns()
        again = json.dumps([runner.count(c) for c in contexts], separators=(',', ':'))
        warm_ns = time.perf_counter_ns()-start
        assert result == again
    start = time.perf_counter_ns(); del runner
    cleanup = time.perf_counter_ns()-start
    return dict(result=result, total_ns=setup+query+cleanup, setup_ns=setup, query_ns=query, cleanup_ns=cleanup, warm_ns=warm_ns)


def run(output):
    correctness(output)
    cases = [c for c in json.loads((AUDIT/'FIXTURES.json').read_text()) if c['task'] == 'affine']
    schedule = [dict(case=c['id'], q=q, repeat=r, method=m) for c in cases for q in (1, 8)
                for r in range(9) for m in (('affine_rows', 'flint', 'm4ri') if r % 2 == 0 else ('m4ri', 'flint', 'affine_rows'))]
    campaign.write(output/'FREEZE.json', dict(schedule=schedule, fixtures_sha256=campaign.sha(AUDIT/'FIXTURES.json'),
                                             scope='stronger native control; already consumed public corpus; no tuned inputs'))
    indexed = {c['id']: c for c in cases}
    expected = {(c['id'], q): session(c, 'flint', q)['result'] for c in cases for q in (1, 8)}
    rows = []
    with (output/'RAW.jsonl').open('x') as stream:
        for cell in schedule:
            gc.collect()
            row = dict(cell, **session(indexed[cell['case']], cell['method'], cell['q']))
            assert row['result'] == expected[(cell['case'], cell['q'])]
            row['exact'] = True
            stream.write(json.dumps(row)+'\n'); stream.flush(); rows.append(row)
    campaign.write(output/'SUMMARY.json', campaign.summarize(rows))
    largest = cases[-1]
    memory = []
    for r in range(3):
        for m in ('affine_rows', 'flint', 'm4ri'):
            start = time.perf_counter_ns()
            child = subprocess.run([sys.executable, '-B', '-m', 'scripts.cm_scalar_m4ri_control', 'worker', '--method', m],
                                   capture_output=True, text=True, check=True, timeout=90)
            record = dict(method=m, repeat=r, lifecycle_ns=time.perf_counter_ns()-start, **json.loads(child.stdout))
            assert record['result'] == expected[(largest['id'], 1)]
            memory.append(record)
    campaign.write(output/'MEMORY.json', memory)
    profiles = []
    for method in ('affine_rows', 'flint', 'm4ri'):
        profile = cProfile.Profile()
        profile.enable(); session(largest, method, 8, warm=False); profile.disable()
        stats = pstats.Stats(profile)
        profiles.append(dict(method=method, total_s=stats.total_tt, functions=[
            dict(file=k[0], line=k[1], function=k[2], calls=v[1], self_s=v[2], cumulative_s=v[3])
            for k, v in sorted(stats.stats.items(), key=lambda kv: kv[1][3], reverse=True)[:30]]))
    campaign.write(output/'PROFILES.json', profiles)
    reread = [json.loads(line) for line in (output/'RAW.jsonl').read_text().splitlines()]
    assert [{k: r[k] for k in ('case', 'q', 'repeat', 'method')} for r in reread] == schedule
    assert all(r['result'] == expected[(r['case'], r['q'])] for r in reread)
    assert campaign.summarize(reread) == json.loads((output/'SUMMARY.json').read_text())
    campaign.write(output/'RESULT.json', dict(cells=len(rows), asserted_outputs=2*sum(r['q'] for r in rows),
                                             memory_children=len(memory), exact=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'run', 'worker'))
    parser.add_argument('--output', type=Path); parser.add_argument('--method')
    args = parser.parse_args()
    if args.action == 'build': build(args.output)
    elif args.action == 'run': run(args.output)
    else:
        case = [c for c in json.loads((AUDIT/'FIXTURES.json').read_text()) if c['task'] == 'affine'][-1]
        before = campaign.process_memory()
        row = session(case, args.method, 1, warm=False)
        print(json.dumps(dict(before=before, after=campaign.process_memory(), **row)))


if __name__ == '__main__': main()
