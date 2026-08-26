# RP-D0 Run 3 Preregistration

Registered: 2026-08-26, before Run 3 implementation or outcome inspection  
Prior cumulative RP-D0 cost reserve: `$0.001302`  
Authorization: one third and final disposable secure Runpod CPU pod

## Scope

Correct the Run 2 orchestration defect by including the binary
`packaging==26.3` dependency of `wheel==0.48.0`. Build only the authorized
pure-Python `astutils==0.0.6` source distribution. All other installed
artifacts must be wheels. CUDD and `dd` source builds remain forbidden.

## Frozen inputs

- Image: `python:3.13.5-slim`.
- Build-tool wheels: setuptools 84.0.0, wheel 0.48.0, packaging 26.3.
- Packaging wheel SHA-256:
  `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c`.
- Astutils source: version 0.0.6, SHA-256
  `e9a6f31b243ecfc3c7c84dd2f145cf5de83e475b650d2a6b781cfa713ad15427`.
- Target binary wheels: NumPy 2.3.2, Numba 0.67.0, llvmlite 0.49.0, and
  `dd` 0.6.0, plus their resolver-selected wheel dependencies.
- Remove all `DD_FETCH`, `DD_CUDD`, and related native-build environment
  variables.

## Procedure and acceptance

1. Maintain separate directories for build-tool wheels, source archives,
   locally built wheels, and resolved target wheels.
2. Download build tools with no dependencies; require all three exact wheels
   and verify the packaging wheel hash before offline installation.
3. Query official PyPI JSON for the exact astutils source URL and digest,
   download within a 1 MiB bound, and verify before execution.
4. Build astutils without build isolation or dependency fetching; require one
   `py3-none-any` wheel and record its hash.
5. Resolve targets with `--only-binary=:all:` using the built astutils wheel;
   reject any non-wheel target artifact.
6. Require the selected `dd==0.6.0` wheel to contain a precompiled
   `dd.cudd` shared object before installation.
7. Install offline from the frozen wheel directories, require `pip check`,
   exact installed versions, imports, and recorded license/artifact hashes.
8. Run deterministic exact Numba packed-word and CUDD truth/cofactor/canonical
   smokes. Timings are diagnostic only and support no performance claim.
9. Terminate in `finally`; run an independent zero-pod inventory.

Any hash, package type, resolution, build, install, import, exactness, timeout,
budget, or teardown failure is retained and ends the final campaign.

## Guards

- One pod, maximum `$0.20/hour`, 20-minute hard lifetime.
- Cumulative RP-D0 spending including `$0.001302` remains below `$0.25`.
- Upload only the new Run 3 worker.
- New refuse-overwrite scripts, audit directory, and pre/post inventories.
- No further pod is authorized after this run.

