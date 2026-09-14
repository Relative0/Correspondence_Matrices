# Implementation handoff

The attribution/corpus/control audit is complete within its local scope. The next engineering objective is to implement and validate the **matched raw-factorized versus prepared-CM repeated-perturbation runner**, using `CM_BIOLOGY_EXPERIMENT_SPEC.md`. Its performance, attribution and heldout gates have not been run or passed. No CM-specific biological speedup is currently demonstrated.

## Repository and custody

- Worktree: `C:/Users/brian/Documents/CM_Computation/tmp/cm-consolidation-20260914`.
- Baseline local main: `b3f10bc582f0c2a59a0fe7513af88199a4f65c56`; this audit consists of uncommitted new files only.
- Original retained evidence root: `C:/Users/brian/Documents/CM_Computation`, dirty preservation branch. Read only. The full biology input freeze/archive and several original September 11 raw panels/reports were deliberately not integrated by consolidation.
- Audit: `docs/audits/2026-09-14-cm-benchmark-attribution/`. The manifests bind both new artifacts and the relevant source surface. The claim/statistical ledgers record exact retained-path dependencies. Do not assume this worktree alone contains every historical input.
- All 22 closed model bytes and their new parsimonious CNFs are copied/hash-bound under `control-inputs/`; do not confuse those successor CNFs with historical campaign inputs.

## Decisions that must carry forward

1. Historical `bnet_cm_scalar` is an oracle. Future arm is `bnet_scalar_oracle`; use the new result schema and explicit mechanism attribution. Preserve old labels only for frozen replay.
2. All 22 closed models are in scope, including larger models unsupported by exhaustive/packed arms. Open exports retain free-input semantics until a separate validated input contract exists.
3. Clamps replace equations; conditions retain them. A simple `.count(fixed)` on the original formula implements conditions and is insufficient for clamps.
4. Raw and CM arms use the same factorized algorithm, caches and backend, and both may reuse preparation. Separate ingress and canonicalization cost from warm evaluation. Identical downstream flat programs cannot support a distinct warm-representation claim.
5. Repetition/query/variant counts do not create independent families. Current heldout-candidates are exposed internal-validation candidates. No paid proposal before local correctness and performance gates yield a concrete hash-bound plan and quote.

## Source seams and remaining implementation order

Start with `cmbench/biology_controls.py` (`encode_fixed_points`, `bnet_scalar_oracle`, `native_fixed_points`, `is_fixed_point`) and `cmbench/backends/exact_controls_v2.py`. The existing native control uses CaDiCaL through installed `python-sat==1.8.dev20` on Windows. Local Ubuntu AEON is 1.4.2; native binaries are pinned to the actual local WSL runtime hashes in `NATIVE_CONTROL_RESULTS.json`. Do not substitute solvers or install unpinned dependencies.

Implement a raw BNet AST-to-FlatProgram path with real constant loads and stable target indices. Implement a distinct CMIRBuilder ingress with the same operator/equality semantics. Retain per-equation roots to support clamp replacement. Feed both into the identical `FactorizedCountPlan` evaluator and compare normalized plan topology/hashes. Build witness retrieval/validation and complete result rows; counters requiring companion witnesses must name and charge that provider.

Add a session supervisor with nonoverlapping construction/preparation/query phases, process-tree CPU and peak memory, per-session deadlines, bounded output collection and explicit failure taxonomy. The old campaign worker's parent-only resource accounting is insufficient. Consume `QUERY_SCHEDULES.json` exactly; distinguish selected-function support from whole-network support and live factor width. Extend the exhaustive auxiliary-extension and clamp/condition tests to both translators before timing. Then execute the specification's bounded local development pilot and freeze a feasible larger local plan. Follow-up implementation belongs in this task because it reuses the corpus mappings, semantics, evidence and authorization boundaries; no new task setup is necessary.

Original-source provenance remains unresolved for open-model biological roles, summary discrepancies 039/094 and casefold candidates 098/173. A later read-only investigation should recover original annotations/publications and add versioned evidence. Do not repair names, add equations or classify broken translations by guessing. This provenance work is independent of implementing the validated closed-model runner and need not block it.

## Reproduction

Use the project virtualenv, from the worktree above. Existing source/test files are immutable historical baselines for this audit; regenerate only the new successor output directory.

```powershell
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' docs/audits/2026-09-14-cm-benchmark-attribution/corpus_audit.py --evidence-root 'C:/Users/brian/Documents/CM_Computation' --self-test
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' docs/audits/2026-09-14-cm-benchmark-attribution/statistical_analysis.py --retained-root 'C:/Users/brian/Documents/CM_Computation'
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' scripts/cm_biology_control_audit.py --phase prepare --evidence-root 'C:/Users/brian/Documents/CM_Computation'
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' docs/audits/2026-09-14-cm-benchmark-attribution/prepare_query_schedules.py
wsl.exe -d Ubuntu-24.04 --exec /opt/cm-successor-replay-003/bin/python /mnt/c/Users/brian/Documents/CM_Computation/tmp/cm-consolidation-20260914/scripts/cm_biology_control_audit.py --phase native
```

Windows sandbox access to WSL required a reviewed escalation in this task. It was approved for local checks; no permission settings were changed. Existing binaries/packages were used and verified, with no network installation. Reproduction overwrites new diagnostic JSON and changes its elapsed-time fields/hashes; preserve the delivered manifest snapshot before rerunning and produce a successor version if you need both records.

Focused/broad test commands and baseline limitations are in `TEST_RESULTS.md`. Before a future commit, review all untracked files deliberately and stage only the requested audit surface. The current task does not authorize commits, pushes, publications, cloud resources, credentials or external mutations.

## Recommended continuation

Nothing remains required to produce this audit and implementation specification. Pursue the matched raw/CM runner next in this task when implementation is requested; `gpt-5.6-sol` at high reasoning is a suitable available model for the bounded code/test work, with independent review for the attribution design. Actual app cost savings are not measured. Defer open-model source recovery until an open-input benchmark is prioritized. No new task or model run is needed merely to restate the completed audit.
