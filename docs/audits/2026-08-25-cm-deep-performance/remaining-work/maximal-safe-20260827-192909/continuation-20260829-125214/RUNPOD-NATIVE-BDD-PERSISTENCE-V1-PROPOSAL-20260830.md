# RunPod native CUDD BDD persistence V1 proposal

## Purpose

Close the remaining native structural-reuse gap by building, serializing, reloading, querying, and independently replaying native CUDD BDD artifacts in distinct fresh processes. This is a bounded functional exactness experiment, not performance evidence.

## Frozen workload

- The unchanged, explicitly approved 136-file/5,494,221-byte source/data package.
- Two admitted cached-real `k=8` feature-model scenarios.
- Native `cudd_bdd` only, with two blocks (one complete single-arm counterbalance cycle).
- Four cells, four build processes, four distinct reload processes, and eight exact relation rows.
- The `dd.cudd` compiled extension must be identified; `dd.autoref` substitution is forbidden.
- Serialized artifacts must independently replay to the scalar CNF oracle without invoking CUDD and must be deterministic across blocks.
- Twenty-two applicable focused tests must pass without failure, error, or skip.
- Source identity must remain unchanged. Timing and memory fields are diagnostics only; performance ranking is forbidden.

## Resources, budget, and cleanup

Use one secure 2-vCPU/4-GB CPU pod, pinned Python 3.13.15 amd64 image, 12 GB ephemeral container disk, zero pod volume, no network volume, and the existing 1,200-second lifetime/1,080-second cleanup bounds. Projected phase cost must remain below $0.10 and aggregate campaign cost below the user's $10 cap. The successful native ZDD/d-DNNF pod `dgfqzk61vl7cbe` must be verified absent first. One create is permitted; deletion and empty inventories are mandatory on every outcome.

