# Runpod P7 W4 timing/RSS scout proposal

Date: 2026-08-31  
Status: exact payload and controller frozen; separate upload/execute authorization required

## Purpose

Run the small W4 development timing/RSS scout from the comprehensive comparative
program. This is the first comparative timing stage, but it is only a resource,
noise, and shard-sizing scout. It is not the principal P7 result and cannot by
itself support a production or headline speed claim.

The W8 LogikBench cohort frozen at logical SHA-256
`427522568449d4d385ce642769b87b0703216535edb131653a0a75b2a8e39dcc`
remains untouched confirmation and is not executed here.

## Frozen selection and ledger

- Parent P6 V4 logical freeze:
  `54ea61a38135426975a0d1fead9b24c020dc565eb3d952356640fa38062598dd`.
- W4 derived logical freeze:
  `d81ab57d4fbfe8a49a28314cc645d9ddf24e7d7182abfe1d2f36c016430c7b31`.
- Twelve independent development clusters, selected without comparative timing.
- Six synthetic cases: `k=8,12,16`, shared and tree at every `k`, covering all
  four frozen generator families.
- Six natural EPFL cones: one hash-selected case from each occupied frozen
  support-bin/source-node-bin stratum after the already retained, policy-independent
  W3 `sqrt` oracle-feasibility exclusion.
- P7 IR: 12 cases x 8 blocks x 4 arms = 384 primary cells.
- P7 relation: 12 cases x 10 blocks x 5 arms = 600 primary cells.
- Total: 984 fresh-process primary cells, each with a source-bound oracle,
  one admitted CPU, a 30-second per-cell deadline, a 1-GiB sampled RSS stop,
  bounded streams, owned process-group cleanup, and outside-span exact validation.
- Each policy is exactly one complete frozen counterbalance cycle. A cycle is
  never shortened after timing begins.

The authoritative selection package is
`docs/research/verification/comparative-p7-w4-timing-scout-v1-2026-08-31`.

## Exact source payload

Reuse the previously disclosed and authorized 96-file P7 V2 private source/test
bundle without modifying any member:

- manifest: `RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json`;
- manifest SHA-256:
  `9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`;
- source files: 96;
- uncompressed source bytes: 19,484,163;
- bundle: `RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V2-20260830.zip`;
- bundle bytes: 3,197,013;
- bundle SHA-256:
  `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`;
- secrets/environment/Git credential material: none.

The bundle's historical manifest says `performance_measurement=false` because it
was frozen for the earlier functional scout. No source member changes here. The
new exact remote wrapper is the separately frozen instruction that selects the
W4 derived freeze and invokes the already tested runner with
`profile=performance`.

## Exact executable identities

- remote wrapper `runpod_p7_w4_timing_remote_v1.py`:
  `dfb40c8b82c788c55b9662b250ceaa000787697825bc845443ffeadd1dd4c913`;
- controller `runpod_p7_w4_timing_controller_v1.py`:
  `51ca1743ae15dc503407df63fc27852290096171008e68346b2834ada7dd67d2`;
- read-only preflight `http_p7_w4_timing_preflight_v1.py`:
  `811a1caae1a752c8705c4a2c7f72f0efaa513594a78079f1e8221d1c45b7cae7`;
- HTTP bootstrap `http_native_scout_bootstrap_v2.py`:
  `ca235af411cce9db778fb453b305e9a2c4cae1262d03d5dd363d5214c8550ac9`;
- exact-bundle/derived-freeze validation
  `P7-W4-TIMING-PACKAGE-V2-LOCAL-VALIDATION.json`:
  `12a447904d84d34ce2ba871fd287a68ad59a94b2931517b357527266e030a675`.

The isolated exact 96-file bundle passed 39 focused tests plus 22 subtests. The
local W4/core selection, runner, and supervisor suite also passed 39 tests plus
22 subtests. The exact bundle independently reproduces the W4 logical freeze
and produces plans of exactly 384 and 600 cells.

## Remote environment and bounds

- one Runpod Secure CPU pod;
- exactly 2 vCPUs and at least 4 GB RAM;
- pinned image
  `python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`;
- 12 GB container storage;
- zero pod volume and zero network volume;
- ports `8080/http` and `8081/http` only for the token-gated bounded transport;
- 13 locked binary Python packages, `--require-hashes --only-binary=:all:`;
- no source builds and no system-package installation;
- 256-KiB bounded resumable upload chunks;
- one create and no replacement within this controller;
- 20-minute hard lifetime, controller cleanup at 18 minutes, independent
  watchdog and ownership-only deletion;
- $0.10 phase cap and $5.00 attributable-campaign cap, with current billing,
  missing-attribution, storage, and lag reserves checked before creation.

The controller refuses creation unless both Runpod inventories are empty, a
compatible offer is currently available, the host is on AC power, account and
spend-limit gates pass, every payload/controller hash matches, and the watchdog
acknowledges the exact state while still live. It validates actual image,
Secure placement, CPU flavor, vCPU/RAM, price, storage, ports, and absence of GPU
or network volume before any upload.

## Evidence and stop rules

The run must retrieve and validate:

- all 984 planned cells exactly once with status `ok`;
- exact source-bound semantic agreement for every cell;
- task-total wall time and sampled owned-process-group peak RSS for each cell;
- fresh worker identity, one-CPU worker affinity, stream closure, and process
  cleanup for every cell;
- complete source-before/source-after identity;
- 13 locked dependency versions and passing focused tests;
- complete counterbalance plans, ledgers, summaries, checksums, runtime identity,
  and derived-freeze identity.

Stop and retain evidence on any semantic mismatch, source/configuration/oracle
identity change, timeout, memory/output stop, partial counterbalance cycle,
unverified cleanup, lost ownership, evidence overflow, or cap violation. Do not
fill missing cells in this controller, allocate a replacement, or touch the W8
confirmation cohort.

## Current operational note

The latest read-only preflight correctly refused readiness because another
unrelated owned-account pod was running and all six compatible Secure CPU
flavors reported `NONE`. This proposal does not authorize interference with
that pod. After exact authorization, the W4 controller may launch only when a
fresh preflight independently reaches the zero-inventory and availability gates.
