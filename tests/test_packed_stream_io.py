"""Binary consumer contracts, failures, cancellation and concurrent ownership."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
from itertools import product

import pytest

from cm_exprlib import Imp, Var, Xor
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import PackedStreamPlan
from cmbench.backends.packed_stream_io import write_packed_stream


def plan(width=9):
    return PackedStreamPlan.from_expr(Imp(Xor(Var(0), Var(1)), Var(2)),
                                     tuple(f"x{i}" for i in range(width)),
                                     cache=PackedMaskCache(max_bytes=8192, max_width=9))


def expected(basis, fixed):
    live = [n for n in basis if n not in fixed]
    values = []
    for row in product((0, 1), repeat=len(live)):
        env = dict(zip(live, row)) | fixed
        values.append(int(not (env['x0'] != env['x1']) or env['x2']))
    return sum(v << i for i, v in enumerate(values)).to_bytes((len(values) + 7) // 8, 'little')


class ShortSink(io.BytesIO):
    def write(self, data):
        return super().write(data[:3])


@pytest.mark.parametrize('fixed', [{}, {'x0': 0}, {'x0': 1, 'x1': 0, 'x2': 1}])
@pytest.mark.parametrize('width', [3, 5, 9])
def test_short_writes_and_padding(width, fixed):
    p = plan(width)
    sink = ShortSink()
    receipt = write_packed_stream(p, sink, chunk_vars=3, max_total_bits=512, fixed=fixed)
    data = expected(p.basis, fixed)
    assert receipt.completed
    assert receipt.written_bits == receipt.total_bits == 1 << (width - len(fixed))
    assert receipt.written_bytes == len(data)
    assert receipt.sha256 == hashlib.sha256(data).hexdigest()
    assert sink.getvalue() == data and not sink.closed


@pytest.mark.parametrize('stop', [0, 1, 7, 64])
def test_cancelled_prefix_does_not_generate_the_next_chunk(stop):
    p = plan()
    sink = io.BytesIO()
    receipt = write_packed_stream(p, sink, chunk_vars=3, max_total_bits=512,
                                 cancelled=lambda: sink.tell() >= stop)
    assert receipt.completed == (stop == 64)
    assert receipt.chunks == stop
    assert receipt.written_bits == stop * 8
    assert sink.getvalue() == expected(p.basis, {})[:stop]
    assert receipt.sha256 == hashlib.sha256(sink.getvalue()).hexdigest()
    assert p.cache.stats()['misses'] + p.cache.stats()['hits'] == stop


@pytest.mark.parametrize('answer', [None, 0, -1, 1000, True, 1.5])
def test_broken_sink_fails_without_spinning(answer):
    class Broken:
        calls = 0
        def write(self, data):
            self.calls += 1
            return answer
    sink = Broken()
    with pytest.raises(OSError):
        write_packed_stream(plan(), sink, chunk_vars=3, max_total_bits=512)
    assert sink.calls == 1


def test_guard_does_not_touch_sink_or_generate():
    p = plan()
    sink = io.BytesIO(b'unchanged')
    with pytest.raises(ValueError):
        write_packed_stream(p, sink, chunk_vars=3, max_total_bits=256)
    assert sink.getvalue() == b'unchanged'
    assert p.cache.stats()['misses'] == 0


def test_sink_error_releases_generator_and_preserves_partial_bytes():
    class Failing(ShortSink):
        def write(self, data):
            if self.tell() >= 3:
                raise OSError('disk full')
            return super().write(data)
    p = plan()
    sink = Failing()
    with pytest.raises(OSError, match='disk full'):
        write_packed_stream(p, sink, chunk_vars=6, max_total_bits=512)
    assert sink.getvalue() == expected(p.basis, {})[:3]
    assert not sink.closed
    p.cache.clear()
    assert p.cache.stats()['entries'] == 0


def test_shared_plan_separate_sinks_and_fixed_contexts():
    p = plan()
    def run(index):
        context = {'x0': index % 2, 'x1': index // 2 % 2}
        sink = ShortSink()
        receipt = write_packed_stream(p, sink, chunk_vars=4, max_total_bits=512, fixed=context)
        assert sink.getvalue() == expected(p.basis, context)
        return receipt.completed
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(pool.map(run, range(32)))
    assert p.cache.stats()['entry_bytes'] <= 8192
