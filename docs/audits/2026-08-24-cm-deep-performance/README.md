# 2026-08-24 CM Deep Performance Audit Artifacts

Start with:

1. `CM-DEEP-PERFORMANCE-AUDIT.md` — conclusions, execution map, cost model, profile, decisions, implementation, and validation.
2. `CM-BENCHMARK-RESULTS.md` — exact commands, timing definitions, environment, dispersion, selector results, and tests.
3. `CM-RESEARCH-LEDGER.md` — primary-source review and applicability decisions.
4. `CM-OPTIMIZATION-BACKLOG.md` — ranked remaining work and rejected/theoretically blocked lanes.
5. `NEXT-AGENT-HANDOFF.md` — copy-paste continuation prompt.

Authoritative machine-readable benchmark set:

- `final_authoritative_raw.csv`
- `final_authoritative_summary.json`
- `final_authoritative_selector.csv`
- `final_authoritative_phases.csv`
- `final_authoritative_environment.json`

`final_smoke_*` is the quick post-tooling verification and records Windows affinity masks after that diagnostic was added. `audit-manifest.json` ties the authoritative files to source/corpus hashes and validation status. `current_pipeline_b2.prof` is the cProfile diagnostic, and `cache_probe_b2.json` is the allocation-instrumented persistent-cache cold/warm probe.

Other prefixes are retained development evidence:

- `deep_*`: pre-change baseline/development replays;
- `post_selector_*`: after the selector edit;
- `post_node_count_*`: after node-count memoization;
- `final_representative_all_*`: rejected `k=13` interpolation replay;
- `final_k16_representative_all_*` and `authoritative_k16_all_*`: repeated `k=16` stability replays;
- `profiled_b2_smoke_*`: small cProfile input/output;
- `baseline_smoke_*`: original general audit smoke.

The development files are not accepted historical artifacts and must not be pooled with `final_authoritative_*`. They are kept to preserve negative results and the decision trail.
