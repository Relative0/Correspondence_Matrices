from __future__ import annotations

import pytest

from cmbench.recognition.gf2_work_policy_experiment import C19Config


def test_c19_config_bounds() -> None:
    C19Config("test", rounds=3, max_seconds=120).validate()
    with pytest.raises(ValueError):
        C19Config("test", rounds=2, max_seconds=120).validate()
    with pytest.raises(ValueError):
        C19Config("test", rounds=3, materialize_budget=3, max_seconds=120).validate()
