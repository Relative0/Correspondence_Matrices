# Runpod P7 W3 correctness/oracle result audit

Date: 2026-08-30  
Status: passed with one shared oracle-feasibility exclusion

## Scope

This audit covers the W3 correctness/oracle campaign run from the exact authorized 96-file P7 V2 private bundle. The uploaded ZIP stayed byte-identical across attempts:

- bundle SHA-256: `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`
- parent freeze SHA-256: `54ea61a38135426975a0d1fead9b24c020dc565eb3d952356640fa38062598dd`
- policies: `p7-ir` and `p7-relation`
- roles: regression and development
- performance measurement: false

The campaign evaluated each retained policy/case arm in a fresh worker process against the policy-independent scalar oracle. It did not collect a benchmark-grade timing sample and does not support performance rankings.

## Result

| Policy | Parent cases | Verified cases | Parent cells | Verified cells | Excluded cells |
| --- | ---: | ---: | ---: | ---: | ---: |
| `p7-ir` | 58 | 57 | 232 | 228 | 4 |
| `p7-relation` | 58 | 57 | 290 | 285 | 5 |
| **Combined** | **116 policy/case slots** | **114** | **522** | **513** | **9** |

All 513 retained cells completed successfully and matched the independent oracle result. The successful evidence contains 513 distinct pod/process identities, one per cell. All eight successful shards also passed the same 42 focused tests with zero failures, errors, or skips and installed the exact 13 locked binary dependency versions.

The sole exclusion is `development-epfl-sqrt-31cdaf5d0213`. Its policy-independent scalar oracle exceeded the fixed 780-second stage limit when isolated. Because oracle generation occurs before and independently of a policy arm, the timeout does not show a CM-arm correctness failure. A second relation-policy attempt would have repeated the same oracle computation and was intentionally skipped.

## Independent verification

`verify_p7_w3_final_v7_outcome.py` independently checked:

- all 14 attempt records and cleanup receipts;
- every member of each successful evidence ZIP against the extracted bytes;
- focused JUnit identities and outcomes;
- locked dependency versions;
- original or derived freeze validity and exact parent-case partitioning;
- source identity before and after each run;
- plan, oracle package, checksums, ledgers, summaries, and reconciliations;
- one `running` and one `ok` ledger row per cell;
- request/result hash agreement between the scalar oracle and worker result;
- process isolation, resource-stream completeness, and RSS records;
- exact combined coverage and the single shared exclusion.

The machine-readable audit is `P7-W3-FINAL-INDEPENDENT-AUDIT.json`.

## Attempts and cost

There were 14 local attempt identities:

- 8 successful shards;
- 5 created-pod failures used to diagnose transport or oracle sizing;
- 1 fail-closed local refusal when another task's pod was present, with no create, upload, or cost.

The controller-derived estimated W3 compute cost is `$0.07571552981138228`. The read-only billing query currently reports `$0.04767928388901055` for seven W3 pod IDs and may lag. The larger controller-derived estimate is the appropriate current campaign charge bound.

The final postflight at `2026-08-30T08:56:43Z` found:

- empty v1 and v2 Runpod inventories;
- HTTP 404 from both API versions for all 13 created W3 pod IDs;
- no remaining W3 resource.

The machine-readable live reconciliation is `P7-W3-FINAL-POSTFLIGHT.json`.

## Interpretation and next gate

W3 now provides broad functional evidence for both P7 policy families over the frozen regression and development corpus. It supports proceeding to the confirmation-corpus freeze and then a separately designed performance scout.

It does not establish relative speed, memory superiority, real-world generality beyond the frozen cases, or behavior for the excluded square-root oracle case. Any later performance study should use a benchmark-specific freeze, warmup and repetition rules, paired scheduling, resource controls, and explicit competitor versions. A different private upload bundle still requires exact payload disclosure even though the standing Runpod spend authorization covers up to `$5`.
