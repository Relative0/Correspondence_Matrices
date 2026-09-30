# Consolidated computation ledger

| ID | Work | Status and evidence |
|---|---|---|
| C1-existing | Audit oracle, rank/class, restriction and MSB/LSB integration | Prior 4,912-file manifest reverified; unchanged package included; see `STATUS_AT_INTAKE.md` |
| T3-01 | Frozen Phase 2 intake | Original Theory ZIP retained; SHA-256 a2d84288aafa9b1ec38ea794a6830aa2120028b5ec96d334e8e745c4e64abbec |
| T3-02 | Preregistration | `PROTOCOL.json` and hash frozen before new results; dense inequality unchanged |
| T3-03 | Independent state implementation | Named moment arrays, fixed-width codec, cumulative horizon, no retained source; `state.py` |
| T3-04 | Exhaustive contract checks | Windows/Linux PASS; 122,120 prefixes, residual round trips and 117,792 update-work checks |
| T3-05 | Optimized exact comparator | CUDD compilation/sifting plus C++17 -O3 integer counting; native packed and direct-factor kernels; 592,960 comparator prefix checks |
| T3-06 | Corpus and incidence | Existing 20-design corpus reused; 8,479 case/depth rows; full provenance and exclusions retained |
| T3-07 | Main execution | 16,752 PASS, 400 UNSUPPORTED allocation-cap cells; `trials_main.jsonl` |
| T3-08 | Complement controls | Addendum frozen before execution; 3,072 PASS; `trials_complement.jsonl` |
| T3-09 | Verified page-cold process loads | 115 PASS, five allocation-cap exclusions; producer/consumer/command/cache records retained |
| T3-10 | Independent Theory replay | Original 3,749,102 checks and 74,384 factor cases reproduced exactly; only output path rebound in memory |
| T3-11 | Raw-source boundary | Eleven selected natural cases re-extracted from hashed BLIF, factors rediscovered and verified; separate phase records |
| T3-12 | Cross-check and analysis | 7,445,928 actual queries and 70,662 updates; payload and update formula checks PASS; per-design summaries |
| T3-13 | Finite storage qualification | Nine primary-favorable pairs fail actual raw-serialization crossover; metadata explicitly separated; no theorem-correctness failure |
| T3-14 | Isolated full-lifecycle memory | Same fixed panel; 115 PASS and five cap exclusions, 21,056 extra actual queries and 214 updates; no pooling into campaign timing |

No old manuscript, source package, historical result or repository tracked file was changed. No commit, push, publication or Runpod job was performed. Full C1 provenance and original failures remain in `PRIOR_PHASE_PACKAGE.zip`; new exclusions, logs and versions are retained here. No unexecuted batch contributes to results.
