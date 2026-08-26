# CM Three-Lane Continuation Preregistration

Registered: 2026-08-26T18:15:36Z  
Local date: 2026-08-27

## Repository preservation

- Root: `C:\Users\brian\Documents\CM_Computation`
- Branch / HEAD: `main` / `0f833bc389778f7f915deb7acd4499d207e0ec21`
- Accepted `cm_ir.py` SHA-256:
  `ff1633ccabd5392512ec0fdf4531773b7a92e0aa52109c6c681bd99357dcb7d7`
- Preserve all existing website, README, audit, Runpod, `.claude/`,
  `external/`, `tmp/`, and `The Broken Silence.*` work.
- Never read `.env*`, credentials, tokens, or private configuration.
- No dependency installation, external write, cloud resource, commit, or push.

## Lane 1 — Real-workload intake

Create a versioned, dependency-free workload manifest contract and validator so
a future external caller can provide the minimum owner-declared evidence needed
before tracing. The template must not contain invented workload values and must
distinguish metrics approval from replayable-expression/context and external
upload approval.

Acceptance:

- strict required fields, types, enums, nonnegative budgets, and unknown-field
  refusal;
- artifact/query type and output-order contract are explicit;
- metrics trace remains one-in-16 and bounded by default;
- validation output hashes the input and refuses overwrite;
- an incomplete template is retained as a template, not accepted as a real
  workload;
- no ambient telemetry is added to the compiler.

## Lane 2 — DP-R2 temporary-memory policy

Inventory local CLI/configuration, CM compiler/materializer, output-budget
helpers, remote request/protocol, remote worker, and tests. Produce a decision
memo with current behavior, parity gaps, policy options, recommendation,
compatibility/override rules, and a staged implementation/test plan.

Acceptance:

- do not change any default or caller behavior;
- distinguish explicit output bytes from temporary memory;
- require refusal before material allocation and no partial artifact;
- cover local/remote parity, typed outcomes, and callers currently passing
  `None`;
- identify the exact policy choice requiring Brian's approval.

## Lane 3 — DP-R3 audit-tool consolidation

Measure duplicate deterministic evidence/provenance logic before editing.
Consolidate at most one small, clearly repeated mechanism into the existing
`cmbench` reporting/provenance surface. Do not reformat or refactor unrelated
benchmark logic.

Acceptance:

- one coherent attributable change with a pre-change duplicate map;
- deterministic output and refuse-overwrite semantics preserved;
- timing-window and corpus-role semantics unchanged;
- focused tests cover the shared helper and migrated callers;
- quick smoke remains below 30 seconds;
- reject the edit if it increases ambiguity or couples unrelated scripts.

## Validation

- Python 3.13 unit tests for new dependency-free helpers;
- established system pytest for focused and full regression;
- JSON/JUnit/source-hash validation;
- `git diff --check` and final `cm_ir.py` hash check;
- retain negative findings and unresolved external-input requirements.

