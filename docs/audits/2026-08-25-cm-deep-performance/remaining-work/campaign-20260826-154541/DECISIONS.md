# CM Remaining-Work Campaign Decisions

Date: 2026-08-26

## Keep

- Keep the dependency-free trace schema, null sink, bounded JSONL sink,
  validator, and logical replay summary.
- Keep tracing off by default.
- When tracing is explicitly enabled, keep deterministic 1/16 workload
  sampling as the default. Every emitted workload event records
  `sample_every=16`, and the session records policy `sampled`.
- Keep full capture available only as an explicit, bounded diagnostic using
  `--cm-trace-sample-every 1`.
- Keep all three overhead studies, including both failed full-rate attempts.
- Keep the RP-D0 failure artifact: the binary-only resolver stopped before
  installing `dd` because its `astutils` dependency has no wheel. Teardown and
  the zero-pod postflight both passed.
- Keep RP-D0 Run 3 as the final dependency-feasibility result. Its corrected
  build-tool wheelhouse installed successfully and its authorized astutils
  source build succeeded, then clean binary target resolution stopped on the
  additional source-only PLY 3.10 requirement. Teardown and the independent
  zero-pod postflight passed.

## Reject

- Reject continuous/full-rate JSONL capture as a routine or production
  recommendation. Even after removing duplicate hashing, merging events, and
  reducing JSON work, the median whole-call overhead was 11.7%.
- Reject any performance claim from the trace mechanics corpus.
- Reject using sampled traces for exact cache replay or reuse-rate claims.
- Reject adding Numba, llvmlite, CUDD, or native build requirements to the
  shared repository environment from feasibility evidence alone.
- Reject changing `WORDS_AUTO_MIN_VARS=16`, selector policy, cache policy, or
  output guards in this campaign.
- Reject further RP-D0 cloud work under the current authorization and source
  contract. The third-and-final pod authorization has been consumed.
- Reject interpreting the dependency gate as a Numba or CUDD runtime result;
  target installation, imports, and exactness smokes were never reached.

## Pending

- RP-D0 standard installation under the final authorized contract is rejected
  as infeasible: after the permitted astutils source build succeeds,
  `dd==0.6.0` still requires source-only PLY 3.10. Any future source build of
  PLY or `--no-deps`/metadata exception requires wholly new authorization and a
  new preregistered campaign; none is recommended without a real workload.
- Real cache/family/context work remains pending an identified workload and
  trace owner. Collection-volume targets and stop rules remain those in the
  dated remaining-work plan.
- A replayable trace mode remains deferred because it changes the data-content
  risk and has no named workload yet.

## Promotion gates

The trace foundation can be reviewed as experimental infrastructure, but it is
not a production telemetry recommendation. Downstream implementations require:

1. a named real workload and declared output/query artifact;
2. adequate request/version/context volume;
3. preregistered equivalent-artifact comparisons;
4. exactness, bounded memory, cold/warm, held-out, and rollback checks;
5. a new external-action approval for each Runpod or dependency campaign.
