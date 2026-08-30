# RunPod P7 functional-scout V1 result audit

Date: 2026-08-30
Outcome: failed before offline-gate verification or any P7 cell
Authorization: consumed; no replacement is implied by this audit

## What ran

The controller created one matching Secure CPU pod, `1xh6csc4oxy067`, at
`$0.06/hour`. The resource record reports two vCPUs, 4 GB RAM, the pinned
Python 3.13.15 image, 12 GB container storage, integer-zero pod storage, no
network volume, and the declared HTTP ports. Ten bounded transport chunks were
accepted, the 152-file payload rehashed, and the remote wrapper started.

Pytest then stopped during collection. Three test modules could not import
`cmbench.recognition.features` through `cmbench.recognition.blif`. The JUnit
record contains three testcase elements, all collection errors. The offline
gate, the 16 IR cells, and the 20 complete-relation cells did not run. No timing,
RSS comparison, semantic result, ranking, or P7 Linux supervision result was
accepted.

## Package defect

The V1 upload manifest was not dependency-closed. The repository's AST import
audit identifies four missing local runtime files:

- `cmbench/backends/__init__.py`;
- `cmbench/backends/bitset_engine.py`;
- `cmbench/recognition/__init__.py`; and
- `cmbench/recognition/features.py`.

It also included none of the 57 unique source files referenced by the
authoritative V4 freeze. Even if collection had passed, full freeze/source
verification would therefore have refused. V1's 152-file count was inflated by
unrelated native-scout and d4 build inputs and was not evidence of closure.

## Evidence and cleanup

- Saved `RUN.json` SHA-256:
  `6827da63c6a1b22c3617fcf9d55a4300d72b52e7f58b8f1bd0cba86be935aa9f`.
- Retrieved evidence ZIP: 23,437 bytes, SHA-256
  `0cd9a0462b719d6c860ca291dc76ab3e9441040453bc967890ce9f6688e4f62b`.
- Source-before and source-after identities match for all uploaded V1 files.
- Estimated compute cost: `$0.002207883052031199`.
- Controller cleanup found both inventories empty and both v1/v2 pod-detail
  routes returned 404 for the owned pod.

The V1 package, controller, output, and failure evidence remain preserved. They
must not be replayed or described as a successful W1/W3 gate.

