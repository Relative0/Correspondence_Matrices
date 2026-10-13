"""Frozen Linux residual-CNF complete-vector lifecycle benchmark.

This successor never changes historical validators. Source selection and timing
contracts are recorded in PROTOCOL.json before a benchmark process is started.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ARMS = ('cm', 'cse', 'cnf', 'cudd_fixed', 'cudd_sift')


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    with Path(path).open('xb') as stream:
        stream.write(encoded(value) + b'\n')


def columns(k):
    full = (1 << (1 << k)) - 1
    return full, tuple((full // ((1 << (1 << v)) + 1)) << (1 << v) for v in range(k))


def scalar(case):
    # Independent assignment-by-assignment oracle, outside every timed cell.
    output = bytearray((1 << case['k']) // 8)
    for a in range(1 << case['k']):
        if all(any(bool(a & (1 << (abs(lit)-1))) == (lit > 0) for lit in c)
               for c in case['clauses']):
            output[a // 8] |= 1 << (a % 8)
    return int.from_bytes(output, 'little')


def graph(manager, root, k):
    nodes, memo = [], {}
    def visit(u):
        if u == manager.false: return -1
        if u == manager.true: return -2
        if u in memo: return memo[u]
        if u.negated:
            level, low, high = manager.succ(~u)
            low, high = ~low, ~high
        else:
            level, low, high = manager.succ(u)
        lo, hi = visit(low), visit(high)
        index = len(nodes)
        nodes.append([manager.var_at_level(level), lo, hi])
        memo[u] = index
        return index
    try:
        root_ref = visit(root)
    finally:
        # Recursive closures retain themselves and their CUDD Function keys.
        # Release references before the manager, rather than at interpreter exit.
        memo.clear()
        visit = None
    return {'nodes': nodes, 'root': root_ref,
            'order': [manager.var_at_level(i) for i in range(k)]}


def graph_value(data, k):
    full, pats = columns(k)
    values = {-1: 0, -2: full}
    for index, (name, low, high) in enumerate(data['nodes']):
        pat = pats[int(name[1:])]
        values[index] = (values[low] & (full ^ pat)) | (values[high] & pat)
    return values[data['root']]


class Engine:
    def __init__(self, arm, case, bundle=None):
        self.arm, self.k, self.clauses = arm, case['k'], case['clauses']
        self.pats = None
        self.configuration = None
        self.program = self.manager = self.root = None
        if arm in ('cm', 'cse'):
            from bitset_backend import FlatProgram, compile_expr_cse, get_flat_program
            if bundle is None:
                from scripts.cm_measurement_verify import _expression
                expr = _expression(self.clauses)
                if arm == 'cm':
                    from cm_ir import compile_expr_to_cm_ir
                    self.program = get_flat_program(compile_expr_to_cm_ir(
                        expr, reuse_cache=False, persistent_cache=False))
                else:
                    self.program = compile_expr_cse(expr, flatten=True)
            else:
                p = bundle['structure']
                self.program = FlatProgram(p['n_slots'], p['root_slot'],
                    tuple(tuple(r) for r in p['loads']),
                    tuple((slot, op, tuple(args)) for slot, op, args in p['ops']))
        elif arm.startswith('cudd'):
            from dd import cudd
            self.manager = m = cudd.BDD(memory_estimate=64 << 20)
            m.configure(reordering=False)
            if bundle is not None:
                data = bundle['structure']
                m.declare(*data['order'])
                resolved = {-1:m.false, -2:m.true}
                for index, (name, low, high) in enumerate(data['nodes']):
                    resolved[index] = m.ite(m.var(name), resolved[high], resolved[low])
                self.root = resolved[data['root']]
            else:
                m.declare(*(f'x{i}' for i in range(self.k)))
                m.configure(reordering=(arm == 'cudd_sift'))
                self.root = m.true
                for clause in self.clauses:
                    term = m.false
                    for lit in clause:
                        u = m.var(f'x{abs(lit)-1}')
                        term |= u if lit > 0 else ~u
                    self.root &= term
                if arm == 'cudd_sift':
                    cudd.reorder(m)  # Mandatory charged sifting, even on tiny graphs.
                m.configure(reordering=False)  # Freeze final order for queries/export.
            self.configuration = m.configure()
        elif bundle is not None:
            self.clauses = bundle['structure']['clauses']

    def evaluate(self):
        if self.arm in ('cm', 'cse'):
            from scripts.cm_measurement_verify import execute_flat
            return execute_flat(self.program, self.k)
        if self.pats is None: self.pats = columns(self.k)
        full, pats = self.pats
        if self.arm == 'cnf':
            result = full
            for clause in self.clauses:
                term = 0
                for lit in clause:
                    pat = pats[abs(lit)-1]
                    term |= pat if lit > 0 else full ^ pat
                result &= term
            return result
        m, memo = self.manager, {}
        def visit(u):
            if u == m.true: return full
            if u == m.false: return 0
            if u in memo: return memo[u]
            if u.negated: value = full ^ visit(~u)
            else:
                level, lo, hi = m.succ(u)
                pat = pats[int(m.var_at_level(level)[1:])]
                value = (visit(lo) & (full ^ pat)) | (visit(hi) & pat)
            memo[u] = value
            return value
        try:
            return visit(self.root)
        finally:
            memo.clear()
            visit = None

    def close(self):
        self.root = None
        self.manager = None
        self.program = None
        self.pats = None

    def bundle(self):
        if self.arm in ('cm', 'cse'):
            p = self.program
            structure = dict(n_slots=p.n_slots, root_slot=p.root_slot, loads=p.loads, ops=p.ops)
        elif self.arm == 'cnf': structure = {'clauses': self.clauses}
        else: structure = graph(self.manager, self.root, self.k)
        return {'schema':'cm-fair-fm-structure/v1', 'arm':self.arm, 'k':self.k,
                'variable_universe':[f'x{i}' for i in range(self.k)], 'structure':structure}


def worker(request_path):
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    resource.setrlimit(resource.RLIMIT_CPU, (15, 16))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 << 20, 16 << 20))
    baseline = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    start = time.perf_counter_ns()
    request = json.loads(Path(request_path).read_bytes())
    case = json.loads(Path(request['case_path']).read_bytes())
    parsed = time.perf_counter_ns()
    bundle = None
    if request['mode'] == 'reload':
        raw = Path(request['artifact']).read_bytes()
        assert sha(raw) == request['artifact_sha256']
        bundle = json.loads(raw)
        assert bundle['arm'] == request['arm'] and bundle['k'] == case['k']
    read = time.perf_counter_ns()
    engine = Engine(request['arm'], case, bundle)
    constructed = time.perf_counter_ns()
    first = engine.evaluate()
    first_bytes = first.to_bytes((1 << case['k']) // 8, 'little')
    queried = time.perf_counter_ns()
    warm = []
    for _ in range(5):
        stamp = time.perf_counter_ns()
        value = engine.evaluate().to_bytes(len(first_bytes), 'little')
        warm.append(time.perf_counter_ns() - stamp)
        assert value == first_bytes
    serialized_ns = None
    artifact = None
    if request['mode'] == 'build':
        stamp = time.perf_counter_ns()
        artifact = engine.bundle()
        raw = encoded(artifact)
        with Path(request['artifact']).open('xb') as stream: stream.write(raw)
        serialized_ns = time.perf_counter_ns() - stamp
    result = dict(pid=os.getpid(), mode=request['mode'], arm=request['arm'],
        case_id=case['id'], result_sha256=sha(first_bytes),
        output_bytes=len(first_bytes), parse_ns=parsed-start, artifact_read_ns=read-parsed,
        construct_ns=constructed-read, first_query_ns=queried-constructed,
        cold_total_ns=queried-start, warm_ns=warm, serialize_ns=serialized_ns,
        artifact_sha256=sha(raw) if raw is not None else None,
        artifact_bytes=len(raw), configuration=engine.configuration,
        rss_baseline_kib=baseline, rss_highwater_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    cleanup_started = time.perf_counter_ns()
    engine.close()
    result['cleanup_ns'] = time.perf_counter_ns() - cleanup_started
    write(request['result_path'], result)


def run(output, protocol_path):
    import platform
    protocol = json.loads(protocol_path.read_bytes())
    output.mkdir(exist_ok=False)
    (output/'cells').mkdir()
    write(output/'host.json', dict(platform=platform.platform(), python=sys.version,
        cpuinfo=Path('/proc/cpuinfo').read_text(), affinity=sorted(os.sched_getaffinity(0))))
    for file in protocol['files']:
        assert sha((ROOT/file['path']).read_bytes()) == file['sha256'], file['path']
    started = time.monotonic()
    case_by_id = {case['id']:case for case in protocol['cases']}
    oracle = {}
    for case in protocol['cases']:
        value = scalar(case)
        raw = value.to_bytes((1 << case['k']) // 8, 'little')
        oracle[case['id']] = sha(raw)
    write(output/'oracles.json', oracle)
    rows = []
    for index, cell in enumerate(protocol['schedule']):
        folder = output/'cells'/f'{index:04d}'
        folder.mkdir()
        case = case_by_id[cell['case_id']]
        write(folder/'case.json', case)
        record = dict(cell, index=index, status='ok', processes=[])
        for mode in ('build', 'reload'):
            if time.monotonic()-started > protocol['campaign_seconds']:
                record['status'] = 'campaign_limit'; break
            request = dict(case_path=str(folder/'case.json'), arm=cell['arm'], mode=mode,
                artifact=str(folder/'artifact.json'), result_path=str(folder/(mode+'.json')))
            if mode == 'reload': request['artifact_sha256'] = sha((folder/'artifact.json').read_bytes())
            write(folder/(mode+'-request.json'), request)
            before = time.perf_counter_ns()
            with (folder/(mode+'.log')).open('xb') as log:
                proc = subprocess.Popen([sys.executable, '-X', 'utf8', '-B', str(Path(__file__)),
                    'worker', '--request', str(folder/(mode+'-request.json'))],
                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                timed_out = False
                try: code = proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    timed_out=True
                    os.killpg(proc.pid, signal.SIGKILL)
                    code=proc.wait(timeout=5)
            parent_wall_ns = time.perf_counter_ns()-before
            record['processes'].append(dict(mode=mode, pid=proc.pid, exit_code=code,
                timed_out=timed_out, parent_wall_ns=parent_wall_ns))
            if code:
                record['status']='timeout' if timed_out else 'worker_error'; break
            result = json.loads((folder/(mode+'.json')).read_bytes())
            assert result['pid'] == proc.pid
            if result['result_sha256'] != oracle[case['id']]:
                record['status']='mismatch'; break
        if record['status']=='ok':
            assert record['processes'][0]['pid'] != record['processes'][1]['pid']
        rows.append(record)
        with (output/'ledger.jsonl').open('ab') as ledger: ledger.write(encoded(record)+b'\n')
        if index % 25 == 0: print(json.dumps(dict(completed=index+1,total=len(protocol['schedule']))),flush=True)
    write(output/'summary.json', dict(cells=len(rows), status_counts={s:sum(r['status']==s for r in rows)
        for s in sorted({r['status'] for r in rows})}, elapsed_s=time.monotonic()-started))
    for file in protocol['files']:
        assert sha((ROOT/file['path']).read_bytes()) == file['sha256'], file['path']


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['worker','run'])
    parser.add_argument('--request',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--protocol',type=Path)
    args=parser.parse_args()
    if args.action=='worker': worker(args.request)
    else: run(args.output,args.protocol)


if __name__=='__main__': main()
