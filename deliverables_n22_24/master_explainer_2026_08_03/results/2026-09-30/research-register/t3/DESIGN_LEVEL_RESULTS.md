# Independent-design timing summary

Descriptive medians of paired comparator/T3 full-lifecycle ratios over the frozen k/batch cells, using two repetitions per cell. Values above 1 favor T3. These design rows are the independent observational units; cells and outputs are not independent designs. The T3 column is the secondary sparse orientation-adaptive implementation, not the primary dense prediction.

| Design | Raw factors / T3 | Historical histogram / T3 | Compiled packed / T3 | CUDD + native count / T3 |
|---|---:|---:|---:|---:|
| adder | 0.776 | 1.922 | 0.102 | 1.714 |
| cavlc | 1.554 | 2.335 | 0.212 | 7.691 |
| ctrl | 2.697 | 3.356 | 0.598 | 33.296 |
| dec | 3.749 | 4.217 | 0.615 | 32.902 |
| i2c | 5.116 | 4.797 | 0.409 | 11.269 |
| int2float | 2.564 | 38.194 | 0.268 | 9.444 |
| mem_ctrl | 5.464 | 5.483 | 0.504 | 18.745 |
| multiplier | 0.551 | 2.043 | 0.111 | 1.819 |
| router | 1.692 | 1.979 | 0.755 | 81.323 |
| sqrt | 0.940 | 2.459 | 0.127 | 2.858 |
| square | 0.729 | 1.779 | 0.129 | 2.453 |

The compiled packed comparator has a lower design-median full lifecycle in every listed design. Router is a constant-only admitted slice and must not be presented as a nontrivial favorable application. T3 has lower full-lifecycle medians than the CUDD compilation path in each listed design, but the compiled CUDD online phase is faster at every design median. Construction/compilation and repeated counts therefore tell different stories.

See `results/DESIGN_TIMING_AGGREGATES.json` for dense and adaptive states, both modes, per-design cells and online ratios. `LIFECYCLE_SUMMARY.csv` separates all requested payload and phase measures. Cold trials have only one repetition per panel cell; their full raw phases and isolated process RSS are in `results/COLD_SUMMARY.json`, not pooled with this table.