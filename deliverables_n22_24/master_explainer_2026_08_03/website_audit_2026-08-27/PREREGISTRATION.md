# CM master-explainer evidence reconciliation preregistration

Date: 2026-08-27  
Repository: `C:\Users\brian\Documents\CM_Computation`  
Branch / starting HEAD: `main` / `4dbfffc1db749e85401d533c5a07cb529a41eb37`

## Mission and frozen acceptance rules

Audit every numeric and categorical website result against the newest accepted
repository artifact for that claim, add the accepted 2026-08-26/27 cache,
family, context, tracing, workload-intake, dependency-feasibility,
temporary-memory, provenance-consolidation, and validation findings, and
regenerate the four audience pages only from authored sources.

The following distinctions are frozen before edits:

- B1/E3 and EPFL remain CM/CSE-flat parity evidence; symmetric V3 is a
  separate workload-specific bare-program result.
- Bare programs, the public wrapper, direct kernels, complete explicit output,
  BDD build/restriction/query/extraction, and synthetic versus real workloads
  remain separate artifacts and timing boundaries.
- An increased test count cannot supersede a benchmark ratio. A smoke cannot
  supersede a preregistered representative study.
- Synthetic all-hit cache, family, context, and trace mechanics are hypothesis
  or reliability evidence, not production-workload evidence.
- RP-D0 is a dependency-resolution refusal. Numba, `dd.cudd`, native
  restriction, and native performance remain untested rather than failed.
- The proposed temporary-memory profiles are future approval candidates; no
  current default or product policy changed.
- Current CM keys are engineering identity under documented normalization and
  collision assumptions, not a theorem of global semantic canonicality.

## Repository preservation

Starting `git status --short` contained only the explicitly excluded local-only
`.claude/`, `external/`, `tmp/`, generated `.pytest*` scratch directories, and
`The Broken Silence.html` / `The Broken Silence.zip`. They are outside this
audit: do not read, modify, stage, delete, or attribute them. Do not read
`.env*`, token stores, credentials, or private configuration. Do not install,
commit, push, deploy, publish, use cloud resources, or make external writes.

No repository or ancestor `AGENTS.md` was found by the scoped search. The
user-supplied global instructions govern this work.

## Starting toolchain

- virtual environment: Python 3.13.5; numpy 2.3.2, sympy 1.14.0, pandas 2.3.2,
  dd 0.6.0, requests 2.34.2; pytest absent
- system environment: Python 3.10.11; numpy 2.2.6, sympy 1.14.0, pandas 2.3.2,
  pyeda 0.29.0, dd 0.5.7, requests 2.32.5, pytest 9.0.2
- Node v22.18.0; npm 10.9.3

## Planned validation

Build twice from identical authored sources and require byte-identical hashes
for generated data and all four HTML pages; parse both JSON files; byte-compile
the builder and audit tool; check shared JavaScript with Node; parse every page
with Python's HTML parser; validate claim-token uniqueness, provenance, source
fields, stale-string absence, JUnit/JSON/CSV inputs, focused tests, the complete
suite, `git diff --check`, final hashes, and final status. Inspect every page in
the in-app browser at desktop and narrow viewport where the browser permits.

