# CM Performance Audit Artifacts

Use these files as follows:

1. Read `CM-PERFORMANCE-AUDIT.md` for the architecture, findings, complexity,
   implementations, and prioritized conclusions.
2. Read `CM-BENCHMARK-RESULTS.md` for exact commands and controlled numbers.
3. Use `before_*` and `after_*` for the authoritative compile optimization A/B.
4. Use `final_batched_large_*` for final sustained wall/CPU timing.
5. Use `final_large_*` for one-operation allocation and peak-RSS behavior.
6. Use `final_cold_warm_*` for first-touch versus warm-cache behavior.
7. Use `baseline_pipeline*` and the `.prof` files for whole-pipeline and
   call-stack attribution.
8. Use `CM-OPTIMIZATION-BACKLOG.md` for remaining work.
9. Read `OUTPUT-BUDGET-CONTINUATION.md` for the post-audit resource guard.
10. Use `NEXT-AGENT-IMPLEMENTATION-PROMPT.md` to continue with byte-bounded
    caches and remote-worker admission in a fresh thread.

The other smoke/final files are retained as exploratory audit history. They are
not the source of headline claims.

## Quick commands

```powershell
.\.venv\Scripts\python.exe scripts\cm_performance_audit.py `
  --suite smoke --label smoke --warmups 2 --repetitions 5 `
  --output-prefix docs\audits\2026-07-26-cm-performance\reproduction_smoke
```

```powershell
python -m pytest -q
```

The benchmark tool writes:

- `<prefix>_raw.jsonl`: environment record plus every per-repetition sample;
- `<prefix>_summary.json`: medians, MAD, p10/p90, throughput, memory, and
  correctness signature.

Performance thresholds are intentionally not part of ordinary pytest.
