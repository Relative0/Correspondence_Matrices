# Delivering packed truth bytes to a file or synchronous consumer

`cmbench.backends.packed_stream_io.write_packed_stream` connects a prepared
`PackedStreamPlan` to a binary sink without collecting the whole truth vector.
It returns a frozen receipt containing completion, total/written bits, written
bytes, chunk count and SHA-256 of the accepted bytes.

```python
import os
from cm_exprlib import And, Var
from cmbench.backends.packed_mask_cache import PackedMaskCache
from cmbench.backends.packed_queries import PackedStreamPlan
from cmbench.backends.packed_stream_io import write_packed_stream

cache = PackedMaskCache(max_bytes=2 << 20, max_width=18)
plan = PackedStreamPlan.from_expr(
    And(Var(0), Var(1)), tuple(f"x{i}" for i in range(24)), cache=cache,
)
with open("truth.bin", "xb") as sink:
    receipt = write_packed_stream(
        plan, sink, chunk_vars=16, max_total_bits=1 << 24,
        cancelled=lambda: False,  # Substitute a thread-safe cancellation flag.
    )
    sink.flush()
    os.fsync(sink.fileno())
assert receipt.completed
cache.clear()
```

The example emits 2 MiB in 8 KiB chunks. Assignment order follows the declared
remaining basis, with the first axis most significant; assignment rows are
packed into bytes least-significant bit first. Outputs shorter than eight bits
occupy one byte, with unused high bits zero. Save the ordered basis, fixed values
and receipt alongside the bytes if another process will read them: a digest alone
does not describe the Boolean task or variable order.

The function validates its output/chunk limits before touching the sink. Opening
a path is the caller's responsibility; use exclusive creation where overwrites
are unwanted. A short write is retried with the remaining bytes. No next chunk
is computed until the current chunk has been accepted. Zero progress or a
nonblocking `None` return raises `BlockingIOError`; invalid write lengths raise
`OSError`.

Cancellation is checked before generating each chunk. It returns a verified
ordered prefix with `completed=False`; a started chunk finishes first. The
receipt distinguishes written valid bits from byte padding. A sink exception
propagates, leaves any accepted prefix in the caller's sink, and closes the
generator. It does not produce a completion receipt. The caller decides how to
retain, mark or discard that partial artifact.

The writer neither flushes nor closes the sink and does not promise atomic
publication or durable storage. SHA-256 covers bytes accepted by `write`; the
RunPod campaign additionally flushes/fsyncs/closes and rereads each file before
calling it verified. A buffered sink can retain its own data, so total memory
includes its buffering and the plan's working space as well as cached masks.

Concurrent callers may share a plan/cache with separate sinks and contexts.
Sharing a sink requires caller synchronization. The cache budget bounds retained
mask entries, not whole-process RSS, in-flight work or references held by callers.
There is no automatic chunk tuning, backend selection or change to default CM
execution.
