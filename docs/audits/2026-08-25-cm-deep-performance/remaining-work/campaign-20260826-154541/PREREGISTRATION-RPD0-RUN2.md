# RP-D0 Run 2 Preregistration

Registered: 2026-08-26, before Run 2 creation or outcome inspection  
Prior RP-D0 cost reserve: `$0.000765`  
Authorization: one new disposable secure Runpod CPU pod

## Scope

Retry dependency feasibility after RP-D0 Run 1 proved that `dd==0.6.0`
cannot resolve under an all-binary rule because `astutils>=0.0.5` has no
wheel. This run may build only the pure-Python `astutils==0.0.6` source
distribution. It must not build CUDD or `dd` from source and makes no
performance claim.

## Frozen inputs

- Image: `python:3.13.5-slim`.
- Target binary wheels: NumPy 2.3.2, Numba 0.67.0, llvmlite 0.49.0, and
  `dd` 0.6.0.
- Source distribution: `astutils==0.0.6`, official PyPI SHA-256
  `e9a6f31b243ecfc3c7c84dd2f145cf5de83e475b650d2a6b781cfa713ad15427`.
- Wheel-building tools: setuptools 84.0.0 and wheel 0.48.0, obtained only as
  wheels and recorded with hashes.
- CUDD-related build environment variables are removed before resolution.
- The `dd` artifact must be a wheel and must already contain a `dd.cudd`
  shared object.

## Procedure and gates

1. Query PyPI release metadata over HTTPS, require the exact astutils filename,
   source type, host, and published SHA-256, then verify the downloaded bytes.
2. Build astutils with no build isolation and no dependencies after installing
   only the pinned wheel build tools.
3. Require the resulting astutils artifact to be a `py3-none-any` wheel.
4. Resolve every other installation artifact as a wheel into a local pod
   wheelhouse, then install offline from that wheelhouse.
5. Require `pip check` to pass and exact installed versions to match.
6. Verify the `dd` wheel contains the precompiled CUDD extension; record the
   installed extension hash and dynamic libraries.
7. Run deterministic exact Numba packed-word and `dd.cudd` truth/cofactor/
   canonical-rebuild smokes. Timings are diagnostic only.
8. Collect results, terminate in `finally`, and independently verify zero pods.

Acceptance requires exact source hash, a pure-Python astutils wheel, no CUDD
source build, wheel-only remaining artifacts, clean `pip check`, exact pinned
versions, successful imports, and zero smoke mismatches.

## Guards

- One pod; maximum `$0.20/hour`; 20-minute hard lifetime.
- Cumulative RP-D0 cost, including `$0.000765` already spent, must remain below
  `$0.25`.
- New scripts and output directory; refuse overwrite of Run 1.
- Upload only the new Run 2 diagnostic worker.
- Any source hash, artifact type, dependency, import, exactness, timeout, or
  teardown failure is retained and stops the campaign.

