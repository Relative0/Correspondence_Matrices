# Runpod v4 exploratory pilot report

Run ID: `pilot-v4-runpod-20260923-01`  
Status: **NO-GO — setup failure before provisioning; no measurement started**  
UTC failure record: 2026-09-23T10:11:27.9006380Z

## Result

The v4 qualification package passed local integrity checks before any Runpod action. The package SHA-256 matched the controlling handoff, and all 68 entries in its extracted deliverable manifest matched their recorded hashes.

Runpod access then failed at read-only inventory/health preflight. The supplied API key was rejected by both documented GraphQL authentication forms. The configured pod proxy returned HTTP 403 to its unauthenticated health endpoint and to a bearer-bootstrap-token health request. Secret values were never printed, copied, or saved in this directory.

Consequently, no pod was created, resumed, changed, or charged; no remote source staging, clean environment setup, smoke check, pilot run, or confirmatory activity occurred. There is no Runpod pilot JSON, no remote environment record, and no remote hash inventory to retrieve. The pod termination requirement is not applicable because this task did not start a pod.

## Retained evidence

- `PRE_FLIGHT_HASH_VERIFICATION.json` records the successful package and frozen-artifact verification.
- `RUNPOD_SETUP_FAILURE.json` records each non-mutating failed access attempt without credential material.

## Gate decision

Gate A remains **NO-GO**. This is not a failure of a stability control and cannot be interpreted as a stability pass or fail: no exploratory observations were collected. The existing v4 NO-GO boundary remains in force, and no confirmatory artifact was inspected.

## Smallest valid next step

Refresh or authorize a Runpod API key with pod-inventory and on-demand-pod permissions, or provide the expected authentication method for the configured proxy. Then rerun this same task from the verified package, selecting one stable on-demand host prospectively and running exactly one full unchanged `pilot-*` attempt.
