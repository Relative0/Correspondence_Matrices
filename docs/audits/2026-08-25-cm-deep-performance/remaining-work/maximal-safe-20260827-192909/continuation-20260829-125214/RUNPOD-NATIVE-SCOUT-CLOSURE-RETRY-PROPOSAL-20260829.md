# Runpod native-scout dependency-closure retry proposal

Date: 2026-08-29  
Status: **not authorized**

## Why a distinct proposal is required

All three native-scout create authorizations are consumed. The third pod proved
that the 256-KiB resumable transport works: all eleven chunks of the frozen
2,831,254-byte payload were acknowledged, the complete payload hash matched,
and the worker started. The focused test phase then failed because the 30-file
manifest omitted local Python dependencies. No P5 smoke or native-tool check
started. The pod was deleted and independently reconciled.

This proposal does not reinterpret any earlier authorization and does not
authorize an automatic replacement.

## Exact additional scope proposed

Authorize **one additional create request and no replacement** for the same
comparative Linux/native readiness workload, with only the source package and
failure-evidence handling corrected:

- the exact 37-file, 5,500,977-byte V5 upload manifest;
- the original 30 files plus seven local dependency-closure files:
  `cmbench/backends/__init__.py`, `cmbench/backends/bitset_engine.py`,
  `scripts/cm_benchmark_provenance.py`, `scripts/cm_process_supervisor.py`,
  `cmbench/reporting/__init__.py`, `cmbench/reporting/provenance.py`, and
  `cmbench/reporting/summary_tables.py`;
- the existing 13 hash-locked binary wheels and frozen native dependency lock,
  with source builds allowed only for `ply==3.10` and `astutils==0.0.6`;
- exactly 60 focused testcase elements, the frozen 144-cell P5 smoke, Linux
  process-control checks, and native CaDiCaL, CUDD, and d4 readiness checks;
- no performance ranking, production calibration, publication, or unrelated
  workload;
- one Secure 2-vCPU CPU pod with at least 4 GB RAM, the same pinned Python
  image, 12 GB container storage, zero pod volume, and no network volume;
- 256-KiB bounded resumable chunks with exact offsets, per-chunk hashes,
  idempotent duplicate handling, and complete-payload validation;
- a 20-minute hard lifetime, cleanup armed before create and due by 18 minutes;
- a $0.10 phase cap and $0.20 attributable comparative-campaign cap;
- ownership-only deletion, bounded evidence, and no replacement after any
  local, provider, transfer, bootstrap, dependency, test, or native-tool failure.

The read-only preflight carries forward the larger observed-or-estimated bound
for the three failed scouts: `$0.002574206`. At the current `$0.06/hour` offer,
the aggregate projected bound is `$0.025907539`. Both v1 and v2 inventories
were empty at 11:10:57 UTC. Billing for the third pod still lagged, so the
conservative elapsed-time bound is retained.

## Dependency and isolation correction

The new AST-based local import-closure audit reports no missing local module for
all 34 Python files in the V5 manifest. An independent temporary-directory
test copied only the 37 manifest files, removed `PYTHONPATH`, and executed all
60 focused tests successfully. Earlier V3 and V4 draft manifests are preserved
because they demonstrate the transitive dependencies found before V5 closed.

The workload, test selection, native tools, dependency versions, timeouts,
resource request, and performance-claim boundary are unchanged.

## Evidence-handling correction

The revised remote wrapper distinguishes pytest suite metadata from actual
JUnit testcase elements. On the failed third run, these were respectively
180 tests/22 failures and 60 testcase elements/7 failed elements because pytest
expanded subtests in suite metadata. Acceptance uses exactly 60 testcase
elements and zero failed, errored, or skipped elements while preserving both
views.

Source-after identity is now attempted independently even when an earlier phase
fails. Missing P5/native artifacts are recorded as bounded section errors. The
controller stores verified partial evidence before reporting a remote workload
failure, so a missing later artifact cannot mask the primary failure again.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| `runpod_native_scout_controller_v4.py` | `5b2d2bf0d88f2034d6c1881aca40654b59fda9651aa03f13adda681bc10b4899` |
| `http_native_scout_preflight_v4.py` | `8ff414e254723677c598d968c1adb18ece92788daa32cd54842150e1257cc857` |
| `http_native_scout_bootstrap_v2.py` | `ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9` |
| `RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V5-20260829.json` | `f2550901addb878f6d36bbb55fee98b8ae18732958aa3a962b898910f7795f8e` |
| 13-wheel lock (`RUNPOD-WHEEL-LOCK.json`) | `8ca822023845a23884555aed6d0f1ce763424fbef9344618ea390157aa1af788` |
| `RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json` | `947696d26d2cfc029d21af2f395faff14b83234d1ddcde3b1b159387f492abb7` |
| `runpod_native_scout_remote_v2.py` | `e5076a3caaa5c152f060780736899a51d6f0e10e9471130d2a840b08792daa1d` |
| `scripts/cm_manifest_dependency_audit.py` | `3037c6b429ea7f860c0b7451d0bd2877d8c32ed3c8018874e40025e58ce49d9b` |
| third-attempt final verification | `56082cf176eed8ee2266d4ab45c09b044c690ff65fb274aba08697e49b92af57` |
| current read-only preflight | `be091309ac547fdde2b03e8fc54a2cf65c22ff7ec65ec0319d1ce5e597abe2e1` |

The pinned image remains:

`python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`

## Authorization boundary

`HTTP-NATIVE-SCOUT-CLOSURE-RETRY-AUTHORIZED-20260829.json` does not exist. The
V4 controller refuses to run without a separately hash-bound record. Until
explicit authorization is recorded, only local tests and read-only Runpod
preflight/reconciliation are allowed.

Suggested exact authorization:

> I authorize one additional Runpod dependency-closed native-scout retry
> exactly as specified in
> `RUNPOD-NATIVE-SCOUT-CLOSURE-RETRY-PROPOSAL-20260829.md`, using the exact
> 37-file workload, 256-KiB bounded resumable chunks, one zero-volume Secure
> 2-vCPU CPU pod, a 20-minute limit, $0.10 phase and $0.20
> attributable-campaign caps, owned cleanup, and no replacement.
