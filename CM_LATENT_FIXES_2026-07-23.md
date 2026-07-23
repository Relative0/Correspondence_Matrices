# CM latent fixes — Audit V3 independent-review findings 1, 2, 3, 5

Date: 2026-07-23
Project contact: **Brian Theory (Droncheff)**
Predecessor: `CM_SESSION_2026-07-23_AUDIT_V3_STATE_AND_FINDINGS.md`
Findings source: `CM_AUDIT_V3_INDEPENDENT_REVIEW_2026-07-23.md` (commit `39f3313`), "New findings"

Brian approved fixing findings 1, 2, 3, and 5 of the independent review. Finding 4
(the "two vs three constants" prose understatement in the V3 report) stays
as-documented: prior reports are never edited in this project, and the independent
review already records the correction. Each fix below was first re-verified against
the code at `5dd6ec7`, then landed as its own commit on `main`. All benchmarks ran on
`.venv` Python 3.13.5; all test runs on system Python 3.10.11.

**Aggregate blast radius: zero published numbers change.** Every fix touches either a
path no published result exercised (words/flat in partial/family/remote workloads), a
path unreachable from the compilers (unknown opcodes), or a memory-only allocation
outside all timed windows.

Suite state after each commit and at the end: `python -m pytest -q` = **159 passed**,
collection size unchanged (all new assertions were folded into existing test
functions, per project practice).

---

## Fix 1 — symmetric engine in partial/family Bitset controls (`cc52f43`)

**Verified real.** At `5dd6ec7`, `_cm_partial_workload` (cm_bench.py:390) and
`_cm_family_workload` (cm_bench.py:864) passed `words_eval=config.cm_words_eval` to
the CM side, while the Bitset comparators in the same workloads always used the
recursive bigint engine: full-recompute control `eval_expr_bitset` (~:610), restricted
control `_eval_expr_bitset_fixed` (~:624), family control `eval_expr_bitset` (~:997).
Under `--cm-words-eval` (or `--cm-flat-eval`) those comparisons favored CM.

**Change.** Both workloads now select the control engine with the same precedence as
the single-expression path (words > flat > recursive). Semantics preserved: the engine
changed, not the scope — the full-recompute control still evaluates over all n
variables, the restricted control still evaluates over the remaining variables with
the context supplied as `fixed=`. New provenance columns
`partial_bitset_baseline_kind` and `family_bitset_baseline_kind` record the engine
(`raw_ast_words` / `raw_ast_flat` / `raw_ast_recursive`), mirroring
`bitset_baseline_kind` in single-expression rows.

**Bit-exactness.** `deliverables_n22_24/latentfix1_partial_family_engine_parity_2026_07_23.py`
fuzzes n=8–18 (66 cases: 6 expressions per n, full-scope plus 4 restricted contexts
each): flat and words engines are complete packed-bit equal to the recursive
reference on both scopes — 66/66, `CM_latentfix1_engine_parity.csv`. End-to-end CLI
runs at n=8,12 (2 trials), partial and family workloads, with and without
`--cm-words-eval`: every `*_ok_rate` = 1.0 and the expected baseline kind recorded
(`CM_latentfix1_{partial,family}_cli_{plain,words}_{raw,summary}.csv`), matching the
pattern of `CM_independent_review_words_cli_{ord,lns}_raw.csv` for the single-expr
path.

**Tests.** Words-mode workload assertions folded into
`test_cm_cached_and_no_cache_match_reference` (partial) and
`test_family_workload_correctness_and_cache_fields` (family). 159 passed.

**Blast radius.** Zero published numbers: no published result exercised
partial/family workloads with words/flat enabled. Default-engine rows behave
identically and only gain the provenance column.

## Fix 2 — remote words provenance (`f80a1cd`)

**Verified real.** `execute_remote_cm` (cm_bench.py:190) forwarded `hybrid_threshold`
but not `cm_words_eval`; `CMRemoteRequest` had no words field and
`cm_remote_worker.execute_cm_request` never passed one, so a
`--cm-words-eval --cm-exec-target runpod` run would record `cm_words_eval=True`
while the pod evaluated without words.

**Change (preferred alternative implemented).**
- `CMRemoteRequest` gains `words_eval: bool = False` (from_expr/from_dict/to_dict);
  payloads without the key parse as off, so stale senders stay valid.
- `build_remote_request` and `execute_remote_cm` forward the flag.
- The worker honors it: `materialize_hybrid_no_reinflate(..., words_eval=...)` on the
  reduced-output branch; `evaluate_compiled` gained an optional pass-through
  `words_eval=None` (None = module default — library defaults untouched) for the
  other branch.
- The worker echoes `remote_words_eval` in response diagnostics, and the client
  (`_check_remote_words_provenance`) **refuses** to record a words run whose response
  lacks that echo. A stale deployed worker silently ignores the new request field —
  and precisely because of that, produces no echo, so the run errors out instead of
  recording a provenance lie. The provenance hole is closed against every worker
  vintage.

**Proof.** `deliverables_n22_24/latentfix2_remote_words_provenance_2026_07_23.py`
(`--cm-runpod-local-mock` machinery only; no pods started): 32 mock round trips at
n=8–14, words on/off — response ok, echo correct, full-scope packed bits equal to the
recursive bigint reference in every case; stale-worker simulation (echo stripped)
refused for words and accepted for non-words
(`CM_latentfix2_remote_words_roundtrip.csv`). End-to-end mock CLI run at n=8,12 with
`--cm-exec-target runpod --cm-runpod-local-mock --cm-words-eval`: all rows
`cm_runpod_status=ok`, `cm_words_eval=True`, `cm_hybrid_no_reinflate_ok=True`,
`bitset_baseline_kind=raw_ast_words` (`CM_latentfix2_mock_cli_words_{raw,summary}.csv`).

**Deployment note.** The deployed pod worker predates this protocol. Until it is
redeployed from current `cm_remote_worker.py`, a live `--cm-words-eval` runpod run
fails fast with "remote worker did not confirm words_eval" (recorded as an error row,
optionally falling back to honest local words execution under
`--cm-runpod-fallback-local`). Non-words runpod runs are unaffected. Redeploy at the
next pod session; no pod was started this session per ground rules.

**Tests.** Protocol round-trip (including stale-payload default), mock executor echo,
and mock-CLI provenance assertions folded into `test_expr_and_protocol_round_trip`,
`test_local_mock_remote_executor`, and `test_benchmark_runpod_fields_with_local_mock`.
159 passed.

**Blast radius.** Zero published numbers: no published run combined words with the
runpod target; local execution paths untouched.

## Fix 3 — reject unknown opcodes (`96294ac`)

**Verified real.** The operation loops in `eval_cm_node_flat`
(bitset_backend.py:357), `eval_expr_flat_bitset` (:438), and `_eval_words` (:578)
ended in `else:  # _FLAT_OP_EQV`, executing any unrecognized opcode as EQV — a
malformed FlatProgram computed garbage silently. Swept the library for other
dispatch copies: none (`_compute_word_plan` passes opcodes through without
dispatching; the F4-style prebound copies live only in historical scripts under
`deliverables_n22_24/`, untouched per ground rules).

**Change.** Each loop dispatches `elif opcode == _FLAT_OP_EQV` explicitly and raises
`ValueError("unknown flat opcode: ...")` in the `else`.

**Proof.** `deliverables_n22_24/latentfix3_opcode_guard_2026_07_23.py`
(`CM_latentfix3_opcode_guard.csv`):
- Byte-identity: fuzz n=8–16 collectively covering all six opcodes; new kernels vs
  in-script verbatim copies of the pre-fix loops vs the recursive reference — all
  packed-bit identical, 40/40 cases.
- Refusal: a hand-built `FlatProgram` with opcode 6 (the
  `independent_review_f1_words_extra` pattern) now raises in all three kernels; it
  executed as EQV before.
- Perf formality: one n=18 medium formula, 16 interleaved order-alternating rounds of
  60 evaluations, paired old vs new: min-based new/old ratios **0.974 (words)** and
  **0.984 (flat)** — no measurable hot-loop regression (round medians on this machine
  are noise-dominated at ±15%; mins are stable).

**Tests.** Three-kernel refusal assertions folded into
`test_full_mask_clipping_for_not_imp_eqv`. 159 passed.

**Blast radius.** Zero published numbers: behavior differs only on programs neither
compiler can produce.

## Fix 5 — skip the unused bigint env under words/flat (`1cf4bcf`)

**Verified real.** The ordinary full-output path (cm_bench.py:~2041) built
`local_bit_env` unconditionally; the flat/words branch never reads it — its only
consumers are the recursive `eval_expr_bitset` calls.

**Change.** `local_bit_env` is built only when the recursive engine can run (neither
`--cm-flat-eval` nor `--cm-words-eval`). The build sits before the `t7` timing start
in old and new code alike, so it remains outside all timed windows; the change is
memory-only.

**Proof.** Ordinary local CLI runs at n=8,12 with and without `--cm-words-eval`
(`CM_latentfix5_ordinary_cli_{words,plain}_{raw,summary}.csv`): every `bitset_ok` and
`cm_ok` flag True, baseline kinds `raw_ast_words` / `raw_ast_recursive` as expected.
The recursive path still builds the env and is untouched; the words path never
consumed it, so no computed value can change — the CLI runs confirm the flags.

**Tests.** No behavior visible to tests changed; 159 passed.

**Blast radius.** Zero published numbers: no timing window moves.

---

## Finding 4 — left as-documented (by design)

The V3 report's "two n=18 formulas are constants" understatement (a third constant
exists at n=28 trial 1) is a prose error inside a shipped report. Prior reports are
never edited; the independent review records the correction and the affected 4/29 and
median-16 numbers were already verified unaffected. No code change exists to make.

## Commits

- `cc52f43` — fix 1, partial/family control engine symmetry + provenance columns
- `f80a1cd` — fix 2, remote words_eval forwarding, worker echo, client refusal
- `96294ac` — fix 3, explicit EQV dispatch + unknown-opcode ValueError
- `1cf4bcf` — fix 5, conditional local_bit_env build

## Artifacts (all new, nothing overwritten)

- `deliverables_n22_24/latentfix1_partial_family_engine_parity_2026_07_23.py`,
  `CM_latentfix1_engine_parity.csv`,
  `CM_latentfix1_{partial,family}_cli_{plain,words}_{raw,summary}.csv`
- `deliverables_n22_24/latentfix2_remote_words_provenance_2026_07_23.py`,
  `CM_latentfix2_remote_words_roundtrip.csv`,
  `CM_latentfix2_mock_cli_words_{raw,summary}.csv`
- `deliverables_n22_24/latentfix3_opcode_guard_2026_07_23.py`,
  `CM_latentfix3_opcode_guard.csv`
- `deliverables_n22_24/CM_latentfix5_ordinary_cli_{words,plain}_{raw,summary}.csv`
