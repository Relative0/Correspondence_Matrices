# RunPod canonical native CUDD BDD persistence V2 retry proposal

## Why this retry is warranted

The V1 workload completed all four native CUDD BDD build/reload cells and all eight
relations were exact, but the controller correctly rejected the result because the
producer's raw JSON dump was not byte-deterministic across equivalent fresh builds.
Pod `8fh5st71uqe2pe` is deleted and both RunPod inventories are empty. Its estimated
compute cost was $0.0008549349188804626.

V2 replaces that raw dump with a canonical, bounded, reachable BDD graph. A strict
producer-independent validator checks schema, variable order, root identity, node
order, cycles, reachability and every bounded assignment before native reconstruction.
The environment-sensitive tests now validate native capabilities instead of assuming
that native ZDD and d4 are unavailable.

## Frozen workload

- Revised manifest-bound 136-file/5,497,827-byte source/data package, SHA-256
  `a9b1a6c135fb0b5b1b6b094d0049d3318e3a1f9cbf60fb44fe221f86a69bcc7a`.
- Immutable 1,078,139-byte transport ZIP, SHA-256
  `053ede82b0f69a1053778b74778ab7ea1b3f5af5a898924289e38d73447f92b3`;
  every member is revalidated against the manifest locally and remotely.
- Two admitted cached-real `k=8` feature-model scenarios.
- Native `cudd_bdd` only, two blocks, four cells, four fresh build processes,
  four distinct reload processes and eight exact relation rows.
- Native `dd.cudd` identity is mandatory; `dd.autoref` substitution is forbidden.
- Canonical artifacts must be byte-identical across equivalent blocks and replay
  exactly without importing or invoking CUDD.
- All 25 focused tests must pass with no failure, error or skip.
- Source identity must remain unchanged. This is functional evidence only; no
  performance ranking is permitted.

## Resources, budget and cleanup

One secure 2-vCPU/4-GB CPU pod, pinned Python 3.13.15 amd64 image, 12 GB ephemeral
container disk, zero pod volume, no network volume, 1,200-second lifetime and
1,080-second cleanup deadline. Projected phase cost remains below $0.10 and the
aggregate campaign remains below the user's $10 cap. One create is permitted;
deletion and empty v1/v2 inventories are required for every outcome.
