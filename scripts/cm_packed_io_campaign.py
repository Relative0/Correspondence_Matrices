"""Prospective larger synthetic queries and real file sinks, for remote execution."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import resource
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc

import numpy as np

import bitset_backend as bs
from cm_expr_serde import expr_from_json
from cm_ir import compile_expr_to_cm_ir
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import IndependentCountPlan, PackedStreamPlan
from cmbench.backends.packed_stream_io import write_packed_stream
from scripts import cm_packed_queries_campaign as prior

SEED = 202609119301
REPEATS = 9


def fixtures():
    cases = []
    for n in (22, 24):
        for entangled in (False, True):
            cases.append(dict(id=f'count-n{n}-entangled{int(entangled)}', task='count', n=n,
                              entangled=entangled,
                              document=prior.count_fixture(n, 4, SEED + n, entangled)))
        cases.append(dict(id=f'file-n{n}', task='file', n=n,
                          document=prior.stream_fixture(n, SEED + 100 + n)))
    return cases


def methods(case):
    return (('cse_flat', 'independent_expr', 'independent_cm', 'bdd_cudd')
            if case['task'] == 'count' else
            ('complete', 'positional_full', 'stream_12', 'stream_16', 'stream_18'))


def contexts(case, q):
    return [{}] if q == 1 else [{f'x{(i + 3*j) % case["n"]}': (i >> j) & 1
                                for j in range(2)} for i in range(q)]


def freeze(output):
    output.mkdir(parents=True, exist_ok=False)
    cases = fixtures()
    schedule = []
    for case in cases:
        for q in (1, 8):
            for repeat in range(REPEATS):
                arms = methods(case)
                for method in (arms if repeat % 2 == 0 else arms[::-1]):
                    schedule.append(dict(case=case['id'], q=q, repeat=repeat, method=method))
    prior.write(output / 'FIXTURES.json', cases)
    prior.write(output / 'FREEZE.json', dict(
        schema='cm-packed-file-campaign/v1', seed=SEED, repeats=REPEATS,
        fixtures_sha256=prior.sha(output / 'FIXTURES.json'), schedule=schedule,
        script_sha256=prior.sha(Path(__file__)),
        scope='Prospective synthetic extrapolation; real file consumer, no deployed trace.',
        cache_bytes=64 << 20, fixed_chunks=[12, 16, 18],
        timed='JSON disk ingress, compile, count or file open/write/hash/flush/fsync/close, cleanup',
        untimed='oracle, file reread, garbage collection, separate allocation runs',
    ))


def oracle(case, context):
    """Independent NumPy truth interpretation; no CM, flat executor or packed masks.

    2**16 rows per tile bounds the verifier even at n24. Hash follows the complete
    output order, with arrays built directly from assignment indexes.
    """
    live = [f'x{i}' for i in range(case['n']) if f'x{i}' not in context]
    total = 1 << len(live)
    digest = hashlib.sha256()
    count = 0
    for start in range(0, total, 1 << 16):
        indexes = np.arange(start, min(total, start + (1 << 16)), dtype=np.uint32)
        env = {name: ((indexes >> (len(live) - axis - 1)) & 1).astype(bool)
               for axis, name in enumerate(live)}
        env.update({name: np.full(indexes.size, bool(value)) for name, value in context.items()})
        values = []
        for node in case['document']['nodes']:
            op = node['op']
            if op == 'var': value = env[f'x{node["i"]}']
            elif op == 'not': value = np.logical_not(values[node['a']])
            else:
                a, b = values[node['a']], values[node['b']]
                if op == 'and': value = np.logical_and(a, b)
                elif op == 'or': value = np.logical_or(a, b)
                elif op == 'xor': value = np.logical_xor(a, b)
                elif op == 'eqv': value = np.equal(a, b)
                elif op == 'imp': value = np.logical_or(np.logical_not(a), b)
                else: raise ValueError(op)
            values.append(value)
        truth = values[case['document']['root']]
        count += int(np.count_nonzero(truth))
        digest.update(np.packbits(truth, bitorder='little').tobytes())
    return dict(count=count, sha256=digest.hexdigest(), bytes=(total + 7) // 8)


def cudd(document, basis):
    from dd.cudd import BDD
    manager = BDD()
    manager.configure(reordering=False)
    manager.declare(*basis)
    values = []
    for node in document['nodes']:
        op = node['op']
        if op == 'var': value = manager.var(f'x{node["i"]}')
        elif op == 'not': value = ~values[node['a']]
        else:
            a, b = values[node['a']], values[node['b']]
            if op == 'and': value = a & b
            elif op == 'or': value = a | b
            elif op == 'xor': value = manager.apply('xor', a, b)
            elif op == 'eqv': value = ~manager.apply('xor', a, b)
            elif op == 'imp': value = ~a | b
            else: raise ValueError(op)
        values.append(value)
    root = values[document['root']]
    return lambda context: int(manager.count(manager.let({k: bool(v) for k, v in context.items()}, root),
                                             nvars=len(basis) - len(context)))


def make_runner(case, method, pool, document):
    basis = tuple(f'x{i}' for i in range(case['n']))
    if method == 'bdd_cudd': return cudd(document, basis)
    expr = expr_from_json(document)
    if method == 'independent_expr':
        return IndependentCountPlan.from_expr(expr, basis, cache=pool).count
    if method == 'independent_cm':
        return IndependentCountPlan.from_cm_node(compile_expr_to_cm_ir(expr), basis, cache=pool).count
    if method.startswith('stream_') or method == 'positional_full':
        return PackedStreamPlan.from_expr(expr, basis, cache=pool)
    bs.get_expr_cse_program(expr, flatten=True)
    return lambda context: bs.eval_expr_flat_cse(expr, tuple(n for n in basis if n not in context),
                                               fixed=context, flatten=True)


class FirstWrite:
    def __init__(self, sink):
        self.sink = sink
        self.first_ns = None
    def write(self, data):
        n = self.sink.write(data)
        if self.first_ns is None: self.first_ns = time.perf_counter_ns()
        return n


def consume(case, method, runner, requests, directory, prefix):
    results, files = [], []
    first = None
    for index, context in enumerate(requests):
        if case['task'] == 'count':
            value = runner(context)
            results.append(value.bit_count() if method == 'cse_flat' else value)
            continue
        path = directory / f'{prefix}-{index}.bin'
        with path.open('xb', buffering=65536) as raw:
            sink = FirstWrite(raw)
            if method == 'complete':
                bits = runner(context)
                data = bits.to_bytes((1 << (case['n'] - len(context))) // 8, 'little')
                accepted = sink.write(data)
                if accepted != len(data): raise OSError('short buffered control write')
                value = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
            else:
                width = case['n'] if method == 'positional_full' else int(method.split('_')[1])
                receipt = write_packed_stream(runner, sink, chunk_vars=width,
                                              max_total_bits=1 << case['n'], fixed=context)
                assert receipt.completed
                value = dict(sha256=receipt.sha256, bytes=receipt.written_bytes)
            raw.flush()
            os.fsync(raw.fileno())
            if first is None: first = sink.first_ns
        results.append(value)
        files.append(path)
    return results, first, files


def session(case, method, q, fixture_file, directory, *, warm=True):
    started = time.perf_counter_ns()
    pool = PackedMaskCache(max_bytes=64 << 20, max_width=24)
    document = json.loads(fixture_file.read_text())
    runner = make_runner(case, method, pool, document)
    requests = contexts(case, q)
    setup = time.perf_counter_ns() - started
    start = time.perf_counter_ns()
    result, first, files = consume(case, method, runner, requests, directory, 'cold')
    query = time.perf_counter_ns() - start
    warm_ns = 0
    if warm:
        start = time.perf_counter_ns()
        again, _, warm_files = consume(case, method, runner, requests, directory, 'warm')
        warm_ns = time.perf_counter_ns() - start
        assert again == result
        files.extend(warm_files)
    stats = pool.stats()
    start = time.perf_counter_ns()
    del runner
    pool.clear()
    bs.clear_bitset_env_cache()
    cleanup = time.perf_counter_ns() - start
    return result, files, dict(total_ns=setup + query + cleanup, setup_ns=setup,
                              query_delivery_ns=query, cleanup_ns=cleanup, warm_ns=warm_ns,
                              first_chunk_ns=None if first is None else first - started, cache=stats)


def reread(files, result):
    for i, path in enumerate(files):
        digest = hashlib.sha256()
        size = 0
        with path.open('rb') as stream:
            while block := stream.read(65536):
                digest.update(block)
                size += len(block)
        assert dict(sha256=digest.hexdigest(), bytes=size) == result[i % len(result)]


def run(output):
    frozen = json.loads((output / 'FREEZE.json').read_text())
    assert prior.sha(output / 'FIXTURES.json') == frozen['fixtures_sha256']
    assert prior.sha(Path(__file__)) == frozen['script_sha256']
    cases = {c['id']: c for c in json.loads((output / 'FIXTURES.json').read_text())}
    inputs = output / 'inputs'
    inputs.mkdir()
    targets = {}
    for case in cases.values():
        prior.write(inputs / (case['id'] + '.json'), case['document'])
        for q in (1, 8):
            values = [oracle(case, context) for context in contexts(case, q)]
            targets[case['id'], q] = ([v['count'] for v in values] if case['task'] == 'count' else
                                      [{k: v[k] for k in ('sha256', 'bytes')} for v in values])
    prior.write(output / 'ORACLES.json', [dict(case=k[0], q=k[1], result=v) for k, v in targets.items()])
    print('CM_STAGE io-timing', flush=True)
    rows = []
    with (output / 'RAW.jsonl').open('x') as raw:
        for cell in frozen['schedule']:
            case = cases[cell['case']]
            bs.clear_bitset_env_cache()
            gc.collect()
            with tempfile.TemporaryDirectory(prefix='cm-sink-') as temporary:
                result, files, measures = session(case, cell['method'], cell['q'],
                                                  inputs / (case['id'] + '.json'), Path(temporary))
                assert result == targets[case['id'], cell['q']], cell
                reread(files, result)
            row = dict(cell, **measures, result=result, exact=True, files_replayed=len(files))
            rows.append(row)
            raw.write(json.dumps(row) + '\n')
            raw.flush()
    print('CM_STAGE io-memory', flush=True)
    memory = []
    for case in cases.values():
        for method in methods(case):
            bs.clear_bitset_env_cache()
            gc.collect()
            with tempfile.TemporaryDirectory(prefix='cm-memory-') as temporary:
                tracemalloc.start()
                result, files, measures = session(case, method, 1, inputs / (case['id'] + '.json'),
                                                  Path(temporary), warm=False)
                retained, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                assert result == targets[case['id'], 1]
                reread(files, result)
            memory.append(dict(case=case['id'], method=method, peak_python_bytes=peak,
                               after_session_python_bytes=retained, cache=measures['cache'], exact=True,
                               limitation='tracemalloc excludes native CUDD allocations'))
    prior.write(output / 'MEMORY.json', memory)
    # Use the established paired bootstrap without altering selection thresholds.
    summary_rows = [dict(r, case=r['case'].replace('file-', 'cloud-stream-').replace('count-', 'cloud-count-'))
                    for r in rows]
    prior.write(output / 'SUMMARY.json', prior.summarize(summary_rows))
    prior.write(output / 'HOST.json', dict(python=sys.version, platform=platform.platform(),
                                          machine=platform.machine(), cpu=platform.processor(),
                                          max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                          packages={n: importlib.metadata.version(n) for n in ('numpy', 'dd')},
                                          cpus=os.cpu_count(), vm_allowed=True))
    print('CM_STAGE io-lifecycle', flush=True)
    lifecycle = []
    selected = [c for c in cases.values() if c['n'] == 24 and
                (c['task'] == 'file' or not c['entangled'])]
    for case in selected:
        arms = ('complete', 'stream_16') if case['task'] == 'file' else ('cse_flat', 'independent_expr', 'bdd_cudd')
        for repeat in range(5):
            for method in (arms if repeat % 2 == 0 else arms[::-1]):
                start = time.perf_counter_ns()
                child = subprocess.run([sys.executable, '-B', '-m', 'scripts.cm_packed_io_campaign',
                                        'worker', '--output', str(output), '--case', case['id'],
                                        '--method', method], capture_output=True, text=True, check=True, timeout=90)
                elapsed = time.perf_counter_ns() - start
                row = json.loads(child.stdout)
                assert row['result'] == targets[case['id'], 1]
                lifecycle.append(dict(row, case=case['id'], method=method, repeat=repeat,
                                      process_lifecycle_ns=elapsed, exact=True))
    prior.write(output / 'LIFECYCLE.json', lifecycle)
    cancellation = []
    case = cases['file-n24']
    shared_pool = PackedMaskCache(max_bytes=2 << 20, max_width=18)
    plan = PackedStreamPlan.from_expr(expr_from_json(case['document']),
                                     tuple(f'x{i}' for i in range(24)), cache=shared_pool)
    def cancelled_file(index):
        with tempfile.TemporaryDirectory(prefix='cm-cancel-') as temporary:
            path = Path(temporary) / 'prefix.bin'
            with path.open('xb') as sink:
                receipt = write_packed_stream(plan, sink, chunk_vars=16, max_total_bits=1 << 24,
                                              cancelled=lambda: sink.tell() >= 3 * 8192)
                sink.flush()
                os.fsync(sink.fileno())
            assert not receipt.completed and receipt.chunks == 3
            assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt.sha256
            # Independent numpy prefix oracle uses fixed high axes at zero.
            prefix_context = {f'x{i}': 0 for i in range(6)}
            expected = oracle(case, prefix_context)
            # Full independent digest checked elsewhere; cancellation is also
            # checked byte-for-byte against a separately generated full prefix.
            expr = expr_from_json(case['document'])
            bits = bs.eval_expr_flat_cse(expr, tuple(f'x{i}' for i in range(6, 24)),
                                         fixed=prefix_context, flatten=True)
            data = bits.to_bytes(32768, 'little')
            assert hashlib.sha256(data).hexdigest() == expected['sha256']
            assert path.read_bytes() == data[:receipt.written_bytes]
            return dict(index=index, **asdict(receipt), exact=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        cancellation = list(pool.map(cancelled_file, range(16)))
    stats = shared_pool.stats()
    assert stats['entry_bytes'] <= stats['max_bytes']
    shared_pool.clear()
    prior.write(output / 'CANCELLATION.json', dict(rows=cancellation, cache=stats,
                                                  after_clear=shared_pool.stats()))
    prior.write(output / 'RESULT.json', dict(status='complete', timing_rows=len(rows), memory_rows=len(memory),
                                            fresh_children=len(lifecycle), cancellation_sessions=len(cancellation),
                                            verified_files=sum(r['files_replayed'] for r in rows)))


def verify(output):
    freeze = json.loads((output / 'FREEZE.json').read_text())
    rows = [json.loads(line) for line in (output / 'RAW.jsonl').read_text().splitlines()]
    targets = {(r['case'], r['q']): r['result'] for r in json.loads((output / 'ORACLES.json').read_text())}
    cases = json.loads((output / 'FIXTURES.json').read_text())
    assert len(rows) == len(freeze['schedule'])
    for row, cell in zip(rows, freeze['schedule']):
        assert all(row[k] == v for k, v in cell.items())
        assert row['result'] == targets[row['case'], row['q']] and row['exact']
        assert row['total_ns'] == row['setup_ns'] + row['query_delivery_ns'] + row['cleanup_ns']
    for case in cases:
        for q in (1, 8):
            values = [oracle(case, c) for c in contexts(case, q)]
            result = ([v['count'] for v in values] if case['task'] == 'count' else
                      [{k: v[k] for k in ('sha256', 'bytes')} for v in values])
            assert result == targets[case['id'], q]
    prior.write(output / 'VERIFICATION.json', dict(status='verified', rows=len(rows),
                                                   oracle_contexts=sum(len(contexts(c,q)) for c in cases for q in (1,8)),
                                                   scope='Schedule, charged totals, outputs and independent tiled NumPy oracle replay'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'run', 'verify', 'worker'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case')
    parser.add_argument('--method')
    args = parser.parse_args()
    if args.action == 'freeze': freeze(args.output)
    elif args.action == 'run': run(args.output)
    elif args.action == 'verify': verify(args.output)
    else:
        case = next(c for c in json.loads((args.output / 'FIXTURES.json').read_text()) if c['id'] == args.case)
        with tempfile.TemporaryDirectory(prefix='cm-fresh-sink-') as temporary:
            result, files, measures = session(case, args.method, 1,
                args.output / 'inputs' / (case['id'] + '.json'), Path(temporary), warm=False)
            reread(files, result)
        print(json.dumps(dict(result=result, **measures,
                              peak_process_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)))


if __name__ == '__main__':
    main()
