# Runpod gate for the bounded verification pilot

Status: **prepared locally; not uploaded or run on Runpod**. This is a new
verification bundle, not the other task's 65-file memory-smoke bundle. Its
older authorizations and consumed run names must not be reused for this job.

The other task's separately approved zero-volume memory smoke has now
completed successfully (70 focused tests, 312 rows and verified deletion).
That result does **not** authorize or execute this 12-file pilot. See
[the memory-smoke audit](RUNPOD-ZERO-VOLUME-RESULT-AUDIT-2026-08-28.md).

## Ready-to-review bundle

- File: `C:\Users\brian\Documents\CM_Computation\docs\runpod\cm-verification-bundle-2026-08-28.zip`
- Archive bytes: 55,948.
- Archive SHA-256: `a87bf19f93c9117ecb9547d2de76e2fe461d4850d6de3128255345c67db700f8`.
- Source-manifest SHA-256: `a3eda0c9d7a67719b058ad7cc8af081e0a7a267c7e306b112a37adb08c52b48d`.
- Exactly 12 allowlisted Python files plus their source manifest. No dotenv
  files, credentials, git history, corpus, website, local databases, or prior
  run outputs. The source includes the observed dirty implementation, pinned
  by exact bytes rather than HEAD alone.
- The archive's entries were checked against the source manifest before
  packaging. The local frozen-source regression and pilot both passed.

The archive root contains `scripts/`, `tests/`, `cmbench/`, the three root
implementation files, the independent auditor under `deliverables_n22_24/`,
and `source_manifest.json`. No source dependency installer is included.

## First gate: read-only account visibility

Brian authorized private use of the memory-smoke campaign credential. The
read-only check completed at 08:09 UTC on 2026-08-28: both APIs accepted
inventory requests (HTTP 200), both returned zero pods, and the supplied pod
ID returned HTTP 404 on both. No existing pod is visible for this workload.
This establishes inventory access, not permission or success for creation.
See [the authenticated access record](RUNPOD-READONLY-ACCESS-2026-08-28.md).

Reconciled at 08:18 UTC: the other task's authorized 08:08 UTC root-loader
check returned the same 200/empty inventories and 404 supplied-ID results.
Its saved evidence was verified here without repeating authentication.
Both loader checks are complete; changing the loader has not resolved the
issue, and no key equality/account identity inference follows.

Credential location (location only; never print its contents):

```text
C:\Users\brian\Documents\CM_Computation\docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\.env.runpod.local
```

The helper and its imported controller were reviewed before execution.
The operation used list/detail GET requests with redirects disabled,
selected non-secret fields, bounded timeouts and a new local evidence
filename. Unrelated credential/proxy discovery was disabled in the session.
Never print full API pod objects: the API schema contains environment
variables and other sensitive fields.
[Official list-pods reference](https://docs.runpod.io/api-reference/pods/GET/pods).

The earlier creation HTTP 500 responses remain historical observations;
no creation was retried. Pod non-visibility was freshly corroborated by the
read-only check. Read newer updates before choosing any action. Root-loader
credential use was not included in the 08:09 campaign-key check; it was
separately authorized and completed in the reconciled root-loader record.

## Second gate: exact upload, target and spending approval

Only after a usable account/route is established, confirm the actual target
and the effect before uploading this bundle or allocating a resource. A
possible bounded proposal is one disposable Secure CPU pod, two vCPU, at
least 4 GB RAM, 10 GB ephemeral disk, no network volume or public service
ports, at most USD 0.25/hour and USD 0.10 total, and at most 15 minutes.
These are **proposed ceilings, not a live quote or authorization**. No GPU
is required by these tests. Do not attach to or modify an unrelated pod.

The other task's new HTTP transport amendment concerns its **65-file memory
smoke**, not this archive. It proposes different ports, storage and lifetime.
Do not merge the two proposals, run two competing retries, or treat approval
of either bundle as approval of the other. Prefer settling that single
transport diagnostic before proposing another resource allocation here.
See [the reviewed distinction](RUNPOD-TRANSPORT-REVIEW-2026-08-28.md).

The 65-file retry was separately authorized and executed by `Run CM safe
work campaign`; this 12-file bundle is still not authorized for upload.
The corrected memory-smoke controller received HTTP 201 but refused the
reported zero-GB pod volume versus the approved ten GB before source upload.
The pod was deleted and final 08:41 UTC checks were clear. Its single actual
create is consumed; no duplicate or replacement is queued. See
[current execution/audit status](RUNPOD-HTTP-RETRY-INDEPENDENT-AUDIT-2026-08-28.md).
Successful allocation is not a successful upload or cloud benchmark.

The existing digest-pinned Python image and a matching binary-only NumPy
2.3.2 wheel can be considered, but their availability, hashes and dependency
installation must be validated before a launch proposal is called runnable.
Do not silently install latest packages or import the old campaign's source
build exceptions. This verification needs standard-library unittest and
NumPy; it does not need pytest, CUDD, d4, or a GPU runtime.

Require an independent deadline/cleanup mechanism before resource creation,
new ownership evidence, no automatic replacement, bounded logs, and evidence
retrieval before termination of only the owned pod. Check postflight inventory
and billing separately; controller estimates are not a finalized invoice.
Unresolved provider HTTP 500 failures are not a reason to launch repeatedly.

## Workload after the gates pass

From the extracted bundle's root, under the pinned remote Python:

```text
python -B -m unittest discover -s tests -p test_cm_measurement_verify.py -v
python -B scripts/cm_measurement_verify.py --pilot-output runs/remote-functional-pilot-UNIQUE-RUN-ID
```

Replace the output name with a new, approved run identity. Keep the source
manifest unchanged, verify the archive and each source hash before execution,
and collect the full new run directory and bounded unittest output. Verify
the returned checksums and replay outputs locally before reporting success.

Important current runner limitation: its pilot metadata labels execution as
local and `cloud_run: false`. Those fields deliberately describe its current
local entry point. **Do not run the above on Runpod and then silently rewrite
those fields as remote evidence.** A reviewed remote-provenance extension
must first record provider/pod/run identity supplied by the trusted controller,
runtime/dependency versions, launch/collection times and artifact hashes. Pin
that amended source under a new manifest/bundle identity and obtain approval
for the exact revised upload. This archive is a reviewable starting point,
not a fully certified cloud controller package.

The maximum width is eight live variables and the real pilot contains four
synthetic fixtures, three representations, eight independent structural
replays and eight fresh-process reloads: 28 scheduled cells total. Timings
remain plumbing diagnostics. A remote pass is compatibility/reproducibility
evidence, not a CM speedup result or closure of all measurement gaps.

## Unchanged boundaries

Initial packaging performed no credential use or authenticated request.
The subsequently authorized read-only check is recorded above. No source
upload, resource launch, support message, commit or push occurred. No browser
URL-policy workaround was used. The other task's core changes, Runpod
controllers, consumed requests and historical artifacts remain intact.
