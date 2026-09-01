# P7 W5 development freeze v1

This package freezes the principal P7A/P7B development ablation as four
sequential Runpod allocations. It projects the original pre-timing V4 corpus
into two balanced shards per policy without changing cases, arms, metrics, or
within-case schedules.

The W3 `sqrt` case remains a typed feasibility exclusion: its policy-independent
oracle generation exceeded 780 seconds, so repeating it inside a 20-minute W5
allocation would prevent any measured cells from running. It is retained in
completion/frontier reporting and is not counted as a success. The remaining
57 cases are partitioned 29/28 within role and source-kind strata.

IR uses the frozen 8-block minimum. W4's predeclared 5% noise rule triggered the
relation extension, so both relation shards run the frozen 20-block maximum.
Each allocation also runs the same two-case synthetic/natural diagnostic anchor
as a separately labeled output; anchors are not independent primary formulas.

Primary cells: 7524. Cells including repeated diagnostic
anchors: 7852.
