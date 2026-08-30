# Runpod native-scout host-preflight amendment result audit

Date: 2026-08-29  
Final status: **attempt safely reconciled; workload did not run**

## Authorized scope and preflight

Brian authorized one create and no replacement under the exact V7
host-preflight amendment. The authorization is bound to the unchanged 37-file,
5,504,396-byte V6 manifest, 256-KiB chunk protocol, Secure 2-vCPU `cpu3c`,
12-GB container disk, integer zero pod volume, no network volume, 20-minute
lifetime, `$0.10` phase cap, and `$0.20` attributable-campaign cap.

The fresh read-only preflight at 15:35 UTC reported:

- Windows host AC power connected;
- empty v1 and v2 pod inventories;
- `cpu3c` available at `$0.06/hour` with 2 vCPU and 4 GB RAM;
- a `$0.005954736242691676` prior campaign bound; and
- a `$0.029288069576025005` projected 20-minute aggregate bound.

All 39 transport/supervisor safety tests passed before launch. The fresh output
identity `native-procfs-v7-001` was absent before the controller started.

## Attempt result

The controller issued exactly one POST. Runpod returned HTTP 201 and pod
`3o7r0za7cm72yn`. The returned and read-back resource identity matched the
approved contract: Secure cloud, `cpu3c`, 2 vCPU, 4 GB RAM, `$0.06/hour`, pinned
Python image, 12-GB container disk, integer zero pod volume, no network volume,
and HTTP ports 8080 and 8081.

Both generic `/health` probes subsequently returned the expected bootstrap
identity. The next proxied request returned HTTP 404. The controller therefore
stopped before the first upload-status acknowledgment, recorded zero uploaded
source files, never started the worker, and retrieved no workload evidence.
None of the 63 focused tests, 144 P5 cells, or native CaDiCaL/CUDD/d4/Linux
readiness work ran in this attempt.

Control flow localizes the failure to the first call in `upload_payload`, which
is a GET of the authenticated port-8080 upload-status route. That localization
is an inference from the saved `bootstrap_ready_utc`, zero-upload fields, error,
and frozen controller sequence; the error record did not capture the request
route or response body. Because `/health` is identical on both servers, it does
not prove that each public proxy hostname reached its role-specific internal
port. Saved evidence cannot distinguish transient Runpod proxy routing from a
port-role mismatch after the pod was deleted. Earlier attempts using the same
V2 bootstrap successfully completed chunked uploads, so the 404 is not a
deterministic failure of the frozen upload implementation.

## Cleanup and accounting

The controller deleted only its owned pod; DELETE returned HTTP 204. Its cleanup
snapshot had empty v1/v2 inventories. The independent postflight then checked
all ten known pod IDs: every detail request returned HTTP 404 through both APIs,
and both inventories remained empty. The watchdog reported
`controller_cleanup_verified` with no errors. Both Windows host-awake guards
released and their worker processes exited.

Provider billing had not yet posted a row for the new pod. Using the approved
storage-rate reserve and the recorded 31.711-second lifetime gives a
`$0.0006166058043638865` attempt bound and a
`$0.0065713420470555626` attributable-campaign bound, below both caps.

The postflight verified the authorization hash, frozen controller/preflight/
bootstrap/remote/manifest/lock hashes, and every source identity. It reports
`attempt_safely_reconciled=true`, `workload_completed=false`, and
`authorization_consumed=true`. No replacement or further create is authorized.

## Evidence hashes

| Artifact | SHA-256 |
|---|---|
| Authorization | `3f9759ea846f6e4022b7efc20b85bd472909777e7288c9d896c3bb0a00db9d23` |
| Fresh read-only preflight | `4edab471ecad5070e6b86aabaf20d0c601fc4247d1a626fc12b772e338306b4a` |
| `native-procfs-v7-001/RUN.json` | `12caa31bf76872c52ba609cfdd722f4c6cdde22fd6a12a2a0d2c295e5598cd69` |
| Pod resource check | `824d396b9d73fc59009b68e75c8b7ac958283ba2bd580810f0254c6e34d53383` |
| Watchdog result | `03791c37f3ef486067451f8808bc1358ef23b7f84a602ba5a720abdb4a1de064` |
| Final verification | `16499ec7f9f471c6726e0165d3027d4f34241f626a16bcc0613d34bec5f551ab` |
| Read-only verifier | `c212dc156a33ed9ebec5cb9604a48f07ada2fbf4bc6d1c3197e120c5356459a1` |

