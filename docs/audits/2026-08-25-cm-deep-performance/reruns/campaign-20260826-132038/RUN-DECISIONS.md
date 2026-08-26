# Run Decisions

## Confirmed

- Retained CM semantics, canonical DAG order, cache identity tests, packed
  outputs, and above-guard refusal behavior are healthy.
- Preparation remains the leading local optimization surface.
- The one-memo change retains a reproducible approximately 2.5%--2.7% local
  preparation improvement on representative reused corpora and an approximately
  11.8% smoke traced-peak reduction.
- Keep `WORDS_AUTO_MIN_VARS=16`; the universal lower-threshold retune still
  fails its catastrophic-routing gate. The independent i10 corpus now adds
  transfer evidence: about `1.012x` oracle regret and zero catastrophes.
- Treat the retained one-memo preparation change as cross-host confirmed: all
  three Runpod CPU flavors reproduced a useful direction with exact outputs.

## Rejected

- DP-R1 rational compact-order labels: exact, but 1.83x slower overall and
  1.24x higher traced peak; reverted.
- A production cache/family selector based on these synthetic all-hit runs:
  BitSet remained the strongest whole-workload baseline.
- The BX1-trained ridge feature selector: on untouched i10 it produced 7 raw
  and 11 CM catastrophic routes and was 10.8%/12.2% worse in regret than k16.
  Do not retune it on i10 and relabel the result as validation.

## Interesting but not accepted

- Partial contexts at `n=16`, 500 overlapping contexts, and at least 50% fixed
  reached approximate CM/BitSet parity. Validate this on a real context trace
  with more repetitions and a task-matched BDD restriction comparator.
- Fresh V3 point estimates differ from the accepted local run while agreeing
  with the old Runpod range. Add run/machine-level replication to future
  uncertainty statements; do not replace accepted history silently.

## Still blocked by dependencies or real workloads

- Native CUDD or Numba/LLVM: dependency installation/build approval required.
- A production feature selector requires another independently frozen circuit
  family and a model class that passes training CV before held-out timing.
- Cache, family, and partial-context production claims still require real
  access/edit/context traces.

No production selector, cache policy, output guard, or API default changed.
