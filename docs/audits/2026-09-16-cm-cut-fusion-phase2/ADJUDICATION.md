# Bounded two-operand cut fusion: Phase-2 adjudication

Date: 2026-09-16

Baseline HEAD: `015f5cbb70b112795c08b61c27924c1ee752b9e9`

Decision: **STOP**

The opt-in recognizer is exact on the completed campaign and reduces the execution kernel on its favorable synthetic identities. Its recognition and compilation cost is too large to repay at the frozen measured reuse levels. The locked F1/F2 confirmation produced **0.4932x** q64 whole-session speed versus CSE, below the frozen **1.10x** requirement, and lost all seven paired rounds. Per the frozen protocol, the experiment stops without tuning, promotion, natural-panel timing, or a separate memory-promotion sweep.

## Implemented candidate

[`cmbench/recognition/cut_fusion.py`](../../../cmbench/recognition/cut_fusion.py) implements a research-only pass with no default dispatch change. It:

- propagates exact four-bit Boolean tokens over cuts with at most two structural operands;
- uses a proved 16-function template table and explicit operand polarity/permutation alignment;
- rejects unsafe cut interiors with external fanout;
- selects bottom-up, non-overlapping rewrites in one batch and does not rematch;
- preserves ambient variable order, including axes made irrelevant by a rewrite;
- returns the original expression on refusal or failed profitability;
- accepts only programs saving at least two bigint operations and 10%, without increasing reported peak live word buffers; and
- enforces the frozen limits: 4,096 nodes, depth 96, eight nontrivial cuts per node, 32-node shells, 400,000 cut pairs, 1,000,000 shell visits, and 256 rewrites.

The default compiler and evaluator remain unchanged.

## Evidence integrity

Stage A ran each candidate and control in a supervised Windows Job with one CPU, a 512 MiB hard committed-memory limit, a 60-second worker limit, cleanup verification, and capped output. The timing campaign used the same containment, seven fresh-process paired rounds, rotating and reversing arm order, fresh q sessions, cleared caches, and exact result hashes from an out-of-timing direct oracle.

| Split | Cases | Worker receipts | Timing rows | Exact request outputs | Refusals |
|---|---:|---:|---:|---:|---:|
| Synthetic development | 24 | 168 | 8,736 | 185,640 | 0 |
| Locked synthetic confirmation | 36 | 252 | 13,104 | 278,460 | 0 |
| **Total** | **60** | **420** | **21,840** | **464,100** | **0** |

Every timing row completed, every worker cleaned up, and every arm returned the same ordered output hashes for its case, round, and q. Peak worker committed memory was 407,302,144 bytes in development and 414,388,224 bytes in confirmation, both below the 536,870,912-byte cap. These are whole-worker peaks, so they do not establish the required per-arm 1.25x memory ratio.

The final verification is reproducible with [`verify_phase2.py`](verify_phase2.py); its output is [`phase2-verification.json`](phase2-verification.json). Earlier Stage-A v1-v3 artifacts are retained as superseded diagnostics. V1 and v2 exposed an unbounded diagnostic serialization bug; v3 fixed it, and v4 replayed the final source-bound static stage cleanly.

## Frozen gates

| Gate | Result | Evidence |
|---|---|---|
| Stage A correctness, containment, and activation | **PASS** | F1 and F2 activated; 14/64 EPFL cases activated versus the required 8; all 18 C36 cases retained; zero resource failures. Three EPFL expressions over depth 96 were exact candidate refusals and stayed in the output. |
| Locked F1/F2 q64 speed >=1.10x and win every round | **FAIL** | 0.4932x versus CSE; round speedups 0.5260, 0.4571, 0.4330, 0.5047, 0.4724, 0.5233, 0.5145. |
| Exposed EPFL q64 speed >=1.05x | **NOT RUN AFTER STOP** | The earlier locked confirmation gate failed decisively. Stage A showed static activation in 14/64 EPFL cases, which is not timing evidence. |
| F3-F6/C36 cohort and individual floors | **FAIL on completed F3-F6** | Every F3-F6 cohort/q result was below the 0.95x floor; individual minima were also below 0.80x. C36 timing was not run after the earlier stop. |
| Peak memory <=1.25x CSE and under absolute cap | **PARTIAL** | All completed workers stayed under the absolute cap. A per-arm relative sweep was not run after the latency stop. |

The overall decision is **STOP**, as required by the first failed frozen gate. The recognizer remains an isolated experiment and is not wired into production or default dispatch.

## Locked confirmation ledger

Equal-weight geometric means over the 12 locked F1/F2 cases at q64:

| Component | CSE control | Candidate CSE | Candidate/control observation |
|---|---:|---:|---|
| Parse | 148,083 ns | 174,690 ns | Candidate slower |
| Compile/recognize/rewrite | 158,759 ns | 3,179,205 ns | Candidate adds about 3.02 ms |
| Bind | 914,194 ns | 931,650 ns | Similar |
| Execute | 987,484 ns | 589,960 ns | Candidate execution is faster |
| Output | 189,064 ns | 199,396 ns | Similar |
| **Whole session** | **2,583,926 ns** | **5,238,760 ns** | **0.4932x speed** |

The experiment found a real execution reduction, but recognition and compilation dominate through q64. Using each case's q64 median setup and stationary per-request costs gives estimated crossings from q132 to q1,620. All estimates lie outside the measured q1/q4/q16/q64 range. They assume comparable repeated requests and are not measured performance claims; the protocol forbids invented q256/q1024 wins.

The complete F3-F6 control results reinforce the setup-cost problem:

| Family | q1 speed | q4 speed | q16 speed | q64 speed | Worst individual case |
|---|---:|---:|---:|---:|---:|
| F3 | 0.0854x | 0.1312x | 0.2472x | 0.5259x | 0.0653x |
| F4 | 0.0880x | 0.1357x | 0.2439x | 0.4651x | 0.0690x |
| F5 | 0.0701x | 0.1097x | 0.2145x | 0.3981x | 0.0567x |
| F6 | 0.1075x | 0.1475x | 0.3131x | 0.5467x | 0.0851x |

Each cell compares candidate CSE with the best fixed control for that family and q. Direct evaluation is best at q1/q4; CSE is best at q16/q64.

## Checks

- Focused semantic/compiler suite: **86 passed in 4.33 s**.
- `tests/test_d10_rule_engine.py`: **5 passed, 4 subtests passed, 1 failed**. The sole failure is the pre-existing Windows CRLF byte-hash mismatch for `docs/recognition/source_fixtures/yosys-bench-human-decomposition-20260830/LICENSE.txt`: working SHA-256 `44d054188ebd92dbbd86093849ae6779e937bd7e719269b05e2a459690740293`, while the expected and HEAD-blob SHA-256 is `4722e5e40d884575cf601b2eb63904778e66822b5db2d0c4bab7affcdddbd954`. LF normalization in memory matches the Git blob. No validator or fixture was changed.
- Final verifier: **STOP reproduced**, with expected row/receipt counts, exact cross-arm output hashes, clean worker receipts, a 0.4932322426x primary result, and stationary q estimates of 132-1,620.

The focused command was:

```text
python -B -m pytest tests/test_cut_fusion.py tests/test_cm_pair_alignment.py tests/test_bitset_backend.py tests/test_bitset_cse.py tests/test_cm_ir_cost.py tests/test_cm_ir_wide_associative.py tests/test_rule_normalization.py -q -p no:cacheprovider
```

## Limitations

- Local ABC was unavailable on `PATH`; nothing was installed. This experiment makes no external-synthesis superiority claim.
- The completed timing rows aggregate cut discovery and rewrite into compile time. They do not split those candidate subphases or include a retained-plan replay diagnostic.
- The exposed EPFL/C36 panel was used for static activation only. Natural timing, the relative memory sweep, and retained-plan replay were skipped after the frozen locked latency gate failed.
- Synthetic renamings and sizes within F1/F2 are correlated mechanism checks, not independent application families.

## Artifacts

- Candidate: [`cmbench/recognition/cut_fusion.py`](../../../cmbench/recognition/cut_fusion.py)
- Tests: [`tests/test_cut_fusion.py`](../../../tests/test_cut_fusion.py)
- Frozen generator input: [`synthetic-manifest.json`](synthetic-manifest.json)
- Proved templates: [`template-table.json`](template-table.json)
- Final Stage A: [`stage-a-results-v4.json`](stage-a-results-v4.json)
- Development timing: [`stage-b-development-results.json`](stage-b-development-results.json)
- Locked confirmation timing: [`stage-b-locked_confirmation-results.json`](stage-b-locked_confirmation-results.json)
- Machine-readable decision: [`phase2-verification.json`](phase2-verification.json)

No commit, push, publishing, dependency installation, cloud/paid resource, production change, or other-checkout access occurred.
