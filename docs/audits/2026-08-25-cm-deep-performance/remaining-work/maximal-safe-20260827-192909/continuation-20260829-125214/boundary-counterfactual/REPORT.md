# Temporary-memory boundary counterfactual

This is a local policy analysis of a frozen Runpod measurement, not a new
benchmark. It uses the exact inclusive rule `estimate <= limit` and the
recorded comparable-window `tracemalloc` peak. It excludes output/variable
gates and cannot establish an RSS limit.

## Result

- Eligible measured calls: 360
- Candidate estimates above/equal/below peak: 360 / 0 / 0
- Legacy estimates above/equal/below peak: 75 / 0 / 285
- At `candidate estimate - 1`, false refusals: 360
- At the exact candidate estimate, false admissions: 0
- At the exact legacy estimate, false admissions: 285

The row-level JSONL records `estimate-1`, `estimate`, and `estimate+1` checks
and the complete byte interval in which each estimate/measurement pair would
disagree. The CSV separates fixed 4 MiB, 16 MiB, and 64 MiB results by role,
schedule, representation, and model.

No candidate coefficient or production default changed. Repeated calls are
retained as observations; they are not claimed as independent formulas.
