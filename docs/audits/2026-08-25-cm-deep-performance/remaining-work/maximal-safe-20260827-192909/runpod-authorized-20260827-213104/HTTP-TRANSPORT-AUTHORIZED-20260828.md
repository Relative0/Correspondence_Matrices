# Single HTTP transport smoke retry authorized

Brian replied **"Yes, please run it"** to the exact one-CPU HTTP retry question
and `HTTP-TRANSPORT-RETRY-PROPOSAL-20260828.md`. This authorizes one shared
attempt, not one per task. This task owns the launch; the website task has
explicitly confirmed it will not start a duplicate.

The approved effect is one Secure CPU pod, two vCPUs / at least 4 GB RAM,
at most $0.25/hour compute, $0.10 additional and $0.20 total smoke campaign
spending including storage, and a 20-minute lifetime. The 12-GB container
disk, 10-GB pod volume, and temporary token-protected HTTP ports 8080/8081
are specifically approved. Delete the owned pod and its pod volume afterward.
No network volume, SSH, Jupyter, alternate GPU or replacement create request.

The pinned Python 3.13.15 image, 65-file manifest, 13-wheel hash lock,
focused output-budget tests and k=6,8 smoke remain unchanged. The existing
project-root loader may privately authenticate the lifecycle and its read-only
checks. No account key is uploaded to the worker or proxy. The source is
uploaded after creation; a fresh per-pod token gates the transport.

Implementation: `runpod_http_smoke_controller.py`, `http_transport_bootstrap.py`,
and `http_transport_preflight.py`; output directory `http-execute-001`.
The new adapter reuses the preserved remote smoke code byte-for-byte.
The latest 25 offline fake-client checks pass, including corrupted uploads,
endpoint authentication, idempotent execution, credential exclusion, timeout,
resource mismatches, cleanup failure, and ambiguous ownership. These tests
are not cloud workload evidence.

Independent review raised two prelaunch issues, both corrected before any
create request: v1 response-field mapping and partial watchdog state reads.
The response validator accepts documented `image` and `machine.secureCloud`
evidence, rejects contradictory aliases or GPU assignment, and uses a v2
detail lookup only when cloud-placement evidence is absent. State/ready/ack
publication is atomic and refuses overwrite; creation requires an exact
state acknowledgment and a live watchdog process.

Primary sources reviewed August 28:

- [Create Pod request and response](https://docs.runpod.io/api-reference/pods/POST/pods)
- [Get Pod response](https://docs.runpod.io/api-reference/pods/GET/pods/podId)
- [Storage pricing](https://docs.runpod.io/pods/pricing): the $0.01/hour storage
  reserve exceeds the documented rate for this 22-GB configuration.

The independent watchdog starts before creation, checks both inventories,
deletes only the owned pod when aborted or at 18 minutes, and reconciles an
ambiguous create response through the full 20-minute horizon. The host must
remain on AC, awake, open and online. No final result is asserted here.
