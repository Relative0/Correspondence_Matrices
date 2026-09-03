# Query-ladder cross-machine/compiler replication preparation

Date: 2026-09-04
Scope: exact, non-neural repeated-restriction portability check
Status: package validated; cloud execution not authorized

## Prepared comparison

The next controlled phase is an exact replication of the verified 27,648-cell Lane-B
query ladder. It preserves all 54 cases, eight arms, q1/q4/q16/q64 cells, 16 balanced
arm-order blocks, source checkpoint `13d9927`, frozen oracles, exact output contract,
isolated-child measurement method, and independent verifier. It changes only the
execution host/compiler boundary needed to test portability.

The prior result used RunPod flavor `cpu3c`, an AMD EPYC 9655 host, and GCC 12. The new
package requests `cpu5c` and Debian Bookworm `clang-14=1:14.0.6-12`. It requires a new
Pod identity and a nonempty RunPod machine-placement identifier. On the worker, a
preflight reads the actual CPU model and aborts before dependency installation or the
workload if it is still `AMD EPYC 9655 96-Core Processor`. The Clang package version,
resolved executable, executable SHA-256, and full version string are recorded and later
cross-checked against the campaign runtime binding.

The run remains one-create/no-replacement and fail-closed. It permits only paired
portability analysis after independent verification. It does not authorize selector or
gate fitting, neural training, production routing, website changes, publication, or a
Git push.

## Local verification

The 70-file, 3,939,509-byte package passed a clean isolated-tree functional replay. The
replay covered all eight arms at q1, q4, q16, and q64 (32 functional cells), used a
synthetic clock, did not inject `PYTHONPATH`, used no network, created no RunPod
resource, and produced no timing, memory, or decision-bearing evidence. Separate tests
verify every manifest source hash, the unchanged schedule, the host/compiler guards,
the exact prior-result bindings, transport-source bindings, and refusal to proceed
without the new authorization record.

## Authorization boundary

The immutable request is
`docs/recognition/architecture_query_ladder_cross_machine_execution_20260904/RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_AUTHORIZATION_REQUEST_20260904.json`
with SHA-256
`b9b9a8aba4eb71c70609eff705a26bbf2de6efe935253dc2404c5e8da83e3bad`.
It permits at most one Secure CPU Pod at no more than $0.10/hour and $0.02 total, with
a $0.04 cumulative hard ceiling including the preceding ladder attempts. The Pod has
2 vCPU, at least 4 GB RAM, 12 GB disposable disk, no persistent or network volume,
ten-minute cleanup, and twelve-minute inventory reconciliation.

No cloud resource has been created. The prior authorization is not reusable. Execution
requires the exact new approval text recorded in the request.
