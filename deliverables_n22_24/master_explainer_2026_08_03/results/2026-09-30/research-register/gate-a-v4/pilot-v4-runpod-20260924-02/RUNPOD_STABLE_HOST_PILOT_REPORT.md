# Runpod stable-host pilot report — `pilot-v4-runpod-20260924-02`

## Decision

No exploratory pilot was completed. Gate A remains **NO-GO**: the unchanged v4
environment-qualification gate was not evaluated, and no performance or
confirmatory result was run or inspected.

## Experiment boundaries preserved

- No frozen v4 file, corpus, runner, harness, schedule, analyzer, protocol, or
  user checkout was changed.
- No package transfer reached successful staging; consequently no smoke check,
  11-repetition exploratory pilot, or confirmatory schedule ran.
- No performance result file was opened or inspected.
- Every started pod was terminated. The final pod lookup returned `not_found`.

## Retained setup failures

1. The least-cost Secure Cloud RTX 4000 Ada request was rejected before a pod
   ID was issued.
2. Several Secure Cloud L4 containers exposed configuration failures before
   staging: an omitted shell wrapper; a bare Ubuntu image without `/workspace`
   or `python3`; and a compatible image without a bundled `runpodctl` binary.
3. The official `runpodctl` v2.8.0 bootstrap passed its pinned binary hash but
   rejected the local sender's UUID code format. The matching v2.14.0 bootstrap
   established the relay connection but rejected UUID codes as malformed.
4. The v2.14 sender's generated relay-indexed word code was then used under
   the explicit public-relay authorization. Its receiver returned `room not
   ready` on the initial attempt and one container restart. Neither attempt
   staged the package.

The setup controller records, redacted system/container logs, provisioning and
termination responses, and hashes are retained alongside this report. One-time
transfer codes, API credentials, and sender output were removed rather than
placed in the evidence directory.

## Environment / cost state

The compatible candidate used Secure Cloud L4, 6 vCPUs, 62 GB RAM, a 20 GB
ephemeral container disk, zero persistent volume, and
`runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2404`. Its published Ubuntu image
digest is recorded in the sanitized system setup logs. All retrieved current
Runpod billing queries returned an empty array, so actual cost is not yet
reported and is deliberately not inferred from hourly price.

## Smallest valid next step

Use a prospectively authorized transfer route that does not depend on the
public relay (for example, a user-approved private object store or a scoped
SSH/key-based transfer), then launch one new `pilot-*` identity. Do not reuse
this failed environment attempt or run a confirmatory schedule.
