# Runpod native-scout retry amendment proposal

Date: 2026-08-29  
Status: **not authorized**

## Why a separate amendment is required

The one create authorized by `RUNPOD-NATIVE-READINESS-SCOUT-PROPOSAL-20260829.md`
was consumed by pod `84442bdg4m47x8`. The pod was created with the approved
resources, but the frozen controller raised `KeyError` at
`ready["prior_cost_bound_usd"]` after resource inspection and before any source
upload. Its controller and watchdog deleted the pod. Independent postflight
found empty v1/v2 inventories, 404 for all known pod details, exited host guards,
and verified cleanup. The workload did not run.

The prior controller, preflight, authorization, and output directory remain
unchanged. This proposal does not reinterpret the previous authorization or
permit an automatic replacement.

## Exact additional scope proposed

Authorize **one additional create request and no replacement** for the unchanged
comparative Linux/native readiness scout:

- the same exact 30-file, 5,461,757-byte upload manifest;
- the existing 13 hash-locked binary wheels plus the frozen native dependency
  lock, with source builds allowed only for `ply==3.10` and `astutils==0.0.6`;
- exactly 60 focused tests and the frozen 144-cell P5 smoke;
- Linux process-control checks and native CaDiCaL, CUDD, and d4 readiness checks;
- no benchmark performance ranking, production calibration, publication, or
  unrelated workload;
- one Secure 2-vCPU CPU pod with at least 4 GB RAM, the pinned Python image,
  12 GB container storage, zero pod volume, and no network volume;
- a 20-minute hard lifetime, cleanup armed before create and due by 18 minutes;
- a $0.10 retry-phase cap and $0.20 attributable comparative-campaign cap;
- ownership-only deletion, bounded source/evidence transfer, and no replacement
  after any local, provider, bootstrap, dependency, test, or native-tool failure.

The retry preflight carries forward the larger of the first attempt's observed
billing and its conservative `$0.000147912` estimate. It rechecks empty v1/v2
inventories, all prior evidence, current offers, account readiness, and both
caps before any POST. Delayed billing remains possible.

## Corrected transport

The correction makes the preflight/controller return-value contract explicit:
the preflight publishes top-level `prior_cost_bound_usd`, and the controller
passes that value through its actual-resource and aggregate-budget validation.
An integration regression test exercises that exact interface. The retry
controller refuses to run while its separate authorization file is absent.

Frozen SHA-256 values:

| Artifact | SHA-256 |
|---|---|
| `runpod_native_scout_controller_v2.py` | `443332c19660b6a65611fcdb453fda991c0e033ab9527029ba5997595f712fff` |
| `http_native_scout_preflight_v2.py` | `3eea47ba3d4e073c0237fc04af7352d9c586322f8c72cf8b70036cb1d8fd483e` |
| `RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V2-20260829.json` | `3236c5f7415852df030d128d2e8cb07953f12eac4c9ca755beed55ad6a814364` |
| `RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json` | `947696d26d2cfc029d21af2f395faff14b83234d1ddcde3b1b159387f492abb7` |
| `http_native_scout_bootstrap_v1.py` | `7b997d3b36307f501875290369f50fb661f60fa516b56c214f67986df16d0646` |
| `runpod_native_scout_remote.py` | `1f1d22093a5bf9a37c60b1fa35e280088a3e3b683b859ccdd9915033c559aaa7` |
| first-attempt final verification | `944ed020b1f10093e01e61394b5c775e4d076c66bb5d6fb072bc401f9afd9393` |

The pinned container image remains:

`python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`

## Authorization boundary

No authorization record exists for this amendment. A later authorization must
name this proposal and approve one additional create with no replacement. Until
then, only read-only local and Runpod preflight/reconciliation work is allowed.

Suggested exact authorization:

> I authorize one additional Runpod native-scout retry exactly as specified in
> `RUNPOD-NATIVE-SCOUT-RETRY-AMENDMENT-PROPOSAL-20260829.md`, using the unchanged
> 30-file workload, one zero-volume Secure 2-vCPU CPU pod, a 20-minute limit,
> $0.10 retry-phase and $0.20 attributable-campaign caps, owned cleanup, and no
> replacement.
