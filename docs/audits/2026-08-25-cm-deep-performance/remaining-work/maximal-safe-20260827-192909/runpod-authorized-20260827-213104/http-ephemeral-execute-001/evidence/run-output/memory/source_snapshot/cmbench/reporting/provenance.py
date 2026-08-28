"""Small deterministic provenance helpers shared by benchmark tooling."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: str | Path, *, chunk_size: int = 1 << 20) -> str:
    """Return the SHA-256 digest of a file without retaining it in memory."""
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
