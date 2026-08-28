# One additional CPU create authorized — container storage only

Brian replied **"I approve"** to the final question linking
`HTTP-EPHEMERAL-RETRY-AMENDMENT-20260828.md`. Its exact target, effect and
limits are approved. This records one additional create request, shared
across the coordinating CM tasks and owned by this task. The earlier
`http-execute-001b` create is consumed; it is not repeated.

Use one Secure CPU pod with 2 vCPU / at least 4 GB RAM, maximum $0.25/hour,
12-GB container disk, zero pod volume and no network volume. The same pinned
image, approved 65 files, 13 locked wheels, focused tests, k=6,8 smoke,
token-gated HTTP ports 8080/8081, 16-MiB evidence bound and private root-loader
authentication remain in effect. No account key goes to the worker or proxy.

Both HTTP attempts together remain capped at $0.10 and the smoke campaign
at $0.20 including prior costs and storage. Reserve at least $0.01 for the
completed allocation pending billing, or its higher attributable charge.
Keep the 20-minute lifetime, independent watchdog cleanup at 18 minutes,
owned-pod deletion and independent inventory/billing/guard postflight.
No automatic replacement, duplicate launch, GPU fallback or wider workload.

New controller: `runpod_http_smoke_controller_v3.py`.
New accounting preflight: `http_transport_preflight_v2.py`.
Exclusive new output: `http-ephemeral-execute-001`.
The original v1/v2 controllers, bootstrap and earlier outputs are preserved.
The source bundle and remote workload code are unchanged.

The billing preflight attributes any nonzero records to the known prior
HTTP pod and reconciles detail against aggregate amounts. Unknown or
unreconciled costs refuse creation. The v1 grouped billing record fields
were checked against the official [Pod billing history reference](https://docs.runpod.io/api-reference/billing/GET/billing/pods)
on August 28, 2026. Delayed billing is still covered by a reserve.

Authorization is not evidence of execution. Read the new run directory's
`RUN.json`, freeze, progress, results and cleanup records for the outcome.
