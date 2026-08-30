# RunPod P7 dependency-closed functional-scout V2 retry proposal

Date: 2026-08-30
Status: proposed; **not authorized**
Performance measurement/ranking: false

## Why a retry is needed

The consumed V1 create reached Linux but stopped during pytest collection because
its upload manifest omitted local imports. It also omitted every source file
referenced by the authoritative freeze. No offline-gate verification or P7 cell
ran. The failure and cleanup are preserved in
`RUNPOD-P7-FUNCTIONAL-SCOUT-V1-RESULT-AUDIT-20260830.md`.

V2 uses the independently isolated and dependency-closed runner package described
by `P7-LINUX-ISOLATED-RUNNER-GATE-AUDIT-V2-20260830.md`.

## Exact package

- 96 files and 19,484,163 uncompressed source/data bytes.
- Upload manifest: `RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json`,
  23,410 bytes, file SHA-256
  `9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`.
- Logical source-manifest SHA-256:
  `5eb8b349e0b7c431f97dc8b7ed8723d42f3443caa6b2c1a4eb753be05c6adae1`.
- Upload ZIP: `RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V2-20260830.zip`,
  3,197,013 bytes, SHA-256
  `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
- The package contains all 57 unique source files named by P6 V4, offline gate
  V6, the V2 runner/worker/package builder, 42 focused tests, and the existing
  hash-locked binary-only dependency requirements.
- It contains no `.env*`, credential, token cache, private key, database, git
  metadata, prior run evidence, native executable, or source-build input.
- Its AST import-closure audit, isolated focused tests, offline-gate verification,
  byte rehash, and nonmutating verifier all pass locally.

## Exact functional workload

1. Verify the complete payload and every source identity.
2. Install only the 13 already hash-locked binary wheels; refuse source builds
   and system-package installation.
3. Run the 42 focused tests with zero failures, errors, or skips.
4. Verify P6 V4 and offline gate V6 under pinned Linux Python 3.13.15 amd64.
5. Run two frozen development cases and two functional blocks per policy:
   - P7 IR: four arms, 16 fresh-process cells;
   - P7 complete relation: five arms, 20 fresh-process cells.
6. Require 36 distinct owned worker processes, exact independent-oracle equality,
   positive task-total/RSS evidence, complete process-group cleanup, source-before/
   after equality, ledger reconciliation, and read-only output verification.

Both plans retain `profile=functional`, `performance_measurement=false`, and
`performance_claim_permitted=false`. Durations are retained only as operational
evidence that the timer and process supervision work; no arm ratio, rank, or
performance conclusion may be reported.

## Resource, transport, budget, and cleanup boundary

- One Secure 2-vCPU/4-GB CPU pod using the pinned Python 3.13.15 amd64 image.
- 12 GB ephemeral container storage; integer-zero pod volume; no network volume.
- Exact HTTP ports `8080/http` and `8081/http`.
- Maximum lifetime 1,200 seconds; watchdog cleanup at 1,080 seconds.
- 256-KiB bounded resumable upload chunks and full-payload hash before start.
- Phase cost below `$0.10`; conservative attributable-campaign total below
  `$0.20`, including the V1 failure, earlier recorded reserve, and a `$0.01`
  storage/billing reserve.
- Exactly one create, owned deletion on every outcome, empty v1/v2 inventories,
  absent owned pod details, exited guards/watchdog, bounded evidence retrieval,
  and delayed-billing reconciliation.
- No replacement, retry, next shard, comparative timing, source change, native
  build, publication, commit, or production change is included.

## Frozen operational files

- Preflight `http_p7_functional_scout_preflight_v2.py`:
  `5179e90d9e532238c94746353296e72d1b8f0778f66fc7d9587238f2f9652ae5`.
- Remote wrapper `runpod_p7_functional_scout_remote_v2.py`:
  `5674380f0410e5ad7dac283bebccf2ba82cde6b1db4499a8b15d9a7ff0d7e31e`.
- Controller `runpod_p7_functional_scout_controller_v2.py`:
  `7e92a91542463a25959e5796d7b427a91c93a70696069438ded2d7bd3c110aeb`.
- Bootstrap `http_native_scout_bootstrap_v2.py`:
  `ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9`.

The controller is fail-closed while
`HTTP-P7-FUNCTIONAL-SCOUT-V2-AUTHORIZED-20260830.json` is absent. Authorization,
if granted, must name this proposal and the exact hashes above. This proposal
does not authorize a RunPod create, upload, purchase, or external write.

