# Copy/paste Phase-2 implementation prompt

The following is a complete starter instruction. Use this task for the follow-up because it retains the research context. Suggested available model: GPT-5.6-sol, high reasoning. No new task or model change is performed by this document.

```text
Implement and evaluate exactly the bounded two-opaque-operand cut-fusion experiment specified in:
C:\Users\brian\.codex\worktrees\1949\CM_Computation\docs\audits\2026-09-16-cm-mathematical-speedups\PHASE2_SPEC.md

Read REPORT.md and CANDIDATES.md in the same directory first. Stay in this worktree. Check applicable AGENTS.md, HEAD, git status, and source hashes before edits. Research baseline HEAD was 015f5cbb70b112795c08b61c27924c1ee752b9e9, three ahead of fetched origin/main e35f352a2036db403f5e28ecca2f61550d1db0c7. If relevant source changed, reconcile it before using old static evidence; do not reset or overwrite unrelated work.

Objective: test whether exact four-bit token composition across cuts with at most two structurally identified compound operands reduces the actual whole CSE/CM flat program enough to repay all setup and output costs. This is generic Boolean compilation unless evidence shows a distinct CM benefit. No new runtime opcode or backend is needed.

Current evidence is exploratory, static and exposed: 5,120 local composition checks and 1,310,720 physical-substitution checks passed; 61/64 EPFL cases had potentially cheaper local shells, versus 0/18 C36. There were 2,310 overlapping CM-shell residuals, 1,821 remaining after a one-pass proved-rule control. These are not whole-program savings or timings. The census lacked the new 32-node shell bound. One illustrative absorption identity is already solved by rule-pack then CM; do not claim it as new.

Use existing cm_exprlib.py, cm_token.py, cm_ir.py, bitset_backend.py, cmbench/recognition/rule_pack.py and bounded normalization/comparative APIs. Current CM already has structural UID memoization, compact intern keys, cached hashes, sharing-aware flattening and Boolean identities. Prepared execution, periodic byte masks, resident caches, projected/affine/bucket/component count plans and proved rule packs already exist. Do not reimplement them as speedup discoveries.

Follow every cap, input split, comparator, cost field, proof obligation and stop gate in PHASE2_SPEC.md. Implement an opt-in research pass and harness, leaving default dispatch unchanged. At most 2 leaves, 8 nontrivial cuts plus self per node, 32 interior nodes per shell, 400,000 cut pairs and 1,000,000 interior visits per source, 256 one-batch replacements, no rematching. Exact structural frame equality and explicit polarity/permutation alignment are mandatory. Reject externally shared interiors conservatively. No repeated full compilation per cut. Lower a proved, frozen template pool into existing primitives. Reject final plans lacking at least 2 operations and 10% savings or increasing reported live word buffers; charge failed attempts.

Preserve ordered ambient axes, including variables made irrelevant by rewriting. Test independent scalar and packed truth semantics, all 16 token functions, operand substitution/aliasing, orientation, constants, fanout, invalid input and one-over-limit fallback. Report bigint primitive counts separately from flat instruction counts.

Required controls include direct/prepared R2, CSE, CM, one-pass proved rules, D10 indexed motifs, bounded fixpoint rules, and precompute-full-relation plus exact restrictions. D10 already showed no local oracle headroom, so cheap screening alone is not a new rationale. Charge original preparation for resident sessions and every output byte. Record an available local ABC synthesis control if compatible; if absent, state the limitation without installing tools or claiming external superiority. No scalar-count substitution for full-relation output.

First run the frozen proof/static activation stage. If it fails, stop before timings and report a completed negative experiment. Only after it passes run the sealed local schedule: 24 synthetic development cases, 36 locked synthetic cases, the exposed 82-case panel, q1/q4/q16/q64, seven paired rounds under the fixed single-worker/512-MiB/60-second-case/30-minute-campaign limits. Freeze generator, templates and manifests before timings. Do not tune after consuming confirmation or widen bounds to rescue results. If containment is unavailable, report the missing tool before timing.

Success means every frozen gate passes: locked favorable q64 >=1.10x; exposed EPFL q64 >=1.05x; control and q1 floors; memory <=1.25x plus absolute cap; no semantic or resource failure. Even a pass permits only an opt-in local result. If execute plus required output is not faster, state “no finite amortization break-even.” Keep all refusals and negative outcomes; no invented extrapolated q threshold.

Create new Phase-2 evidence separately from this research folder. Run relevant project checks and review git status/diff. A known Windows historical normalization test rejects the CRLF EPFL corpus: LF-normalized bytes equal HEAD's expected bb98f14a5525a2d869a7ad80e25e879fd176e78ad6d01c51385edc947f2806ac. Do not weaken the validator, normalize the corpus, or claim that historical test passed. Bind actual bytes and parsed semantic identities in new manifests.

I authorize scoped reversible local implementation, exact checks, and this bounded local experiment. No paid/cloud resources, dependency installation, secrets, commits, pushes, publishing, production changes, other-checkout access, or broad new optimizer. Do not spawn subagents unless separately instructed. Preserve unrelated edits. Finish with the gate-by-gate result, changed files, test results, limitations, and the smallest justified next action; a failed gate ends this experiment.
```
