# Local packed-mask audit protocol notes

The original `freeze.json` and source snapshot precede candidate timing. The
algorithm is fixed: directly repeat periodic packed bytes above the existing
10-variable branch boundary, with no change below it. All inputs are new
synthetic fixtures; confirmation is independent by seed and width, not by
application family or machine. Nine paired AB/BA rounds are descriptive local
evidence, not a production workload gate. No earlier frozen panel is reopened.

The initial profile was instrumented and is diagnostic only. Environment timing
is a separate uninstrumented pass. Before whole-session development timing, the
harness corrected the dense mode spelling to `numpy` (the supported mode), and
removed a needless direct-control environment copy. The exact development
harness is preserved in `harness_development.py`. No failed campaign was erased.

After development, comparator review identified that `eval_expr_flat_cse`
defaults to structural CSE without associative flattening. Those saved rows are
labelled `cse`, correctly. A separate `development_strong` run adds `cse_flat`
with `flatten=True`; confirmation retains BOTH arms. This strengthens the
comparator without retuning the candidate. The candidate's identical byte
construction is integrated into `bitset_backend.py` for regression testing.

Whole-session timing includes DAG decode/validation, representation compilation,
binding, execution, guard/selection where provided by the chosen public API,
and packed delivery. Inputs, oracle, cache clearing, and GC before each session
are outside timing. Programs and masks are shared only within a session. The
separate warm measurement excludes its preceding setup and warm-up; it does
not represent a fresh process. The task returns each requested packed result;
q64 intentionally executes 64 requests without a result cache.

Restrictions rotate three fixed variable positions and values. The `direct`
restriction arm uses the public raw-AST flat fixed-assignment evaluator because
the recursive direct evaluator infers its truth width from its environment.
Explicitly naming this change avoids treating an unsupported contract as a
direct recursive comparison.

All vector oracles interpret the stored DAG using independent NumPy Boolean
arrays and integer assignment indices. No oracle consumes candidate masks.
Dense output is charged for conversion to the same complete packed relation.
Fresh-process diagnostics are a separate pass, with interpreter/import/lifecycle
time included in parent elapsed time. OS retained endpoints and process-lifetime
peak are labelled separately from task-scoped tracemalloc peak; a process peak
is not a calibrated incremental task peak.

The candidate preserves cache keys, size, identity, immutability, output basis,
and output resource guards. It does not provide a byte-bounded cache. No native
batch source, earlier frozen file, website, default router, or resource policy
is changed by this audit.

The first fresh-process diagnostic includes both an uninstrumented build and a
tracemalloc build. Its parent lifecycle is explicitly NOT a one-shot latency.
`fresh_process_timing.json` is a separate five-pair pass using `--timing-only`:
one build, checksum delivery, imports and process cleanup. Both artifacts are
retained. The original lifecycle source is `lifecycle_diagnostic.py`; the added
timing-only path does not change the mask candidate or confirmation workload.

The initial verifier's minimum CM ratio field covered q1. The strengthened
`verification_all_sessions.json` checks the same 0.95 floor over EVERY cold
CM session cell, including q64 and changing restrictions. Raw evidence and
thresholds are unchanged. The original verification receipt remains available.
