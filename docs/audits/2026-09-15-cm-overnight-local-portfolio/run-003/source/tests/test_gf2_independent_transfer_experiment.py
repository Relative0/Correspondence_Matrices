from __future__ import annotations

import pytest

from cmbench.recognition.gf2_independent_transfer_experiment import C18TransferConfig


def test_c18_transfer_bounds() -> None:
    C18TransferConfig("test", rounds=1, max_seconds=120).validate()
    with pytest.raises(ValueError):
        C18TransferConfig("test", rounds=4, max_seconds=120).validate()
    with pytest.raises(ValueError):
        C18TransferConfig("test", rounds=1, max_partitions=32, max_seconds=120).validate()
