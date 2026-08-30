# Runpod native-scout host-preflight amendment proposal

Date: 2026-08-29  
Status: **not authorized; blocked until host AC power is connected**

## Why an amendment is required

Brian authorized the exact V6 procfs-race retry. Its controller created only an
empty local output directory and then refused in the Windows host-awake guard
because `ACLineStatus=0`. The guard wraps `run()`, so the controller performed
no Runpod request, did not reach the create POST, and did not consume the one
cloud-create authorization.

Review then found a second deterministic pre-create refusal in the frozen V6
controller: it still expected the V5 aggregate source byte count `5,500,977`,
while the authorized V6 manifest correctly records `5,504,396`. The exact V6
controller therefore cannot safely be replayed unchanged even after AC power is
restored. Its empty local failure directory and hash-bound failure receipt are
preserved.

This amendment changes no cloud resource or remote workload. It requires a new
exact authorization because the controller and preflight hashes differ from the
previous proposal.

## Exact amended scope proposed

Authorize **one create request and no replacement**, carrying forward the
unconsumed V6 cloud scope:

- the unchanged exact 37-file, 5,504,396-byte V6 manifest;
- the unchanged 63 focused tests, frozen 144-cell P5 run/read-only verify, and
  CaDiCaL/CUDD/d4/Linux-control readiness scout;
- the unchanged 13 hash-locked binary wheels and native dependency lock;
- the unchanged pinned Python image, Secure 2-vCPU `cpu3c` request, at least
  4 GB RAM, 12 GB container storage, integer zero pod volume, no network volume,
  and approved HTTP ports;
- the unchanged 256-KiB resumable chunks, 20-minute lifetime, cleanup due by
  18 minutes, `$0.10` phase cap, and `$0.20` attributable campaign cap;
- no performance ranking, production calibration, publication, or unrelated
  workload;
- ownership-only cleanup and no replacement after any failure.

The V7 controller changes only the local launch contract:

- correct the manifest byte check from `5,500,977` to `5,504,396`;
- use the shorter fresh output identity `native-procfs-v7-001`, preserving the
  empty V6 local directory;
- require the V6 authorization and local-refusal hashes in the amended
  authorization; and
- add a read-only AC-power gate to preflight, in addition to retaining the
  controller's host-awake guard.

The source/test bundle, bootstrap, remote program, dependency locks, resource
request, runtime bounds, validation gates, and cleanup logic are unchanged.

## Verification and current blocker

The V6 local refusal receipt records zero create requests and an unconsumed
cloud authorization. The amended transport/supervisor surface passes 39 tests;
the combined changed surface passes 135. The isolated V6 package still passes
all 63 focused tests.

The authenticated V7 read-only preflight found both Runpod inventories empty,
`cpu3c` at `$0.06/hour`, sufficient account headroom, a conservative prior
bound of `$0.0059547362`, and a projected aggregate bound of `$0.0292880696`.
It correctly returned `ready=false` solely because the controller host remains
off AC power. No launch is allowed until the computer is plugged in and a fresh
preflight reports `host_ac_connected=true`.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| `runpod_native_scout_controller_v7.py` | `3442f8dc313deb97a9382845e2b5cbd8b0ed75673a44e4e6c20c2577087dcd71` |
| `http_native_scout_preflight_v7.py` | `b48ee4aa5a36a1f9af6505c20a785a30ba378b516772a029a5bcbfe16fcbbd84` |
| `http_native_scout_bootstrap_v2.py` | `ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9` |
| `runpod_native_scout_remote_v4.py` | `6d737955b88ede1741db0b6bf7500060b0ca2e3e34c0b49cf3b1c12fb4d029da` |
| `RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V6-20260829.json` | `4883f93e3147bd2aa6c986d99685d20e18974fc6d2da1c3645b269579fe38c2c` |
| 13-wheel lock (`RUNPOD-WHEEL-LOCK.json`) | `8ca822023845a23884555aed6d0f1ce763424fbef9344618ea390157aa1af788` |
| `RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json` | `947696d26d2cfc029d21af2f395faff14b83234d1ddcde3b1b159387f492abb7` |
| V6 authorization | `adac7e3db14a559b51bc4bf1da0b57b8fa6a59f0eeb9c7876eb393b23d364ebe` |
| V6 local failure receipt | `612baf08e19986d4a4ce74e6f3146b1d3599fa27081922c090917b424ab5c100` |
| amendment local verification | `a8f56d42cf5552038f1615ca5c9ffeff3b5e3802d954af58f95a1f9b478e1c93` |
| amendment read-only preflight | `e1696184990377bb8f2736fc533b30bc1ca97519278940104d9a79f47fae576d` |

## Authorization boundary

`HTTP-NATIVE-SCOUT-HOST-PREFLIGHT-AMENDMENT-AUTHORIZED-20260829.json` does not
exist. The V7 controller refuses without a separately hash-bound authorization.
Even after authorization, the preflight and host guard refuse while the
computer is not connected to AC power.

After connecting the computer to AC power, suggested exact authorization:

> I authorize the one-create Runpod native-scout host-preflight amendment
> exactly as specified in
> `RUNPOD-NATIVE-SCOUT-HOST-PREFLIGHT-AMENDMENT-PROPOSAL-20260829.md`, carrying
> forward the unconsumed exact 37-file V6 workload, 256-KiB bounded chunks, one
> zero-volume Secure 2-vCPU pod, 20-minute limit, $0.10 phase and $0.20 campaign
> caps, owned cleanup, and no replacement.
