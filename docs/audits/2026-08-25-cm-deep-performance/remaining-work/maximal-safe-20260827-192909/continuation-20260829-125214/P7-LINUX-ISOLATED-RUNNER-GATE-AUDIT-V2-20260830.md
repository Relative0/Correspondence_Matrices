# P7 isolated-runner and package gate audit V2

Date: 2026-08-30
Performance measurement: false

## Runner corrections after V1

The V2 runner schema closes issues found during postflight review:

- every cell identity now binds the freeze, case and cluster, source and member
  hashes, concrete arm configuration, output contract, lifecycle, admitted-CPU
  class, exact supervisor-limit profile, order row, block/case/arm position, and
  worker-source manifest;
- worker requests contain the complete immutable cell and refuse forged or extra
  identities before loading a case;
- IR task-total timing begins before source loading/BLIF translation and ends
  after the declared artifact is complete; semantic evaluation remains outside;
- complete-relation task-total timing includes source loading, preparation,
  execution, extraction, and artifact delivery, with oracle comparison outside;
- independent oracle records bind the case/source/member/root/support/width,
  encoding, result, generator sources, and package identity;
- resume refuses a partial ledger tail hidden by a later segment;
- actual supervisor limits must hash to the frozen cell profile; and
- executable code plus the active case source are rechecked between cells, with
  full source identity retained before and after the shard.

## Local and isolated verification

- Focused local run: 42 tests passed and 26 subtests passed.
- The focused set covers deterministic clocks, request refusal before source
  execution, timeout, semantic mismatch, cleanup failure, malformed/duplicate/
  nonfinite JSON, resource-profile mismatch, oracle tampering, interrupted resume,
  partial-tail fencing, primary metric requirements, and the real worker CLI.
- Offline gate V6 prepares all 58 P7 cases, verifies both frozen policy bindings,
  and repeats the two-case nine-arm no-duration correctness dry run.
- Dependency-closed runner package V2 contains 96 files and 19,484,163 source
  bytes. Its deterministic ZIP is 3,197,013 bytes with SHA-256
  `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
- Logical source-manifest SHA-256:
  `5eb8b349e0b7c431f97dc8b7ed8723d42f3443caa6b2c1a4eb753be05c6adae1`.
- The AST closure audit reports no missing local Python import.
- Extraction into a temporary source tree passed all 42 focused tests and
  independently verified offline gate V6. The read-only package verifier passes
  all manifest, source, bundle, closure, checksum, and saved-evidence checks.
- The package includes all 57 unique source files referenced by V4 and excludes
  `.env*`, credentials, keys, databases, git metadata, and earlier run evidence.

## Remaining gate

The revised runner has not completed end-to-end Linux `/proc` supervision. A
single dependency-closed 36-cell functional retry is the narrow next step. It
is not a timing campaign and cannot support an arm ranking. Its controller is
fail-closed until a new exact authorization record exists.

