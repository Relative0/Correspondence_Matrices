# Frozen T3 computation — consolidated Master package

Start with [HANDOFF_TO_MASTER.md](HANDOFF_TO_MASTER.md). The computation supports T3 correctness and its counter payload/update formulas under the frozen contract, while qualifying the finite serialized-byte crossover and practical performance claims. No manuscript was changed.

- [Verified prior work and missing pieces at intake](STATUS_AT_INTAKE.md)
- [Computation ledger](COMPUTATION_LEDGER.md)
- [Theorem-to-experiment crosswalk](THEOREM_EXPERIMENT_CROSSWALK.md)
- [Independent-design results](DESIGN_LEVEL_RESULTS.md)
- [Counterexamples and finite-size qualifications](MINIMIZED_COUNTEREXAMPLES.md)
- [Environment and comparator configuration](ENVIRONMENT.md)
- [Reproduction commands](REPRODUCTION_COMMANDS.md)
- [Failures, exclusions and continuations](FAILURE_TIMEOUT_RECORD.md)

`LIFECYCLE_SUMMARY.csv` separates mathematical payload, real binary size, RSS and every measured phase. `EXPERIMENT_MANIFEST.csv` indexes the raw and analyzed result files. `results/trials_*.jsonl` retain all actual queries, updates, phases and statuses. `logs/cold/` contains producer configuration, consumer result, command/return code and log files. Source code, native binary, frozen Theory documents, input factors, corpus incidence and hashes are included.

`PRIOR_PHASE_PACKAGE.zip` is the unchanged complete prior delivery, containing attributed Astra C1 evidence, the historical Draft-3 baseline, the 20-design corpus and offline dependency wheels. It is nested to avoid silently rewriting prior manifests or presenting old results as newly executed. Extract it alongside this directory for reproduction. The original Theory Phase 2 ZIP is also included.

Use `python verify_delivery.py` for a non-mutating hash check. The main protocol and complementary-control addendum remain separately hashed. The final ZIP has a separate SHA-256 sidecar next to it.

**Next: upload this single ZIP to the online Master task for the convergence gate.** Use the existing Master task, preferably GPT-6-Astra/high for the mathematical/resource interpretation. No new computation campaign is proposed before that decision.
