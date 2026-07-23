"""Latent-fix 2 proof: remote words provenance round trip and refusal.

1) Mock round trip: build_remote_request(words_eval=True) -> local mock worker
   -> response echoes remote_words_eval=True and the packed result equals the
   local recursive-bigint reference bit-for-bit (fuzz n=8..14).
2) Stale-worker simulation: a response whose diagnostics lack the
   remote_words_eval echo (what a pre-fix deployed worker returns) makes
   cm_bench._check_remote_words_provenance raise instead of recording a row
   that claims words was used remotely.

Writes CM_latentfix2_remote_words_roundtrip.csv; exits nonzero on failure.
"""
from __future__ import annotations

import csv
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cm_bench
from bitset_backend import build_bitset_env, eval_expr_bitset
from cm_exprlib import random_expr
from cm_remote_executor import LocalMockCMRemoteExecutor, build_remote_request

OUT = Path(__file__).resolve().parent / "CM_latentfix2_remote_words_roundtrip.csv"


def main() -> int:
    rng = np.random.default_rng(20260723)
    rows = []
    failures = 0
    last_result = None
    for n in range(8, 15, 2):
        names = [f"x{i}" for i in range(n)]
        for expr_index in range(4):
            expr = random_expr(n, rng, max_depth=6, p_unary=0.25)
            ref_bits = int(eval_expr_bitset(expr, build_bitset_env(names)))
            for words in (False, True):
                req = build_remote_request(
                    expr, n, hybrid_threshold=16, max_full_output_vars=26, words_eval=words
                )
                result = LocalMockCMRemoteExecutor().execute(req)
                last_result = result
                ok = bool(result.response.ok)
                echo = result.response.diagnostics.get("remote_words_eval")
                payload = result.response.result or {}
                remote_bits = int(str(payload.get("bits_hex", "0x-1")), 16) if "bits_hex" in payload else None
                # The remote result may be scope-reduced; compare only full-scope results.
                out_vars = payload.get("output_vars")
                full_scope = out_vars is not None and len(out_vars) == n
                bits_eq = (remote_bits == ref_bits) if full_scope else None
                case_ok = ok and (echo is words) and (bits_eq is not False)
                failures += 0 if case_ok else 1
                rows.append(
                    {
                        "n_vars": n,
                        "expr_index": expr_index,
                        "words_eval_requested": words,
                        "response_ok": ok,
                        "remote_words_eval_echo": echo,
                        "full_scope": full_scope,
                        "packed_bits_equal": bits_eq,
                        "case_ok": case_ok,
                    }
                )

    # Stale-worker simulation: strip the echo, expect refusal for words runs
    # and acceptance for non-words runs.
    stale = replace(
        last_result,
        response=replace(
            last_result.response,
            diagnostics={
                k: v for k, v in last_result.response.diagnostics.items() if k != "remote_words_eval"
            },
        ),
    )
    try:
        cm_bench._check_remote_words_provenance(stale, words_requested=True)
        stale_refused = False
    except RuntimeError as exc:
        stale_refused = "did not confirm words_eval" in str(exc)
    stale_nonwords_accepted = (
        cm_bench._check_remote_words_provenance(stale, words_requested=False) is stale
    )
    failures += 0 if (stale_refused and stale_nonwords_accepted) else 1
    rows.append(
        {
            "n_vars": "stale_worker_sim",
            "expr_index": "",
            "words_eval_requested": True,
            "response_ok": stale.response.ok,
            "remote_words_eval_echo": None,
            "full_scope": "",
            "packed_bits_equal": "",
            "case_ok": stale_refused and stale_nonwords_accepted,
        }
    )

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(
        f"cases={len(rows)} failures={failures} stale_refused={stale_refused} "
        f"stale_nonwords_accepted={stale_nonwords_accepted} -> {OUT.name}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
