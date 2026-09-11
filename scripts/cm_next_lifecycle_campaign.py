"""Real pipe consumption, bounded concurrent lifetimes, and inert structural reload."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import gc
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from cm_exprlib import Var, Xor, And, Or
from cm_expr_serde import expr_to_json_dag, expr_from_json
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import PackedStreamPlan, IndependentCountPlan
from cmbench.backends.packed_stream_io import write_packed_stream
from cmbench.backends.projected_counts import ProjectedCNFCountPlan
from cmbench.backends.affine_constraints import AffineConstraintPlan
from scripts.cm_next_count_campaign import write


def tree(nodes, op):
    while len(nodes) > 1:
        nodes = [op(nodes[i],nodes[i+1]) if i+1 < len(nodes) else nodes[i] for i in range(0,len(nodes),2)]
    return nodes[0]


def memory():
    return {k:int(v.split()[0])*1024 for line in Path('/proc/self/status').read_text().splitlines()
            for k,_,v in [line.partition(':')] if k in ('VmHWM','VmRSS','VmPeak')}


def parity_hash(n, byte_count):
    """Independent tiled assignment-index parity; no CM execution or mask helper."""
    import numpy as np
    digest = hashlib.sha256()
    for start in range(0,byte_count*8,1 << 16):
        indexes = np.arange(start,min(byte_count*8,start+(1 << 16)),dtype=np.uint32)
        truth = np.zeros(indexes.size,dtype=np.uint8)
        for i in range(n): truth ^= ((indexes >> i) & 1).astype(np.uint8)
        digest.update(np.packbits(truth,bitorder='little').tobytes())
    return digest.hexdigest()


def consumer(delay):
    digest = hashlib.sha256(); count = 0; first = None
    while True:
        chunk = sys.stdin.buffer.read1(4096)
        if not chunk: break
        if first is None: first = time.perf_counter_ns()
        digest.update(chunk); count += len(chunk)
        if delay: time.sleep(delay)
    print(json.dumps(dict(bytes=count,sha256=digest.hexdigest(),first_read_ns=first,
                         completed_ns=time.perf_counter_ns(),memory=memory())),flush=True)


class Sink:
    def __init__(self, raw): self.raw,self.first,self.bytes = raw,None,0
    def write(self, data):
        result = self.raw.write(data)
        if result:
            if self.first is None: self.first = time.perf_counter_ns()
            self.bytes += result
        return result


def pipe_worker(n, width, delay, cancel):
    before = memory(); start = time.perf_counter_ns()
    cache = PackedMaskCache(max_bytes=64 << 20,max_width=24)
    plan = PackedStreamPlan.from_expr(tree([Var(i) for i in range(n)],Xor),tuple(f'x{i}' for i in range(n)),cache=cache)
    child = subprocess.Popen([sys.executable,'-B','-m','scripts.cm_next_lifecycle_campaign','consumer',
                              '--delay',str(delay)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,bufsize=0)
    try:
        sink = Sink(child.stdin)
        receipt = write_packed_stream(plan,sink,chunk_vars=width,max_total_bits=1 << n,
                                     cancelled=lambda:cancel and sink.bytes >= 4*(1 << width)//8)
        producer_ns = time.perf_counter_ns()-start
        child.stdin.close(); child.stdin = None
        stdout,stderr = child.communicate(timeout=30)
        assert child.returncode == 0, stderr.decode(errors='replace')
        consumed = json.loads(stdout)
        assert consumed['bytes'] == receipt.written_bytes and consumed['sha256'] == receipt.sha256
        observed = memory(); cache_stats = cache.stats()
        del plan; cache.clear(); gc.collect()
        total_ns = time.perf_counter_ns()-start
        return dict(n=n,width=width,delay_s=delay,cancel=cancel,receipt=asdict(receipt),consumer=consumed,
                    first_accepted_ns=sink.first-start,first_consumed_ns=consumed['first_read_ns']-start,
                    producer_ns=producer_ns,total_ns=total_ns,memory_before=before,memory_after=observed,
                    memory_after_release=memory(),cache_stats=cache_stats,
                    producer_consumer_peak_rss_sum_upper_bytes=observed['VmHWM']+consumed['memory']['VmHWM'])
    finally:
        if child.poll() is None: child.kill(); child.wait(timeout=10)


def pipes(output):
    output.mkdir(parents=True,exist_ok=False)
    schedule = [dict(n=n,width=w,delay=delay,cancel=cancel,repeat=r) for n in (22,24)
                for delay in (0,.0005) for cancel in (False,True) for r in range(9)
                for w in ((12,16,18,n) if r % 2 == 0 else (n,18,16,12))]
    write(output/'SCHEDULE.json',schedule)
    hashes = {(n,b):parity_hash(n,b) for n in (22,24)
              for b in {(1 << n)//8,*(4*(1 << w)//8 for w in (12,16,18))}}
    rows = []
    with (output/'RAW.jsonl').open('x') as stream:
        for cell in schedule:
            start = time.perf_counter_ns()
            run = subprocess.run([sys.executable,'-B','-m','scripts.cm_next_lifecycle_campaign','pipe-worker',
                    '--n',str(cell['n']),'--width',str(cell['width']),'--delay',str(cell['delay']),
                    *(['--cancel'] if cell['cancel'] else [])],capture_output=True,text=True,check=True,timeout=45)
            row = json.loads(run.stdout); row['repeat'] = cell['repeat']; row['process_lifecycle_ns'] = time.perf_counter_ns()-start
            expected_bytes = min((1 << cell['n'])//8,4*(1 << cell['width'])//8) if cell['cancel'] else (1 << cell['n'])//8
            assert row['receipt']['written_bytes'] == expected_bytes
            assert row['receipt']['sha256'] == hashes[cell['n'],expected_bytes]
            assert row['receipt']['completed'] == (expected_bytes == (1 << cell['n'])//8)
            row['independent_exact'] = True
            rows.append(row); stream.write(json.dumps(row)+'\n'); stream.flush()
    write(output/'RESULT.json',dict(rows=len(rows),exact=True,consumer='separate process through OS pipe',
          memory_metric='sum of independently observed lifetime peak RSS is an upper bound, not simultaneous RSS',
          durability='reader verified every accepted byte; no persistent storage claim'))


def soak(output, seconds=120):
    cache = PackedMaskCache(max_bytes=2 << 20,max_width=20)
    plans = [IndependentCountPlan.from_expr(tree([Var(i) for i in range(n)],Xor),tuple(f'x{i}' for i in range(n)),cache=cache)
             for n in (16,17,18,19,20)]
    retained = [cache.environment(tuple(f'caller{j}x{i}' for i in range(n))) for j in range(2) for n in (16,18,20)]
    start = time.monotonic(); queries = 0; snapshots = []; failures = 0
    def one(index):
        plan = plans[index % len(plans)]
        result = plan.count({plan.basis[0]:index & 1})
        assert result == 1 << (len(plan.basis)-2)
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        while time.monotonic()-start < seconds:
            values = list(pool.map(one,range(32)))
            queries += len(values)
            stats = cache.stats(); assert stats['entry_bytes'] <= stats['max_bytes']
            if len(snapshots) <= (time.monotonic()-start)//5:
                snapshots.append(dict(elapsed_s=time.monotonic()-start,queries=queries,cache=stats,memory=memory(),held_environments=len(retained)))
            if retained and time.monotonic()-start >= seconds/2:
                cache.clear()
                # Caller-held environments must remain valid after eviction/clear.
                assert all(next(iter(env.values())).bit_count() > 0 for env in retained)
                snapshots.append(dict(phase='clear_with_external_references',cache=cache.stats(),memory=memory()))
                retained.clear(); gc.collect()
    before_release = memory(); plans.clear(); cache.clear(); gc.collect()
    write(output,dict(seconds=time.monotonic()-start,queries=queries,threads=4,exact=True,
          snapshots=snapshots,before_release=before_release,after_release=memory(),cache_after=cache.stats(),
          scope='120-second controlled concurrency and pressure soak; allocator RSS need not return to baseline'))


def preparation(output):
    output.mkdir(parents=True,exist_ok=False)
    cases = []
    for family,n in (('projected',48),('projected',96),('affine',128),('affine',512)):
        expr = tree([Or(Var(i),Var(i+1)) for i in range(0,n,2)],And) if family == 'projected' else tree([Var(i) for i in range(n)],Xor)
        path = output/f'{family}-{n}.json'
        started = time.perf_counter_ns()
        payload = json.dumps(expr_to_json_dag(expr),sort_keys=True,separators=(',',':')).encode()
        with path.open('xb') as stream: stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        storage_ns = time.perf_counter_ns()-started
        cases.append((family,n,expr,path,hashlib.sha256(payload).hexdigest(),storage_ns))
    rows = []
    for family,n,expr,path,digest,storage_ns in cases:
        basis = tuple(f'x{i}' for i in range(n)); projected = basis[::2]
        def compile_plan(expression):
            return ProjectedCNFCountPlan.from_expr(expression,basis,projected_names=projected) if family == 'projected' else AffineConstraintPlan.from_expr(expression,basis)
        expected = 1 << (n//2 if family == 'projected' else n-1)
        began = time.perf_counter_ns(); resident = compile_plan(expr)
        resident_setup_ns = time.perf_counter_ns()-began
        for q in (1,32,256):
            for repeat in range(9):
                for method in (('fresh_compile','checked_structural_reload','resident') if repeat % 2 == 0 else ('resident','checked_structural_reload','fresh_compile')):
                    started = time.perf_counter_ns()
                    if method == 'checked_structural_reload':
                        raw = path.read_bytes()
                        assert len(raw) < 1 << 20 and hashlib.sha256(raw).hexdigest() == digest
                        expression = expr_from_json(json.loads(raw))
                        plan = compile_plan(expression)
                    elif method == 'fresh_compile': plan = compile_plan(expr)
                    else: plan = resident
                    prepared = time.perf_counter_ns()
                    answers = [plan.count() for _ in range(q)]
                    queried = time.perf_counter_ns()
                    assert answers == [expected]*q
                    del plan
                    total_ns = time.perf_counter_ns()-started
                    rows.append(dict(family=family,n=n,q=q,repeat=repeat,method=method,
                        setup_ns=prepared-started,query_ns=queried-prepared,total_ns=time.perf_counter_ns()-started,
                        resident_setup_ns=resident_setup_ns,
                        total_with_initial_setup_ns=total_ns+(resident_setup_ns if method == 'resident' else 0),
                        original_storage_ns=storage_ns,serialized_bytes=path.stat().st_size,exact=True))
        del resident
    write(output/'RAW.json',rows)
    write(output/'RESULT.json',dict(rows=len(rows),exact=True,
          resident_setup_charged_separately=True,
          scope='validated inert expression reload recompiles the plan; resident row excludes original construction; storage cost reported separately'))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=('pipes','pipe-worker','consumer','soak','preparation'))
    parser.add_argument('--output',type=Path); parser.add_argument('--n',type=int); parser.add_argument('--width',type=int)
    parser.add_argument('--delay',type=float,default=0); parser.add_argument('--cancel',action='store_true')
    args=parser.parse_args()
    if args.action == 'consumer': consumer(args.delay)
    elif args.action == 'pipe-worker': print(json.dumps(pipe_worker(args.n,args.width,args.delay,args.cancel)))
    elif args.action == 'pipes': pipes(args.output)
    elif args.action == 'soak': soak(args.output)
    else: preparation(args.output)
