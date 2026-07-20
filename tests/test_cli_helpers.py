from argparse import Namespace

from cmbench.cli import apply_preset_args, build_config_and_context, parse_depth_sweep, parse_sizes


def _minimal_args(**overrides):
    values = {
        "sizes": "2,3",
        "trials": 1,
        "seed": 7,
        "max_depth": 2,
        "depth_sweep": "",
        "experiment": "none",
        "compare_robdd_cm": False,
        "cm_compare_hybrid": False,
        "cm_compare_no_reinflate": False,
        "cm_exec_target": "local",
        "no_bitset": False,
        "no_dd": False,
        "no_robdd_dd": False,
        "cm_parallel": False,
        "cm_use_persistent_cache": False,
        "robdd_order_policy": "fixed",
        "robdd_order_sweeps": 1,
    }
    values.update(overrides)
    return Namespace(**values)


def test_parse_sizes() -> None:
    assert parse_sizes("2,4,8") == [2, 4, 8]
    assert parse_sizes((1, 3)) == [1, 3]


def test_parse_depth_sweep() -> None:
    config, _ = build_config_and_context(_minimal_args(depth_sweep="1,2,3"))
    assert parse_depth_sweep(config) == [1, 2, 3]


def test_apply_preset_args_compare_robdd_cm() -> None:
    args = apply_preset_args(_minimal_args(compare_robdd_cm=True))
    assert args.no_bitset is False
    assert args.no_dd is False
    assert args.no_robdd_dd is False
    assert args.cm_compare_no_reinflate is True
    assert args.cm_use_persistent_cache is True


def test_build_config_and_context_minimal_namespace() -> None:
    config, ctx = build_config_and_context(_minimal_args())
    assert config.sizes == (2, 3)
    assert config.trials == 1
    assert ctx.config is config
