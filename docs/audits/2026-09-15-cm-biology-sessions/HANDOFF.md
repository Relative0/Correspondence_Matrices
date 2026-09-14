# Session implementation handoff

Completed: matched raw/CM translators, clamp-aware retained/rebuild sessions, explicit packed and scalar/CaDiCaL controls, hard Windows process-tree supervision, structural row admission, cluster-aware analysis, 288-session development pilot and a deferred all-closed-model replication design.

Read `REPORT.md` first. The primary retained q64 family ratio is 1.0025, not a 5% gain. All completed matched pairs use identical normalized query plans. Canonical CM preprocessing changes plans and remains confounded. There is no heldout or CM-specific speedup claim, and no reason to scale to paid compute on these results.

Worktree: `C:/Users/brian/Documents/CM_Computation/tmp/cm-consolidation-20260914`, based on local main `b3f10bc582f0c2a59a0fe7513af88199a4f65c56`. Original dirty checkout and September 14 audit are preserved. New files remain uncommitted.

Source entry points:

- `cmbench/biology_sessions.py`: raw AST compilation, matched/canonical CM ingress, common normalization, per-equation clamp plans, exact counts/witnesses and worker payloads.
- `cmbench/biology_session_supervisor.py`: Windows Job Object limits, safe child launch, bounded output, deadlines, descendant cleanup and accounting.
- `cmbench/biology_session_analysis.py`: identity/semantic checks, complete-pair and family summaries, explicit failures/confounds, no pilot confidence gate.
- `scripts/cm_biology_sessions.py`: local pilot preparation/execution. New plans snapshot their sources; execution refuses changed sources or an existing ledger.
- `scripts/cm_biology_sessions_finalize.py`: additive reporting correction and frozen deferred replication design. It is tied to this pilot and does not execute future sessions.

Evidence entry points are `pilot-002/PLAN.json`, `RUN.json`, `SOURCE_MANIFEST.json`, `source/`, and the original `ledger.jsonl`; `REPORTING_ADDENDUM.json` and `REPORTING_CORRECTED_LEDGER.jsonl` preserve a metadata-only preprocessing correction. `ANALYSIS.json` and `SUMMARY.json` are derived. `SOURCE_MANIFEST.json` in the parent audit binds current corrected source, while the pilot snapshot binds executed source. Do not confuse those identities or overwrite measured rows.

Current local runtime is the original project `.venv/Scripts/python.exe` with NumPy 2.3.2 and python-sat 1.8.dev20. No installs occurred. Windows supervisor memory is whole-job committed memory; it is not comparable to Linux RSS. The new runner does not implement a Linux supervisor or newly time external AEON/d4/Ganak/CryptoMiniSat arms; their earlier correctness evidence remains in the prior audit. A future cross-platform comparison requires a separately verified supervisor and matching accounting.

`NEXT_LOCAL_PLAN.json` contains 396 explicitly identified sessions: all 22 closed models, q1/q8/q64, three repetitions, matched retained raw/CM paths, deterministic arm alternation, source/corpus/query hashes and 15-minute/10-second/1-GiB bounds. It is a design artifact, not an executable authorization file or a pristine heldout study. It is deferred because no development gain signal emerged. Any future execution must bind the actual executor to this design, preserve all refusal/timeout/not-run outcomes, and avoid making population intervals from exposed families.

Nothing remains required for this continuation. Defer larger or paid runs until a concrete mechanism change merits another bounded development pilot, or the user explicitly requests replication. Related follow-up belongs in this task; no further model run is presently warranted. Original-source open-model provenance remains separately deferred, as agreed in the prior handoff.

`PORTFOLIO_DISPOSITION.md` records the final treatment of all 80 September 13 catalog families. If historical SymPy claim cleanup is desired, start a separate bounded local Y02–Y05 task. Do not carry the 2,400-case cloud target forward as mandatory work.
