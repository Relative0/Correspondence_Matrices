"""A prospective freeze must verify after its actual on-disk JSON encoding."""
import json
from pathlib import Path

import pytest

from cmbench.comparative import gf2_native_slot_batch_workload as workload


def test_freeze_and_oracles_survive_sorted_json_roundtrip():
    root = Path(__file__).resolve().parents[1]
    freeze = workload.build_freeze(project_root=root, source_checkpoint="0" * 40)
    restored = json.loads(json.dumps(freeze, indent=2, sort_keys=True))
    assert workload.digest(restored) == workload.digest(freeze)
    workload.validate_freeze(restored, root)
    oracles = workload.build_oracles(restored)
    workload.validate_oracles(json.loads(json.dumps(oracles, sort_keys=True)), restored, replay=True)
    restored["cohort"]["cases"][0]["live_width_counts"]["7"] += 1
    with pytest.raises(ValueError, match="freeze identity"):
        workload.validate_freeze(restored, root)
