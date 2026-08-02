# CM Gap Series — Next-Phase Master Handoff (2026-08-03, post-acceptance)

Self-contained state for a completely new session after the
**post-acceptance independent replication pass**. Read this file, then the
files it points to, and nothing else is assumed.

## 1. What this pass did (executed by a new, independent agent session)

1. **Independent spot replication of the corrected E3 aggregation —
   PASSED.** A from-scratch, stdlib-only reimplementation (no driver, no
   prior probe, no prior aggregation helper, driver code never opened)
   reproduced every archived summary row (60/60, max float deviation
   2.0e-16), every break-even integer and the 30 never-break-even IDs,
   all recorded derived statistics, and landed an own-RNG stratified
   bootstrap within ±0.005 on all 8 archived stratified CI endpoints.
   This closes the acceptance review's same-session caveat (its §4A
   nomination). Report:
   `deliverables_n22_24\CM_GAP_INDEPENDENT_SPOT_REPLICATION_2026-08-03.md`.
   Two definitions were recovered and documented in the process (summary
   medians are log-space medians; exact break-even rule) — documentation
   nuances, zero numeric impact on cited values.
2. **R1/R2 clarifications of record** (identity-basis corpus fields;
   foreign/twin lowered-slot duplication):
   `deliverables_n22_24\CM_GAP_POST_ACCEPTANCE_CLARIFICATIONS_2026-08-03.md`.
   No historical artifact amended.
3. **EPFL/AIGER external-corpus protocol pre-registered and frozen**
   (incl. the materiality rule fixed before any external data):
   `deliverables_n22_24\CM_GAP_EPFL_PROTOCOL_2026-08-03.md`. Execution
   blocked on download approval.
4. **Pod replication decided NOT WARRANTED** (no cross-machine claim
   intended; no decision changes on pod evidence; trigger to revisit
   documented) and **optimization decision recorded: Outcome A,
   provisional pending EPFL** — treat CM and CSE-flat as
   kernel-equivalent; do not chase the synthetic 0.985; prioritize prep
   cost, cache behavior, and a validated backend selector:
   `deliverables_n22_24\CM_GAP_POST_ACCEPTANCE_OPTIMIZATION_DECISION_2026-08-03.md`.
5. **Verification**: targeted tests 53 passed + 4 subtests (33.3 s);
   full suite 326 passed, 0 failed, 4 subtests (424.2 s).

## 2. Repository state (verified at pass start and end)

- Root: `C:\Users\brian\Documents\CM_Computation`; branch `main`;
  HEAD = `origin/main` = `eab8879edcb7fb13582ad9bdff7ea7c00238774d`.
- Latest commits: `eab8879` (corrected evidence + final acceptance audit),
  `f378eba` (corrected E3 tooling), `882e2c2` (v2 serde reachability),
  `c1d6ead` (foreign-node structural adoption), on `4c51429`.
- `git diff --stat` empty; `git diff --check` clean; **no tracked file was
  modified by this pass.**
- Untracked, pre-existing, preserve:
  `deliverables_n22_24\CM_FINAL_REVIEW_PROMPT_2026-08-02.md`, `.claude\`,
  `tmp\`.
- Untracked, new this pass (commit decision pending): the seven
  deliverables in §3.
- Interpreters: benchmarks/analysis `.venv\Scripts\python.exe` (3.13.5,
  numpy 2.3.2); tests system Python 3.10.11 with workspace-local
  `--basetemp` whose parent exists.

## 3. Artifact map

Authoritative, accepted (committed at `eab8879`; hashes re-verified this
pass): corrected corpus
`CM_gap_e3_corrected_corpus_2026_08_02.jsonl`
(`8a6da87cc8b13f6123cb11adfa77b5d69bcd0a086666abea7df633ef92f6e68a`),
results `cm_gap_e3_corrected_results_2026_08_02.json`
(`66cde08a4722ec4bff4693c0e8ce426acb6dc2756ee821d2c89942819977ec9b`),
driver `cm_gap_e3_corrected_2026_08_02.py`
(`421c32af52a78cff08a045c721f1842f12962939a77dcf0e7cab2775b88773a8`),
summary `CM_gap_e3_corrected_summary_2026_08_02.csv`
(`39ea2df45c25a415580ea3533e52845d9990cfc1bc4c1bf037f127d29c17b53f`),
acceptance review `CM_GAP_CONSOLIDATED_REVIEW_2026-08-03.md`
(`02624709b7e013141c17b70d0c190d9626dca5de93b9bcd38bc714197a7a34e2`),
review results `cm_gap_consolidated_review_results_2026_08_03.json`
(`a5f5a52e1ea4ceb39952ac150013d7b25a712b664a8b6aa35a8b5ab519ee462a`),
consolidated audit + erratum
`CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md`
(`50ca585a681bdb7c312ffae44ad8efc920ec25535a07f3ce6f93f4c463e52d07`),
acceptance handoff `CM_GAP_FINAL_ACCEPTANCE_HANDOFF_2026-08-03.md`
(`c7d8ad3284c46912753b9dd4d3d04fbed41fb043d752a0799c225a457e9a78b2`).

New this pass (untracked; SHA-256 in
`CM_GAP_POST_ACCEPTANCE_FILE_INDEX_2026-08-03.md`):

- `CM_GAP_INDEPENDENT_SPOT_REPLICATION_2026-08-03.md`
- `cm_gap_independent_spot_replication_results_2026_08_03.json`
- `CM_GAP_POST_ACCEPTANCE_CLARIFICATIONS_2026-08-03.md`
- `CM_GAP_EPFL_PROTOCOL_2026-08-03.md`
- `CM_GAP_POST_ACCEPTANCE_OPTIMIZATION_DECISION_2026-08-03.md`
- `CM_GAP_POST_ACCEPTANCE_FILE_INDEX_2026-08-03.md`
- `CM_GAP_NEXT_PHASE_MASTER_HANDOFF_2026-08-03.md` (this file)

Scratch preserved under `tmp\cm_gap_post_acceptance_2026-08-03\`
(replication script
`13d6a83688d4d40c5f07e979393f3235be1546a0794260bcb54abc8ef566fd16`,
median-basis diagnostic, schema inspector).

Superseded map: unchanged from
`CM_GAP_FILE_INDEX_AND_SUPERSESSION_2026-08-02.md` (0.843 and the
96-formula corpus remain superseded; 128×/240× retraction stands; cite
0.888 [0.876, 0.899] vs plain CSE and 0.985 vs CSE-flat, single-machine
synthetic scope).

## 4. Permissions and external actions

- Authorization flags at end of pass — all still `NO`:
  `EPFL_DOWNLOAD_APPROVED`, `POD_REPLICATION_APPROVED`,
  `DEPENDENCY_INSTALL_APPROVED`, `COMMIT_PUSH_APPROVED`.
- Downloads: **none**. Dependency installs: **none**. Pods: **none**.
  Compute cost: **$0** (local only). Commits/pushes: **none**.
- The only deletions performed were of this session's **own** premature
  outputs (an accidental empty directory pair, and the first FAILED-verdict
  draft of the replication JSON, regenerated minutes later by the corrected
  script at the same path — disclosed in the replication report). No
  pre-existing file was deleted, overwritten, staged, or modified.

## 5. Approval gates for Brian (next external work)

**EPFL download** (Phase 4 of the post-acceptance program):
- action: `git clone --depth 1 https://github.com/lsils/benchmarks.git C:\Users\brian\Documents\CM_Computation\external\epfl-benchmarks`
- expected size ~50 MB; zero compute cost; clone never staged or modified;
- no dependency install anticipated (in-repo binary-AIGER parser; venv
  numpy);
- everything else is frozen in `CM_GAP_EPFL_PROTOCOL_2026-08-03.md`.

**Pod replication**: NOT WARRANTED — do not approve unless a cross-machine
claim becomes intended. If that changes: 5 × `cpu3c` pods, ~5 pod-minutes
each, est. < $1 total, frozen corrected corpus + driver, worker must first
be redeployed from current `cm_remote_worker.py` (stale workers fail
closed on the `remote_words_eval` echo; no local-fallback rows accepted),
pods terminated after evidence collection, pod-clustered analysis.

**Commit decision** (see §7).

## 6. Tests (system Python 3.10.11)

- Targeted (`tests/test_e3_output_safety.py`,
  `test_e3_corpus_determinism.py`, `test_expr_serde_v2.py`,
  `test_foreign_node_interning.py`, `test_persistent_path_consistency.py`;
  basetemp `tmp\pytest_cm_post_acceptance_2026-08-03_targeted`):
  **53 passed, 4 subtests, 33.3 s.**
- Full suite (`python -m pytest tests -q --basetemp
  tmp\pytest_cm_post_acceptance_2026-08-03`): **326 passed, 0 failed,
  4 subtests, 424.2 s** — matches the accepted baseline exactly. No
  environmental failures.
- No production or test file was added or modified by this pass; the suite
  run is confirmatory (new Python files are scratch analysis only).

## 7. Recommended commit decomposition (do not execute without Brian)

1. `bench(audit): independent spot replication of corrected E3` —
   `deliverables_n22_24/CM_GAP_INDEPENDENT_SPOT_REPLICATION_2026-08-03.md`,
   `deliverables_n22_24/cm_gap_independent_spot_replication_results_2026_08_03.json`
2. `docs(cm): R1/R2 post-acceptance clarifications` —
   `deliverables_n22_24/CM_GAP_POST_ACCEPTANCE_CLARIFICATIONS_2026-08-03.md`
3. `bench(protocol): pre-register EPFL external-corpus campaign` —
   `deliverables_n22_24/CM_GAP_EPFL_PROTOCOL_2026-08-03.md`
4. `docs(audit): post-acceptance optimization decision and pass index` —
   `deliverables_n22_24/CM_GAP_POST_ACCEPTANCE_OPTIMIZATION_DECISION_2026-08-03.md`,
   `deliverables_n22_24/CM_GAP_POST_ACCEPTANCE_FILE_INDEX_2026-08-03.md`,
   `deliverables_n22_24/CM_GAP_NEXT_PHASE_MASTER_HANDOFF_2026-08-03.md`

Stage the listed files individually (never `git add .`); never stage
`.claude\`, `tmp\`, `external\`, or
`CM_FINAL_REVIEW_PROMPT_2026-08-02.md`. Each message ends with the repo's
`Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` convention. Push
only after confirming remote/branch; no force-push.

## 8. Unresolved risks (carried, none blocking)

blake2b-128 collision assumption (documented); re-associated chain
variants as separate guard classes (pre-existing); corrected E3 remains
single-machine + synthetic-generator scoped until EPFL runs; selector
decision rule unvalidated (analysis stage only); R1/R2 remain
informational with clarifications now standing; EPFL protocol untested
against real AIGER data until approved (any defect found during execution
stops the run and versions a successor protocol).

## 9. Next implementation prompt (copy-paste for a new session, after approval)

```
CM EPFL external validation — execute the frozen protocol.

Project root: C:\Users\brian\Documents\CM_Computation. Confirm HEAD =
origin/main and record the git surface first. Authorization flags:
EPFL_DOWNLOAD_APPROVED = YES (granted this session);
DEPENDENCY_INSTALL_APPROVED / POD_REPLICATION_APPROVED / COMMIT_PUSH_APPROVED
= NO unless Brian states otherwise.

Read, in order:
1. deliverables_n22_24\CM_GAP_EPFL_PROTOCOL_2026-08-03.md  (the frozen
   protocol — execute it as written; do not revise it after seeing data)
2. deliverables_n22_24\CM_GAP_NEXT_PHASE_MASTER_HANDOFF_2026-08-03.md
3. deliverables_n22_24\CM_GAP_POST_ACCEPTANCE_OPTIMIZATION_DECISION_2026-08-03.md

Then: clone per protocol §1 (record provenance manifest); implement the
extractor + parser tests per §2–§3 (no new dependencies; stdlib + venv
numpy; benchmarks on .venv python 3.13.5, tests on system 3.10 with an
existing basetemp parent); deterministic pilot, widening gate, then the
full campaign per §4; cluster-aware analysis per §5; apply the §6
materiality rule exactly as pre-registered; write the §7 artifacts with
refuse-overwrite defaults and end the validation report with exactly one
of the four §7 verdicts. Independently reaggregate summaries from raw
rows before citing them. Report all skips with reasons. Do not stage or
commit anything (including the clone) without explicit approval. If a
protocol defect is discovered mid-run: stop, document it, version a new
protocol file, and rerun into new filenames.
```

## 10. Overall status

Independent replication: **PASSED**. Documentation: **complete**. External
legs: **pre-registered, awaiting authorization** (EPFL) / **not warranted**
(pods). Optimization: **Outcome A provisional; no production change
justified**. Working tree: **clean of modifications; new deliverables
uncommitted pending Brian.**

**READY FOR AUTHORIZED EXTERNAL WORK**
