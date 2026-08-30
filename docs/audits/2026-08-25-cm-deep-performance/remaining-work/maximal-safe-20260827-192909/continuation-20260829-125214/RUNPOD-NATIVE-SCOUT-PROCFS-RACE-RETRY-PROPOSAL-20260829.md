# Runpod native-scout procfs-race retry proposal

Date: 2026-08-29  
Status: **not authorized**

## Why a distinct proposal is required

The P5-CLI-corrected authorization is consumed. Pod `pow0qre2q39m4t` passed
all 60 focused testcase elements, completed and independently verified all 144
P5 cells, installed the complete locked native dependency set, and passed the
Linux control probes. The first CaDiCaL worker then failed closed with
`process_tree_measurement_incomplete`; CUDD, d4, and perf did not run. Cleanup
and the separate postflight reconciliation passed.

Code review found a specific false-refusal path: the supervisor excluded zombie
state `Z`, but not Linux terminal states `X`/`x`, and did not recheck state when
`VmRSS` disappeared between its `stat` and `status` reads. The saved evidence
does not record the triggering state, so the terminal-transition explanation is
a supported code-level diagnosis rather than a directly observed kernel-state
claim.

This proposal does not reinterpret an earlier authorization and does not
authorize an automatic replacement.

## Exact additional scope proposed

Authorize **one additional create request and no replacement** for the same
comparative Linux/native readiness workload, with only the procfs supervisor
and its focused regression tests changed:

- the exact 37-file, 5,504,396-byte V6 upload manifest;
- exactly two source identities changed from V5:
  `cmbench/comparative/linux_supervisor.py` and
  `tests/test_cm_comparative_linux_supervisor.py`;
- the existing 13 hash-locked binary wheels and unchanged native dependency
  lock, with source builds allowed only for `ply==3.10` and
  `astutils==0.0.6`;
- exactly 63 focused testcase elements: the previous 60 plus three procfs
  terminal/race/fail-closed regression tests;
- the unchanged frozen 144-cell P5 smoke and its read-only verifier;
- the unchanged native CaDiCaL, CUDD, d4, Linux-control, allocation, source
  identity, and performance-boundary gates;
- no performance ranking, production calibration, publication, or unrelated
  workload;
- one Secure 2-vCPU CPU pod with at least 4 GB RAM, the same pinned Python
  image, 12 GB container storage, zero pod volume, and no network volume;
- the existing 256-KiB bounded resumable transport;
- a 20-minute hard lifetime, cleanup armed before create and due by 18 minutes;
- a `$0.10` phase cap and `$0.20` attributable comparative-campaign cap;
- ownership-only deletion, bounded evidence, and no replacement after any
  local, provider, transfer, bootstrap, dependency, test, P5, procfs, or native
  failure.

The supervisor correction skips `Z`, `X`, and `x` terminal entries. When a
live status snapshot lacks `VmRSS`, it rereads `stat` and counts only a proven
disappearance, group change, or terminal transition as a race. A still-live
owned process without measurable RSS remains a hard incomplete-measurement
failure, and the result then records `whole_tree_rss_measured=false`.

## Local and read-only verification

The exact V6 manifest has no missing local Python imports. Its isolated focused
set passed all 63 tests. The combined comparative, transport, no-reinflation,
native-contract, process-supervisor, and measurement surface passed 133 tests.
The authorization record is absent.

The read-only Runpod preflight at 12:39:45 UTC found both inventories empty,
all prior attempts reconciled, `cpu3c` at high availability and `$0.06/hour`,
and sufficient account headroom. Provider billing still lacked the latest pod
row, so the conservative prior bound remains `$0.0059547362`. The projected
20-minute phase bound is `$0.0233333333`; the projected aggregate bound is
`$0.0292880696`.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| `runpod_native_scout_controller_v6.py` | `5a7ff4b520729d274f6d04f3c5e2a55892d61a967b88445a6c5fe5b60d74eb66` |
| `http_native_scout_preflight_v6.py` | `342b4db4c6501781e8d4a292d7641a9e3b0f05a6dacff5cc72bf51b21ed3e3a9` |
| `http_native_scout_bootstrap_v2.py` | `ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9` |
| `runpod_native_scout_remote_v4.py` | `6d737955b88ede1741db0b6bf7500060b0ca2e3e34c0b49cf3b1c12fb4d029da` |
| `RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V6-20260829.json` | `4883f93e3147bd2aa6c986d99685d20e18974fc6d2da1c3645b269579fe38c2c` |
| 13-wheel lock (`RUNPOD-WHEEL-LOCK.json`) | `8ca822023845a23884555aed6d0f1ce763424fbef9344618ea390157aa1af788` |
| `RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json` | `947696d26d2cfc029d21af2f395faff14b83234d1ddcde3b1b159387f492abb7` |
| P5-attempt final verification | `b110d7c6bdd356ff9fa33f930479557c9593b37491be8e69ab75b4bddb082dd6` |
| V6 local verification receipt | `6647ad840b471afd83ef52b83ce672cecda47671f5048e8fd38e188ddb2e781e` |
| current read-only preflight | `f5944524055fd9960346b888d4309dbd5320793e5e7f9db22c7a218e16fa6759` |

The pinned image remains:

`python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`

## Authorization boundary

`HTTP-NATIVE-SCOUT-PROCFS-RACE-RETRY-AUTHORIZED-20260829.json` does not exist.
The V6 controller refuses to run without a separately hash-bound record. Until
explicit authorization is recorded, only local tests and read-only Runpod
preflight/reconciliation are allowed.

Suggested exact authorization:

> I authorize one additional Runpod procfs-race-corrected native-scout retry
> exactly as specified in
> `RUNPOD-NATIVE-SCOUT-PROCFS-RACE-RETRY-PROPOSAL-20260829.md`, using the exact
> 37-file V6 workload, 256-KiB bounded resumable chunks, one zero-volume Secure
> 2-vCPU CPU pod, a 20-minute limit, $0.10 phase and $0.20 attributable-campaign
> caps, owned cleanup, and no replacement.
