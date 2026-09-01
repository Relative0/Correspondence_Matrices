# C27 independent Docker second-machine protocol

## Purpose

Run the unchanged frozen C27 support-aware GF(2) package on an independent physical
machine without relying on the RunPod HTTPS payload proxy. The result is second-machine
evidence only when the Docker engine runs on hardware distinct from the Windows/Docker
host used for the C27 development and same-host portability repetitions.

## Frozen workload

- 63 source files, 1,078,671 bytes;
- Python `3.13.15` on Linux/amd64;
- base image `python:3.13.15-slim-bookworm` pinned to
  `sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`;
- NumPy `2.3.2`, installed with the single wheel hash frozen in the C27 manifest;
- 48 cases, five rounds, 720 measurement batches, 7,560 timed queries, and 24 memory
  batches;
- timing-gate failure is valid evidence when every exactness invariant passes.

## Host requirements

- Linux or a Docker host capable of running `linux/amd64` containers;
- Docker Engine with at least 2 available CPUs and 4 GiB RAM;
- network access only while pulling/building the pinned runtime;
- `bash`, `sha256sum`, and `tar` on the host;
- no repository credentials, API keys, volumes, or production data.

## Execution

1. Extract the frozen package into a new directory.
2. Verify the package manifest and `frozen.sha256` before execution.
3. Run `./run_c27.sh independent-machine` only on physically independent hardware.
   Use `./run_c27.sh same-host` for validation or repeated runs on the development
   machine; those results must not be described as second-machine evidence.
4. The script builds the manifest-pinned runtime, then runs both scientific commands
   with `--network none`, a read-only container root, read-only frozen sources, 2 CPUs,
   4 GiB RAM, all Linux capabilities dropped, and a bounded writable result mount.
5. Retrieve `c27-results.tar.gz` and `results/PORTABILITY-SUMMARY.json`. The archive must
   remain at or below 16 MiB.

## Acceptance

The package verifier requires:

- result status `complete`;
- 720 measurement batches and 7,560 timed queries;
- 24 memory batches, 48 fallback controls, 48 selected-path controls, and 10 refusal
  controls;
- zero semantic or artifact mismatches;
- independent verification status `verified`, including recomputed summaries;
- a Boolean support-aware timing gate and a bounded result archive.

Either timing-gate value is admissible. Production promotion remains false. A same-host
Docker pass proves Linux runtime portability only; only an `independent-machine` result
from distinct hardware may be compared as second-machine timing evidence.
