"""Synchronous, bounded delivery of ordered packed truth bytes to a binary sink."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
from typing import BinaryIO

from cmbench.backends.packed_queries import PackedStreamPlan


@dataclass(frozen=True)
class PackedWriteResult:
    """Receipt for bytes accepted by the sink, including a cancelled prefix.

    Acceptance does not imply flushing or durable storage. The caller owns the
    sink, its buffering, flush/fsync, and any partial output after an exception.
    """

    completed: bool
    total_bits: int
    written_bits: int
    written_bytes: int
    chunks: int
    sha256: str


def write_packed_stream(
    plan: PackedStreamPlan, sink: BinaryIO, *, chunk_vars: int,
    max_total_bits: int, fixed: Mapping[str, int] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> PackedWriteResult:
    """Write one chunk at a time, honoring synchronous short writes.

    Guards run before the sink is touched. Cancellation is checked before each
    chunk is generated and returns a valid ordered prefix. A started chunk is
    completed before cancellation is checked again. No next chunk is generated
    until the sink accepts the current one. A nonblocking/zero-progress writer
    is refused instead of spinning. The sink is never flushed or closed here.
    """
    context = dict(fixed or {})
    chunks = plan.iter_chunks(chunk_vars=chunk_vars, max_total_bits=max_total_bits,
                              fixed=context)
    total_bits = 1 << (len(plan.basis) - len(context))
    digest = hashlib.sha256()
    written_bits = written_bytes = chunk_count = 0
    try:
        while written_bits < total_bits:
            if cancelled is not None and cancelled():
                break
            chunk = next(chunks)
            view = memoryview(chunk.data)
            offset = 0
            while offset < len(view):
                accepted = sink.write(view[offset:])
                if accepted is None or accepted == 0:
                    raise BlockingIOError("packed sink made no write progress")
                if type(accepted) is not int or not 0 < accepted <= len(view) - offset:
                    raise OSError("packed sink returned an invalid write length")
                offset += accepted
            digest.update(view)
            written_bytes += len(view)
            written_bits += chunk.valid_bits
            chunk_count += 1
            # Release the consumer's reference before asking for another chunk.
            del view, chunk
    finally:
        chunks.close()
    return PackedWriteResult(written_bits == total_bits, total_bits, written_bits,
                             written_bytes, chunk_count, digest.hexdigest())
