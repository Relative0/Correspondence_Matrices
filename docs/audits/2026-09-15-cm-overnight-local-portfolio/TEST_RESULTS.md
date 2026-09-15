# Overnight local CM portfolio test results

The frozen schedule completed all 271 fresh-process module cells. 232 modules passed, 30 contained baseline-matched pytest nonpasses, eight made expected collection refusals for absent optional dependencies or Windows platform limits, and one optional-control module skipped every test. No module ended in a harness or resource error.

Across 1912 collected test cases, 1819 passed, 45 failed, 39 errored and 9 were skipped. The 76 supported nonpassing test IDs and outcome kinds exactly match the retained September 14 baseline. The additional eight collection records come from modules that the baseline explicitly excluded after readiness collection; there are no new or resolved supported nonpassing tests.

## Containment

All process-tree cleanups verified. No timeout or resource limit fired. The run used 1000.756 seconds elapsed and 642.484 summed worker CPU seconds. Maximum job peak committed memory was 1208868864 bytes; maximum captured output from one module was 35383 bytes.

## Group outcomes

| Group | Passed modules | Nonpassing modules |
| --- | ---: | ---: |
| affine | 40 | 0 |
| biology | 6 | 0 |
| core_and_synthetic | 140 | 29 |
| exact_controls | 10 | 1 |
| feature_models | 7 | 0 |
| hardware | 10 | 9 |
| lifecycle | 19 | 0 |

The run ledger calls every nonzero pytest exit `backend_error` because the frozen supervisor reports worker exits generically. JUnit separates 30 baseline-matched nonpassing modules, eight expected collection refusals, and one all-skipped optional CUDD module. The immutable ledger is preserved; this terminal analysis supplies the corrected interpretation.

## Nonpassing and refused modules

| Module | Failures | Errors |
| --- | ---: | ---: |
| `tests/test_c38_linux_replication.py` | 2 | 0 |
| `tests/test_c7_linux_confirmation.py` | 1 | 0 |
| `tests/test_cm_comparative_h6_representation_estimator_candidate.py` | 1 | 0 |
| `tests/test_cm_comparative_native_portfolio.py` | 1 | 0 |
| `tests/test_cm_comparative_native_scout.py` | 1 | 0 |
| `tests/test_cm_comparative_native_transport.py` | 5 | 0 |
| `tests/test_cm_comparative_p7_package.py` | 1 | 0 |
| `tests/test_cm_p7_w5_freeze.py` | 1 | 0 |
| `tests/test_cm_runpod_corpus_offline.py` | 1 | 0 |
| `tests/test_d10_rule_engine.py` | 1 | 0 |
| `tests/test_exact_dispatcher.py` | 0 | 11 |
| `tests/test_generated_public_chart_data.py` | 1 | 0 |
| `tests/test_linux_one_pass_confirmation.py` | 2 | 0 |
| `tests/test_native_portfolio_reassessment.py` | 1 | 0 |
| `tests/test_natural_cut_ranking.py` | 0 | 1 |
| `tests/test_natural_decomposition.py` | 0 | 1 |
| `tests/test_natural_variable_cut.py` | 0 | 1 |
| `tests/test_neural_reassessment.py` | 0 | 4 |
| `tests/test_normalization_experiment.py` | 1 | 0 |
| `tests/test_packed_io_campaign.py` | 0 | 1 |
| `tests/test_post_benchmark_neural_gate.py` | 0 | 6 |
| `tests/test_query_ladder_q64_execution.py` | 2 | 0 |
| `tests/test_recognition_computation.py` | 2 | 0 |
| `tests/test_recognition_neural.py` | 0 | 1 |
| `tests/test_recognition_rules.py` | 1 | 0 |
| `tests/test_rule_profitability.py` | 2 | 0 |
| `tests/test_source_anf_hybrid.py` | 0 | 1 |
| `tests/test_variable_decomposition.py` | 0 | 1 |
| `tests/test_version_history_learning_protocol.py` | 1 | 10 |
| `tests/test_bucket_cudd_reference.py` | 0 | 0 |
| `tests/test_cm_architecture_comparison_package.py` | 3 | 0 |
| `tests/test_cm_architecture_query_ladder_cross_machine_package.py` | 3 | 0 |
| `tests/test_cm_architecture_query_ladder_followup.py` | 1 | 0 |
| `tests/test_cm_architecture_query_ladder_package.py` | 4 | 0 |
| `tests/test_cm_architecture_query_ladder_retry_002_analysis.py` | 1 | 0 |
| `tests/test_cm_architecture_query_ladder_retry_002_package.py` | 3 | 0 |
| `tests/test_cm_epfl_context_pilot.py` | 1 | 0 |
| `tests/test_cm_runpod_w8_logikbench_conversion.py` | 1 | 0 |
| `tests/test_yosys_source_anf.py` | 0 | 1 |

The supported failures are retained source/artifact drift, unavailable historical packages, platform assumptions, and previously recorded test errors. Exact supported test-ID parity with the prior baseline means this campaign found no new regression. The nine refused/all-skipped modules preserve explicit dependency and platform readiness outcomes rather than silently omitting them.
