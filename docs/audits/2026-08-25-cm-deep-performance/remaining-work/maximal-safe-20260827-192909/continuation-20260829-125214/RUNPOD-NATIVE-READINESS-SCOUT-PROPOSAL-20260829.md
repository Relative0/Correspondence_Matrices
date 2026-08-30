# Runpod comparative Linux/native readiness scout proposal

Date: 2026-08-29  
Status: **pending explicit authorization; zero pod creates authorized by this document**

## Purpose

Run one bounded functional scout needed to finish the Linux/native portion of
Phase P4 in `CM-FAST-VARIANTS-COMPARATIVE-BENCHMARK-PLAN-20260829.md`. The
scout checks the comparative contracts and evidence path on Linux and executes
the actual native CaDiCaL, CUDD, and d4 adapters on tiny known-answer inputs.
It is not a benchmark campaign and its recorded durations cannot be used for a
performance ranking.

This proposal does not authorize P6 corpus selection, P7 CM timing ablations,
P8 external timing comparisons, additional allocations, or a replacement pod.

## Exact resource and spend boundary

- One Runpod pod create request, with no automatic or manual replacement.
- Secure Cloud CPU, selected from the frozen eligible flavor list; current
  selection is `cpu3c` at 2 vCPU and 4 GB RAM.
- Image:
  `python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`.
- 12 GB container disk.
- Zero pod volume and no network volume.
- Ports `8080/http` and `8081/http` only for the token-gated bootstrap and
  result transport.
- 20-minute ownership/watchdog horizon; controller cleanup begins by 18
  minutes. The pod is deleted immediately after success or failure.
- Rate cap: `$0.25/hour`.
- Scout phase cap: `$0.10`.
- New comparative-campaign cap: `$0.20`. This campaign starts at `$0.00`; the
  four prior, separately authorized pod IDs remain historical evidence and are
  not silently charged to this new campaign.
- Current quote from the read-only 2026-08-29 09:24 UTC preflight is
  `$0.06/hour`. Including the conservative `$0.01/hour` storage-rate reserve,
  the maximum 20-minute projection is `$0.0233334`.

## Exact upload and dependency scope

Upload only the 30 files in
`RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V2-20260829.json`:

- raw source bytes: `5,461,757`;
- manifest SHA-256:
  `3236c5f7415852df030d128d2e8cb07953f12eac4c9ca755beed55ad6a814364`;
- locally constructed ZIP size at review: `2,105,137` bytes;
- locally constructed HTTP payload size at review: `2,831,254` bytes;
- upload hard cap: 8 MiB.

The earlier manifest without `V2` is retained as a superseded review artifact.
V2 includes the corrected complemented-edge CUDD graph exporter. `.env` files,
credentials, token stores, unrelated dirty files, prior evidence, and benchmark
corpora are excluded.

The base environment installs the existing 13-package hash-locked binary-wheel
set from `runpod-requirements.lock`. The native lock then downloads exactly
eight public PyPI artifacts totaling `11,264,212` bytes, with per-file byte and
SHA-256 validation and redirects disabled:

- binary wheel required: `dd==0.6.0`, including `dd.cudd` and `dd.cudd_zdd`;
- binary wheel required: `python-sat==1.9.dev15`, including CaDiCaL 1.9.5;
- binary wheels: `setuptools==84.0.0`, `wheel==0.48.0`,
  `networkx==3.6.1`, and `six==1.17.0`;
- source builds allowed only for the pure-Python packages `ply==3.10` and
  `astutils==0.0.6`;
- source builds are forbidden for `dd` and `python-sat`;
- all installs use exact local artifacts with `--no-deps`, followed by
  `pip check` and exact installed-version reconciliation.

Dependency lock SHA-256:
`947696d26d2cfc029d21af2f395faff14b83234d1ddcde3b1b159387f492abb7`.
Downloaded archives and built wheels live in a temporary directory and are not
returned in evidence.

## Frozen workload

1. Install and verify the 13-package base wheel lock.
2. Run exactly 60 focused tests from these seven files:
   `test_cm_comparative_foundation.py`,
   `test_cm_comparative_readiness.py`,
   `test_cm_comparative_linux_supervisor.py`,
   `test_cm_comparative_native_scout.py`, `test_cm_no_reinflate.py`,
   `test_program_metrics.py`, and `test_cm_native_contracts.py`.
3. Run the frozen P5 smoke: six CM/CSE/raw arms, two deterministic `k=8`
   cases, 12 counterbalanced blocks, and exactly 144 correctness cells.
4. Run Linux process controls for successful completion, bounded-output stop,
   process-tree timeout/cleanup, and sampled whole-process-group RSS stop.
5. Execute native CaDiCaL through `pysat.solvers.Cadical195` on the bounded
   complete-vector and reused-assumption suite, checking witnesses and cores
   against the independent scalar oracle.
6. Execute native `dd.cudd.BDD` with automatic reordering disabled during
   construction. Check fixed order and explicit group sifting where variables
   exist, complemented-edge graph extraction, independent graph replay,
   root-manager identity, and JSON dump/reload. `dd.autoref` cannot substitute
   for this arm. `dd.cudd_zdd` is identity-checked only because no matched ZDD
   task is declared in this scout.
7. Execute the hash-pinned Linux x86-64 d4 ELF after architecture and `ldd`
   checks on five known-count CNFs: true and false zero-variable cases, all
   assignments, an unused declared-variable case, and a contradiction.
8. Probe `perf stat` only for availability/refusal. A refusal or absence is a
   valid result and does not fail the scout.
9. Rehash every uploaded source before and after execution and return bounded,
   checksummed evidence.

No corpus timing, comparative speed ratio, statistical claim, implementation
selection, or publication is permitted from this run.

## Safety and evidence behavior

- The controller requires a separate authorization JSON bound to the proposal
  and V2 manifest hashes before its single POST is reachable.
- A separate Windows watchdog must acknowledge the exact atomic state and
  remain alive before the create request.
- The create response is re-read and must match the pod name/ID, image, Secure
  placement, CPU flavor, 2-vCPU/at-least-4-GB resources, price, ports, 12-GB
  container disk, and exact zero-volume configuration before upload.
- Only the pod ID returned by this create and matching its unique name is
  eligible for deletion. Both v1 and v2 inventories are reconciled afterward.
- Bootstrap authentication is a fresh random token. The provider API key and
  bootstrap token are not passed to the worker or recorded.
- The 2.1-MB source ZIP is passed to the worker by bounded temporary files,
  avoiding Linux `execve` environment-size limits.
- Worker streams, deadlines, process counts, sampled RSS stops, and returned
  evidence are bounded. The sampled RSS stop is explicitly not represented as
  kernel memory-quota enforcement.
- Returned evidence is capped at 16 MiB compressed and 16 MiB summed
  uncompressed files. Missing, malformed, mismatched, or incomplete evidence
  is failure, never success.
- On every outcome the controller requests owned cleanup. No replacement is
  attempted.

## Reviewed identities and current readiness

- controller SHA-256:
  `78e910f99738b27c23ab9553d308e8ddc435372a753cff1a07ffa3732f3320cf`
- read-only preflight SHA-256:
  `4714b2d698b417245f817dab125999ef9df173eb8f3ee07d1d6a9636f27eb3af`
- token-gated bootstrap SHA-256:
  `7b997d3b36307f501875290369f50fb661f60fa516b56c214f67986df16d0646`
- remote program SHA-256:
  `1f1d22093a5bf9a37c60b1fa35e280088a3e3b683b859ccdd9915033c559aaa7`
- read-only preflight receipt SHA-256:
  `6a89f63bcca942819bf0e2f26d0bc1a456cc8db5ccf10a03a919c6acdfb4046e`

The preflight recorded zero resource writes, empty v1/v2 pod inventories,
four reconciled historical pod IDs, sufficient credit/spend limit, three
eligible Secure CPU flavors, and `cpu3c` at HIGH availability. Availability
and account/budget gates are checked again immediately before any authorized
create.

## Exact authorization text

If approved, the authorization is:

> I authorize one Runpod comparative Linux/native readiness scout exactly as
> specified in `RUNPOD-NATIVE-READINESS-SCOUT-PROPOSAL-20260829.md`: upload the
> exact 30-file V2 manifest, install the existing 13 locked binary wheels and
> the exact eight-artifact native lock (allowing source builds only for
> `ply==3.10` and `astutils==0.0.6`), run the 60 focused tests, 144-cell P5
> smoke, Linux controls, and tiny native CaDiCaL/CUDD/d4 checks, using one
> Secure 2-vCPU CPU pod with 12 GB container storage and zero pod/network
> volume, a 20-minute lifetime, `$0.10` scout and `$0.20` new comparative
> campaign caps, owned cleanup, no performance ranking, and no replacement.

