# Next-Agent Handoff: CM Deep Performance

Copy/paste the prompt below only when one of the remaining work items is authorized.

```text
Continue the CM performance work in:
C:\Users\brian\Documents\CM_Computation

Read first, in order:
1. docs\audits\2026-08-24-cm-deep-performance\CM-DEEP-PERFORMANCE-AUDIT.md
2. docs\audits\2026-08-24-cm-deep-performance\CM-BENCHMARK-RESULTS.md
3. docs\audits\2026-08-24-cm-deep-performance\CM-RESEARCH-LEDGER.md
4. docs\audits\2026-08-24-cm-deep-performance\CM-OPTIMIZATION-BACKLOG.md
5. the current claim map/addendum and post-acceptance decision listed in the audit

Repository state at the audit start:
- branch main
- HEAD 6fe11d713cae39e56cd3251cca8e8ceb9cc5578f
- the tree was already dirty with README and website/explainer work plus untracked
  .claude, external, tmp, and a website UX document. Preserve them exactly.
- do not read .env/credentials, install dependencies, commit, push, deploy, or
  make external writes without Brian's explicit approval.

Audit-owned production/test changes:
- cmbench\backends\bitset_engine.py: WORDS_AUTO_MIN_VARS=16; automatic words
  routing begins at k=16.
- cm_ir.py: immutable CM roots memoize _node_count; no-reinflate admission reuses
  the count for full/reduced estimates.
- tests\test_bitset_engine_policy.py: selector boundary/exactness regression tests.
- tests\test_cm_ir_cost.py: derived node-count cache regression test.

Audit-owned tooling/docs:
- scripts\cm_deep_performance_audit.py
- docs\audits\2026-08-24-cm-deep-performance\ (reports, raw CSV/JSON,
  environment sidecars, selector/phase tables, cProfile artifact)

Validation completed:
- focused selector/CM-cost tests: 25 passed.
- full suite: 345 passed plus 4 subtests using audit-local --basetemp.
- final paired replay: 401 records, exact packed equality; 387 eligible raw arms,
  10 source-protocol skips, 4 explicit 8 MiB temporary-budget refusals.

Key result:
- old k>=6 selector raw regret: BX1 tuning 2.060 geomean with 39/80 >=2x;
  held-out B2+EPFL 2.743 with 200/307 >=2x.
- k>=16 selector raw regret: 1.012 tuning and 1.011 held out, zero >=2x.
- CM-node results have the same direction and zero catastrophic rows at k>=16.
- _cm_node_count medians fall from 6.35/7.40/14.60 us cold to 0.3-0.4 us
  warm on BX1/B2/EPFL.

Claims that must not be resurrected:
- no demonstrated CM kernel advantage over sharing-aware CSE-flat;
- no universal k>=6 words crossover;
- no claim above live_k=16;
- no removal of the complete-output Omega(2^k/w) lower bound;
- no family/cache/partial-context win over the strongest measured incumbent;
- no quotient == semantic XOR;
- no blending CUDD build/restrict/extraction windows;
- no theorem of global canonical CM equality.

Choose exactly one authorized next task:
A. Define and implement a production temporary-memory/refusal policy.
B. Run the unchanged final selector harness on a second machine.
C. Analyze a supplied real cache/version/context trace.
D. Prototype compact interning keys with exact paired B2+EPFL validation.

Before editing, record current branch/HEAD/status and compare against this handoff.
Use .venv\Scripts\python.exe for benchmarks. The venv has no pytest; use the
existing test runtime or request approval to change dependencies. Keep each
experiment isolated, preserve per-formula rows, compare equivalent artifacts,
and retain negative results. Do not start native/JIT/GPU work unless Brian has
approved its dependencies/hardware and a real kernel-dominant workload exists.

Exact selector reproduction command:
& .\.venv\Scripts\python.exe scripts\cm_deep_performance_audit.py `
  --suite representative --corpora bx1,b2,epfl `
  --prep-repetitions 3 --kernel-rounds 5 `
  --max-kernel-temporary-bytes 8388608 `
  --output-prefix docs\audits\YYYY-MM-DD-cm-followup\run_name

Exact full-test command in this restricted environment:
python -m pytest -q --basetemp <a new, verified-nonexistent workspace path>
```
