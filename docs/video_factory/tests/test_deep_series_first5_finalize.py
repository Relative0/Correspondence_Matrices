from __future__ import annotations

from pathlib import Path
import sys


FACTORY_ROOT = Path(__file__).resolve().parents[1]
if str(FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(FACTORY_ROOT))

import deep_series_first5_finalize as finalize


def test_first_five_audio_and_mux_timing_topology_is_complete():
    result = finalize.validate_timing()
    assert result == {
        "status": "passed",
        "episodes": 5,
        "chapters": 17,
        "cues": 268,
        "frames": 68399,
    }


def test_native_voice_rate_adjustment_is_bounded():
    assert finalize.VOICE == "Microsoft Mark"
    assert finalize.VOICE_RATE == 1
    assert finalize.SAMPLE_RATE == 24000
