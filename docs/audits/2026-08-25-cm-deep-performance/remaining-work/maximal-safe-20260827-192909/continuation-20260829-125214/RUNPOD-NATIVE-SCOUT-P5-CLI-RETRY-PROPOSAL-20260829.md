# Runpod native-scout P5 CLI retry proposal

Date: 2026-08-29  
Status: **not authorized**

## Why a distinct proposal is required

All four native-scout create authorizations are consumed. The fourth pod proved
the 37-file dependency closure: all 60 focused testcase elements passed and the
source-before/source-after identities matched. P5 then exited before executing
because the frozen remote wrapper passed `--output-dir`, while
`cm_comparative_smoke.py run` requires `--output`. The native readiness scout
did not start. The pod was deleted and independently reconciled.

This proposal does not reinterpret any earlier authorization and does not
authorize an automatic replacement.

## Exact additional scope proposed

Authorize **one additional create request and no replacement** for the same
comparative Linux/native readiness workload, with only the P5 invocation and
its evidence interpretation corrected:

- the unchanged exact 37-file, 5,500,977-byte V5 upload manifest;
- the existing 13 hash-locked binary wheels and frozen native dependency lock,
  with source builds allowed only for `ply==3.10` and `astutils==0.0.6`;
- exactly 60 focused testcase elements;
- the same frozen 144-cell P5 smoke, invoked with its declared `--output`
  argument, followed by its read-only `verify --output` command;
- the unchanged Linux process-control and native CaDiCaL, CUDD, and d4
  readiness checks;
- no performance ranking, production calibration, publication, or unrelated
  workload;
- one Secure 2-vCPU CPU pod with at least 4 GB RAM, the same pinned Python
  image, 12 GB container storage, zero pod volume, and no network volume;
- the existing 256-KiB bounded resumable transport;
- a 20-minute hard lifetime, cleanup armed before create and due by 18 minutes;
- a $0.10 phase cap and $0.20 attributable comparative-campaign cap;
- ownership-only deletion, bounded evidence, and no replacement after any
  local, provider, transfer, bootstrap, dependency, test, P5, or native failure.

The read-only preflight carries forward the larger observed-or-estimated bound
for the four failed scouts: `$0.004289399`. At the current `$0.06/hour` offer,
the aggregate projected bound is `$0.027622733`. Both v1 and v2 inventories
were empty at 11:29:37 UTC. Billing for the fourth pod still lagged, so its
conservative elapsed-time/storage-reserve bound is retained.

## P5 and schema correction

The exact V5 bundle was copied to an isolated temporary directory with no
project `PYTHONPATH`. The corrected P5 command completed all 144 planned cells,
all with status `ok`; the separate read-only verifier reported 144 cells,
25 files, no mutation, and status `passed`.

The wrapper and controller now read `observed_cells`, `statuses`, completeness,
tail state, and missing/unexpected/unfinished lists from P5's declared nested
`reconciliation` object. The previous top-level interpretation would have
rejected valid evidence even after correcting the command, so both issues are
fixed together. Offline success fixtures exercise the controller against the
actual saved P5 summary schema.

The native-scout command was separately checked against its parser: it correctly
uses `--output-dir` and `--dependency-lock`. Native summary, dependency,
Linux-control, CaDiCaL, CUDD, d4, performance-boundary, allocation, and source
identity gates remain unchanged.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| `runpod_native_scout_controller_v5.py` | `4d08ae9ca02431e87f10516e1f10ec115b9285a773a1a1227d7804a700ea24e9` |
| `http_native_scout_preflight_v5.py` | `387ecef8126edb34773af99b6b55ded581f9d714f66a2a2d2a6082a83290cfc6` |
| `http_native_scout_bootstrap_v2.py` | `ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9` |
| `RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V5-20260829.json` | `f2550901addb878f6d36bbb55fee98b8ae18732958aa3a962b898910f7795f8e` |
| 13-wheel lock (`RUNPOD-WHEEL-LOCK.json`) | `8ca822023845a23884555aed6d0f1ce763424fbef9344618ea390157aa1af788` |
| `RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json` | `947696d26d2cfc029d21af2f395faff14b83234d1ddcde3b1b159387f492abb7` |
| `runpod_native_scout_remote_v3.py` | `6d737955b88ede1741db0b6bf7500060b0ca2e3e34c0b49cf3b1c12fb4d029da` |
| fourth-attempt final verification | `58fdb715a06d3665708b0ae0ddaf31f4d85acc4293a7f34e3a45d01b9b5eaa57` |
| current read-only preflight | `4d6554f2208f8478fb2fa7a4b254d5a2dd2e4255f50ff229e18e85f76df87ce0` |

The pinned image remains:

`python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`

## Authorization boundary

`HTTP-NATIVE-SCOUT-P5-CLI-RETRY-AUTHORIZED-20260829.json` does not exist. The
V5 controller refuses to run without a separately hash-bound record. Until
explicit authorization is recorded, only local tests and read-only Runpod
preflight/reconciliation are allowed.

Suggested exact authorization:

> I authorize one additional Runpod P5-CLI-corrected native-scout retry exactly
> as specified in `RUNPOD-NATIVE-SCOUT-P5-CLI-RETRY-PROPOSAL-20260829.md`,
> using the unchanged exact 37-file workload, 256-KiB bounded resumable chunks,
> one zero-volume Secure 2-vCPU CPU pod, a 20-minute limit, $0.10 phase and
> $0.20 attributable-campaign caps, owned cleanup, and no replacement.

