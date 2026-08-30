# Runpod external native-gap V20 result audit

Date: 2026-08-30  
Run directory: `native-gap-v20-001`  
Pod: `rg3zlg5gbdbp5p`

## Result

V20 completed the native-readiness workload. It is readiness evidence only;
no comparative performance measurement or ranking ran.

- 68 JUnit testcase elements passed. The aggregate XML metadata reported 192
  tests and zero failures, errors, or skips.
- All 144 frozen P5 correctness cells passed and the P5 verifier passed.
- Dependency closure, pinned dependency versions, source-before/source-after
  identity, and all four Linux controls passed.
- CaDiCaL passed seven functional cases with whole-process-tree RSS and owned
  process cleanup.
- CUDD passed four functional cases, including exact dump/reload, with
  whole-process-tree RSS and cleanup.
- The static d4 executable had SHA-256
  `29cb30f351ed92b02343e5e7a98b082e949d9838245f37c0bcdecf68a57ffd39`
  and size 5,054,920 bytes. It returned the exact expected counts:
  `true-k1=2`, `false-k1=0`, `all-k3=8`, `unused-k3=4`, and
  `conflict-k2=0`.
- `perf` was unavailable because it was not installed. No `perf` substitute was
  accepted.

The evidence ZIP is 143,415 bytes, contains 71 members, and has SHA-256
`3f508be7c11bad4242dfcd64c439dcc4e4b3a8fda455d725a384ff857346b6d2`.
The frozen source remained unchanged.

## Resource and cleanup reconciliation

The created resource matched the recorded Secure 2-vCPU/4-GB contract, pinned
Python image, 12-GB container disk, zero pod volume, and zero network volume.
The runtime affinity was `[29, 157]`; those are the two allowed logical CPUs,
not a host-size claim.

The controller deleted the owned pod with HTTP 204. Independent read-only
verification found both v1 and v2 inventories empty, all 19 known pod IDs 404,
all V15/V16/V17/V19/V20 guards released, and watchdog cleanup verified. V14
and V18 made no create. Current provider billing was `$0.016106911170936655`
and may lag. The conservative attributable campaign bound through V20 is
`$0.024656037269035973`, below the historical `$0.10` phase and `$0.20`
campaign caps.

Receipt:
`EXTERNAL-NATIVE-GAP-V20-FINAL-VERIFICATION-20260829-170627-870230.json`
(SHA-256
`12c191ebb00b3694a41d9280da4bfb5d0815c7a45b853a9e343c87e6087b113b`).

## Scope caveat

V14 through V20 were launched by a separately owned task under a record that
cites a newer cross-task `$10` instruction. That source conversation is not
visible here, so authorization compliance remains `null`. The technical result
and cleanup are verified; this audit does not adopt that authority claim and
does not authorize another create.

