import base64
import json

import pytest

from scripts import cm_benchmark_runpod_results_controller as controller
from scripts import cm_benchmark_runpod_results_controller_v2 as retry_controller


@pytest.mark.skipif(
    not controller.MANIFEST.exists() or not controller.CORE_PLAN.exists(),
    reason="frozen campaign controls are excluded from the source-only integration",
)
def test_results_payload_injects_exact_runner_and_plan():
    manifest = json.loads(controller.MANIFEST.read_text(encoding="utf-8"))
    remote = controller.render_remote()
    assert "__CM_CORE_SCREEN_CODE_B64__" not in remote
    assert "__CM_CORE_SCREEN_PLAN_B64__" not in remote
    assert base64.b64encode(controller.CORE_SCREEN.read_bytes()).decode() in remote
    assert base64.b64encode(controller.CORE_PLAN.read_bytes()).decode() in remote

    payload = controller.create_payload("test-results-pod", manifest, "token", 1_000.0)
    assert payload["computeType"] == "CPU"
    assert payload["cloudType"] == "SECURE"
    assert payload["cpuFlavorIds"] == ["cpu3g"]
    assert payload["vcpuCount"] == 16
    assert payload["volumeInGb"] == 0
    assert payload["env"]["CM_CORE_SCREEN_SHA256"] == controller.digest(controller.CORE_SCREEN)
    assert payload["env"]["CM_CORE_SCREEN_PLAN_SHA256"] == controller.digest(controller.CORE_PLAN)
    assert len(payload["dockerStartCmd"][0]) < 128_000


def test_results_controller_has_one_fixed_output_and_no_automatic_replacement():
    source = controller.Path(controller.__file__).read_text(encoding="utf-8")
    assert controller.EXPECTED_OUT.name == "runpod-results-001"
    assert "maximum_additional_pods\") != 1" in source
    assert "further_replacement\") is not False" in source
    assert source.count("client.post(V1 + \"/pods\"") == 1


@pytest.mark.skipif(
    not retry_controller.MANIFEST.exists(),
    reason="frozen retry manifest is excluded from the source-only integration",
)
def test_retry_payload_moves_large_controls_out_of_create_request():
    manifest = json.loads(retry_controller.MANIFEST.read_text(encoding="utf-8"))
    payload = retry_controller.create_payload("test-results-retry", manifest, "token", 1_000.0)
    controls = json.loads(payload["env"]["CM_CONTROLS_JSON"])
    assert {row["id"] for row in controls} == {"runner", "plan"}
    assert {row["sha256"] for row in controls} == {
        retry_controller.digest(retry_controller.CORE_SCREEN),
        retry_controller.digest(retry_controller.CORE_PLAN),
    }
    assert len(json.dumps(payload).encode()) < 20_000
    assert len(payload["dockerStartCmd"][0]) < 16_000
