from types import SimpleNamespace

import pytest

from cmbench.config import BenchmarkConfig, config_from_args


def test_config_from_args_maps_phase3_fields():
    defaults = BenchmarkConfig(sizes=(2,), trials=1, seed=1, max_depth=2)
    assert defaults.cm_hybrid_threshold == 16
    assert defaults.cm_words_eval is False

    args = SimpleNamespace(
        sizes="2,3",
        trials=1,
        seed=5,
        max_depth=2,
        out_prefix="out",
        depth_sweep="1,2",
        html="report.html",
        print_summary=True,
        cm_parallel_workers=4,
        cm_parallel_min_n=6,
        cm_parallel_no_shared_memory=True,
        cm_debug_stats=True,
        cm_report_ir_breakdown=True,
        cm_profile_cached_exec=True,
        cm_runpod_local_mock=True,
        cm_runpod_stop_after_run=True,
        cm_runpod_fallback_local=True,
    )

    config = config_from_args(args)

    assert config.out_prefix == "out"
    assert config.depth_sweep == "1,2"
    assert config.html == "report.html"
    assert config.print_summary is True
    assert config.cm_parallel_workers == 4
    assert config.cm_parallel_min_n == 6
    assert config.cm_parallel_no_shared_memory is True
    assert config.cm_debug_stats is True
    assert config.cm_report_ir_breakdown is True
    assert config.cm_profile_cached_exec is True
    assert config.cm_runpod_local_mock is True
    assert config.cm_runpod_stop_after_run is True
    assert config.cm_runpod_fallback_local is True


def test_config_validate_rejects_invalid_phase3_values():
    with pytest.raises(ValueError, match="invalid cm_exec_target"):
        BenchmarkConfig(sizes=(2,), trials=1, seed=1, max_depth=2, cm_exec_target="remote").validate()

    with pytest.raises(ValueError, match="invalid partial_output_mode"):
        BenchmarkConfig(sizes=(2,), trials=1, seed=1, max_depth=2, partial_output_mode="compact").validate()

    with pytest.raises(ValueError, match="family_size"):
        BenchmarkConfig(sizes=(2,), trials=1, seed=1, max_depth=2, family_size=0).validate()
