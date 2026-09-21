"""Download the exact CUDD release pinned by dd 0.6.0; verify before use."""
import hashlib
from pathlib import Path
import tarfile
import urllib.request

BASE = Path(__file__).resolve().parent
URL = "https://sourceforge.net/projects/cudd-mirror/files/cudd-3.0.0.tar.gz/download"
SHA256 = "b8e966b4562c96a03e7fbea239729587d7b395d53cadcc39a7203b49cf7eeb69"
archive = BASE / "build/downloads/cudd-3.0.0.tar.gz"
if not archive.exists():
    with urllib.request.urlopen(URL, timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise RuntimeError("Unexpected CUDD release hash")
    archive.write_bytes(data)
if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
    raise RuntimeError("Unexpected cached CUDD release hash")
destination = BASE / "build/dd-0.6.0"
if not (destination / "cudd-3.0.0").exists():
    with tarfile.open(archive) as source:
        source.extractall(destination, filter="data")
print("Verified CUDD 3.0.0:", SHA256)
