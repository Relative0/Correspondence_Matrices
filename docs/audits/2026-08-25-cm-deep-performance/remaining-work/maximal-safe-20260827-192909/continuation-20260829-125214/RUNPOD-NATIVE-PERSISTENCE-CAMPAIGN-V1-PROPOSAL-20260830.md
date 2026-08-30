# RunPod native persistence campaign V1 proposal

## Purpose

Close two remaining native structural-reuse gaps with a bounded functional experiment: serialize native CUDD ZDD and d4-produced d-DNNF structures, reload each artifact in a distinct fresh process, and independently replay the serialized structure without invoking its producer. This run is an exactness and provenance gate, not performance evidence.

## Frozen workload

- Two admitted cached-real `k=8` feature-model scenarios from the existing version-history cohort.
- Two execution arms only: `cudd_zdd` and `d4_ddnnf`.
- Four blocks, which is one complete two-arm counterbalance cycle.
- Sixteen cells total, with one build process and a distinct reload process per cell.
- Thirty-two exact relation rows (two versions per cell) must agree with the independent scalar CNF oracle.
- Serialized artifacts must be deterministic across blocks for each case and arm.
- Native CUDD ZDD must be an identified compiled `dd.cudd_zdd` extension; no `autoref` substitution is permitted.
- d4 is built ephemerally from the exact minimal source closure at commit `333370cc1e843dd0749c1efe88516e72b5239174`. The resulting ELF SHA-256 is recorded and hash-bound into every worker.
- The d4 compiler must emit its legacy arc-literal d-DNNF format. Reload and independent replay must not invoke d4.
- All worker subprocesses use the fail-closed Linux process-group/RSS supervisor.
- Focused tests must report exactly 24 test cases with no failure, error, or skip before the workload begins.
- Source identity before and after execution must match.
- No performance ranking, crossover claim, production-estimator acceptance, or full-model claim is permitted from this run.

## Ephemeral build dependencies

The pod may run Debian `apt-get update` and install only `build-essential`, `libgmp-dev`, and `zlib1g-dev`. Package versions and build output are retained. The build command is exactly `/usr/bin/make -j2 s` in `external/d4`. No generated binary is returned as a reusable project dependency; only its identity and the functional evidence are retained.

## Resource and cost bounds

- One secure CPU pod, 2 vCPU, at least 4 GB RAM.
- Pinned Python 3.13.15 amd64 image digest.
- 12 GB ephemeral container disk, zero pod volume, no network volume.
- Maximum lifetime 1,200 seconds, cleanup begins by 1,080 seconds.
- Per-phase projected RunPod cap: $0.10 including the existing storage-rate reserve.
- Aggregate authorized campaign cap: $10.00, including reconciled prior attempts and posted/lagging billing reserve.
- Automatic retry is allowed only under the user's aggregate $10 authorization and only after the prior attempt is conclusively reconciled and both pod inventories are empty.

## Safety and acceptance

The V20 readiness pod `rg3zlg5gbdbp5p` must be verified complete and absent through both APIs before creation. The controller may issue exactly one create. A separately bound watchdog owns deadline cleanup. Regardless of workload outcome, deletion and empty v1/v2 inventories are mandatory. Unknown charges, ambiguous ownership, changed source hashes, changed resource identity, unavailable native dependencies, exactness disagreement, malformed artifacts, incomplete process-tree measurements, or missing evidence cause refusal or failure rather than substitution.

