# Runpod native-scout chunked-retry proposal

Date: 2026-08-29  
Status: **not authorized**

## Why another distinct proposal is required

The original scout create and its one separately authorized retry are both
consumed. The original stopped before upload because of a local preflight field
mismatch. The corrected retry passed resource validation and reached bootstrap
health, but timed out during its 2.83-MB monolithic payload request. It never
sent the worker-start request. Both pods were independently verified deleted,
and neither workload ran.

This proposal does not reinterpret either authorization and does not authorize
an automatic replacement.

## Exact additional scope proposed

Authorize **one additional create request and no replacement** for the same
comparative Linux/native readiness workload:

- the unchanged exact 30-file, 5,461,757-byte upload manifest;
- the existing 13 hash-locked binary wheels and frozen native dependency lock,
  with source builds allowed only for `ply==3.10` and `astutils==0.0.6`;
- exactly 60 focused tests, the frozen 144-cell P5 smoke, Linux process-control
  checks, and native CaDiCaL, CUDD, and d4 readiness checks;
- no performance ranking, production calibration, publication, or unrelated
  workload;
- one Secure 2-vCPU CPU pod with at least 4 GB RAM, the same pinned Python
  image, 12 GB container storage, zero pod volume, and no network volume;
- a 20-minute hard lifetime, cleanup armed before create and due by 18 minutes;
- a $0.10 phase cap and $0.20 attributable comparative-campaign cap;
- ownership-only deletion, bounded evidence, and no replacement after any
  local, provider, transfer, bootstrap, dependency, test, or native-tool failure.

The read-only preflight carries forward the larger observed-or-estimated cost of
both failed attempts: `$0.001164632`. At the current `$0.06/hour` offer, the
aggregate projected bound is `$0.024497966`.

## Chunked transfer correction

The payload and source hashes remain unchanged. Only the token-gated transport
changes:

- at most 256 KiB per upload request, yielding eleven requests for the frozen
  2.83-MB payload;
- exact offset and SHA-256 on every chunk;
- rejection of gaps, overlaps with different bytes, oversize chunks, and data
  beyond the frozen total;
- idempotent acceptance of an identical duplicate chunk;
- a read-only upload-status route so a response timeout can be reconciled
  without blindly resending ambiguous data;
- validation against the complete frozen payload size and SHA-256 before the
  worker-start route can succeed;
- a five-minute total upload deadline within the 20-minute pod horizon;
- a 45-second server connection timeout and at most 60 seconds per bounded
  client chunk request.

Offline regression tests cover ordered transfer, conflicting/out-of-order
refusal, idempotent duplicate acceptance, timeout-after-acceptance recovery, the
actual eleven-chunk payload, exact full-payload validation, and the absent
authorization gate.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| `runpod_native_scout_controller_v3.py` | `3a877a708c9be8bc2cbbddb4cc6f37ac3a00138dd0bb2e4b0f4ccc24e415a5c3` |
| `http_native_scout_preflight_v3.py` | `abc431f18224734d723fbaed658720a5320d2a010fa4473a01417f4b96bf7abb` |
| `http_native_scout_bootstrap_v2.py` | `ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9` |
| `RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V2-20260829.json` | `3236c5f7415852df030d128d2e8cb07953f12eac4c9ca755beed55ad6a814364` |
| `RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json` | `947696d26d2cfc029d21af2f395faff14b83234d1ddcde3b1b159387f492abb7` |
| `runpod_native_scout_remote.py` | `1f1d22093a5bf9a37c60b1fa35e280088a3e3b683b859ccdd9915033c559aaa7` |
| consumed-retry final verification | `c1d6203503bad1912afd7207c973eb122e6adc497e83f17cf1b4081b54e2144f` |

The pinned image remains:

`python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`

## Authorization boundary

`HTTP-NATIVE-SCOUT-CHUNKED-RETRY-AUTHORIZED-20260829.json` does not exist. The
V3 controller refuses to run without a separately hash-bound record. Until
explicit authorization is recorded, only local tests and read-only Runpod
preflight/reconciliation are allowed.

Suggested exact authorization:

> I authorize one additional Runpod native-scout chunked retry exactly as
> specified in `RUNPOD-NATIVE-SCOUT-CHUNKED-RETRY-PROPOSAL-20260829.md`, using
> the unchanged 30-file workload, 256-KiB bounded resumable chunks, one
> zero-volume Secure 2-vCPU CPU pod, a 20-minute limit, $0.10 phase and $0.20
> attributable-campaign caps, owned cleanup, and no replacement.
