# Output-Budget Continuation

Date: 2026-07-26

## Outcome

The highest-priority deferred resource-safety item now has a shared,
representation-aware implementation across core materialization, reusable
evaluation, benchmark workflows, equivalence/operator-difference paths, and
the remote protocol.

## Contract

`cmbench/output_budget.py` defines:

- `OutputStatus`: `ok`, `reduced`, `refused`, `timeout`, `oom`, and
  `unvalidated`;
- `OutputBudget`: output bytes, estimated temporary bytes, legacy variable
  limit, and reduced-output permission;
- `OutputEstimate` and `OutputBudgetDecision`;
- typed `OutputBudgetExceeded`, which remains a `ValueError` for compatibility.

Full output is attempted first. Reduced output is selected only when the full
artifact exceeds the budget, reduction is explicitly allowed, and the reduced
artifact fits. Otherwise evaluation is refused before explicit allocation.

## Defaults and compatibility

- Direct APIs default to a 256 KiB explicit-output limit. This retains the
  existing dense `n=18` parallel workflow.
- Benchmark and remote configuration default to 64 KiB and retain
  `cm_max_full_output_vars=16`.
- `OutputBudget()` or an explicitly supplied larger budget supports controlled
  callers that need a different limit.
- Existing return shapes and CSV fields remain intact.
- `FinalNoReinflateResult` adds typed status/decision metadata.
- Remote request/response schemas add byte limits and status fields while
  accepting older requests with fields absent.

## Coverage

New tests cover:

- dense boundaries at 15, 16, 17, 18, 20, 24, and 32 variables;
- packed representation byte boundaries;
- refusal before dense allocation;
- reduced-output status and variable projection;
- temporary-memory refusal;
- equivalence refusal versus generic error;
- remote request/response compatibility, refusal, and reduction.

Verification:

```text
python -m pytest -q
223 passed in 135.56s
```

The isolated code commit `4be1543` was also exported from the Git index and
tested without the pre-existing uncommitted V4 changes:

```text
188 passed in 109.57s
```

The first full run exposed a too-strict 64 KiB direct default through the
existing dense `n=18` parallel test. The direct limit was corrected to 256 KiB;
the test and complete suite then passed.

## Remaining dependency

Output admission bounds one artifact/request, but retained process memory still
depends on entry-bounded caches, per-thread scratch, and unbounded remote
concurrency. Those must be implemented together as the next package. See
`NEXT-AGENT-IMPLEMENTATION-PROMPT.md`.
