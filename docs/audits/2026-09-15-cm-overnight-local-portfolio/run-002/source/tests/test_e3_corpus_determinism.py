"""Cross-process corpus determinism of the corrected E3 driver (2026-08-02, F1).

The superseded driver seeded cells with ``hash(family) % 9973``, which varies
with PYTHONHASHSEED, so two processes generated different corpora. The
corrected driver must produce byte-identical corpora (and hence identical
SHA-256) in fresh subprocesses under different hash seeds.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "deliverables_n22_24" / "cm_gap_e3_corrected_2026_08_02.py"


def _generate(tmp_path, hashseed, tag):
    out_dir = tmp_path / f"corpus_{tag}"
    env = dict(os.environ, PYTHONHASHSEED=hashseed)
    proc = subprocess.run(
        [sys.executable, str(DRIVER), "--corpus-only", "--strata", "8",
         "--per-cell", "1", "--out-dir", str(out_dir)],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=600)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    corpus = out_dir / "CM_gap_e3_corrected_corpus_2026_08_02.jsonl"
    data = corpus.read_bytes()
    return data, hashlib.sha256(data).hexdigest()


def test_corpus_bytes_identical_across_hash_seeds(tmp_path):
    data_a, sha_a = _generate(tmp_path, "0", "seed0")
    data_b, sha_b = _generate(tmp_path, "1", "seed1")
    data_c, sha_c = _generate(tmp_path, "31337", "seed31337")
    assert sha_a == sha_b == sha_c
    assert data_a == data_b == data_c
    # sanity: the corpus is non-trivial (meta line + 8 admitted formulas)
    lines = [ln for ln in data_a.decode("utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1 + 8
