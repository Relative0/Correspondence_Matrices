"""Independent zero-volume and cost-accounting checks with fake inputs only."""
import copy
import hashlib
import json
import math
from types import SimpleNamespace
import unittest
from unittest import mock

from test_cm_runpod_http_transport_independent import load_module


controller = load_module("independent_ephemeral_controller", "runpod_http_smoke_controller_v3.py")
preflight = controller.preflight
FAKE_POD = "offline123456"


class EphemeralIndependentTests(unittest.TestCase):
    def setUp(self):
        self.patch(preflight, "session", side_effect=AssertionError("no credentials or network"))
        self.patch(controller.requests, "Session", side_effect=AssertionError("no network"))
        self.patch(controller.base, "read_key", side_effect=AssertionError("no credentials"))
        self.patch(controller, "load", return_value={"pod_id": FAKE_POD})

    def patch(self, target, name, *args, **kwargs):
        patcher = mock.patch.object(target, name, *args, **kwargs)
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def pod(self):
        return {
            "id": FAKE_POD, "name": "owned", "cpuFlavorId": "cpu3c",
            "vcpuCount": 2, "memoryInGb": 4, "costPerHr": 0.06,
            "image": controller.base.IMAGE, "containerDiskInGb": 12,
            "volumeInGb": 0, "volumeMountPath": "/workspace",
            "ports": ["8080/http", "8081/http"], "networkVolume": None,
            "gpu": None, "machine": {"secureCloud": True},
        }

    def validate(self, pod=None, prior=0.01):
        return controller.validate_pod(
            self.pod() if pod is None else pod, {"name": "owned"}, {"id": "cpu3c"}, prior,
        )

    def metadata(self, amount=0, count=0, unique=0):
        return {"recordCount": count, "uniquePodCount": unique,
                "totals": {"cpuAmount": amount, "gpuAmount": 0,
                           "diskAmount": 0, "totalAmount": amount}}

    def rows(self, amount, pod_id=None):
        return [{"podId": preflight.PRIOR_POD_ID if pod_id is None else pod_id,
                 "amount": amount, "time": "2026-08-28T00:00:00Z"}]

    def test_request_and_returned_resource_agree_on_ephemeral_storage(self):
        payload = controller.create_payload("owned", {"id": "cpu3c"},
                                            "OFFLINE_ONLY_TOKEN", b"offline payload", 1000)
        self.assertEqual(payload["volumeInGb"], 0)
        self.assertEqual(payload["containerDiskInGb"], 12)
        self.assertNotIn("networkVolumeId", payload)
        self.assertEqual(payload["ports"], ["8080/http", "8081/http"])
        result = self.validate()
        self.assertEqual(result["pod_volume_gb"], 0)
        self.assertAlmostEqual(result["projected_aggregate_http_cost_usd"], 0.01 + 0.07 / 3)

    def test_only_an_explicit_integer_zero_volume_is_accepted(self):
        for value in (None, False, True, 0.0, -1, 1, 10, "0", float("nan")):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                self.validate({**self.pod(), "volumeInGb": value})
        pod = self.pod()
        pod.pop("volumeInGb")
        with self.assertRaises(RuntimeError):
            self.validate(pod)

    def test_container_and_network_volume_checks_remain_required(self):
        for changes in ({"containerDiskInGb": 10}, {"containerDiskInGb": None},
                        {"networkVolume": {"id": "not-approved"}},
                        {"volumeMountPath": "/different"}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                self.validate({**self.pod(), **changes})

    def test_actual_resource_gate_cannot_omit_prior_reserve(self):
        for prior in (0, 0.009999, -1, float("nan"), float("inf")):
            with self.subTest(prior=prior), self.assertRaises(RuntimeError):
                self.validate(prior=prior)

    def test_actual_and_quoted_price_gates_share_aggregate_cap(self):
        for rate, prior, accepted in (
            (0.06, 0.01, True), (0.25, 0.01, True),
            (0.06, 0.076, True), (0.06, 0.077, False),
            (0.250001, 0.01, False), (0.11, 0.065, False), (0, 0.01, False),
        ):
            with self.subTest(rate=rate, prior=prior):
                self.assertEqual(preflight.budget(rate, prior)["ready"], accepted)
                pod = {**self.pod(), "costPerHr": rate}
                if accepted:
                    self.assertLessEqual(self.validate(pod, prior)["projected_aggregate_http_cost_usd"], 0.10)
                else:
                    with self.assertRaises(RuntimeError):
                        self.validate(pod, prior)

    def test_delayed_billing_uses_reserve_or_higher_attributed_amount(self):
        empty = preflight.analyze_billing(self.metadata(), [])
        self.assertEqual(empty["prior_cost_bound_usd"], 0.01)
        self.assertTrue(empty["billing_may_lag"])
        for amount in (0.000101, 0.01, 0.025):
            result = preflight.analyze_billing(self.metadata(amount, 1, 1), self.rows(amount))
            self.assertEqual(result["prior_cost_bound_usd"], max(0.01, amount))

    def test_unattributed_and_missing_pod_ids_are_refused(self):
        for rows in (self.rows(0.02, "unrelated-pod"), [{"amount": 0.02}],
                     [{"podId": None, "amount": 0.02}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                preflight.analyze_billing(self.metadata(0.02, 1, 1), rows)

    def test_billing_counts_are_strict_and_complete(self):
        for count, unique, rows in (
            (True, 1, self.rows(0)), (1, True, self.rows(0)),
            (1.0, 1, self.rows(0)), (0, 0, self.rows(0)),
            (1, 0, self.rows(0)), (2, 1, self.rows(0)),
            (1, 2, self.rows(0)), (-1, 0, []), (10001, 0, []), (0, 0, {}),
        ):
            with self.subTest(count=count, unique=unique), self.assertRaises(ValueError):
                preflight.analyze_billing(self.metadata(0, count, unique), rows)

    def test_non_numeric_negative_and_nonfinite_costs_are_refused(self):
        for value in (True, False, "0.01", None, -0.01, math.nan, math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                preflight.analyze_billing(self.metadata(value, 1, 1), self.rows(value))
            with self.subTest(budget=value), self.assertRaises(ValueError):
                preflight.budget(value, 0.01)

    def test_detail_and_component_totals_must_reconcile(self):
        metadata = self.metadata(0.02, 1, 1)
        metadata["totals"]["diskAmount"] = 0.001
        with self.assertRaises(ValueError):
            preflight.analyze_billing(metadata, self.rows(0.02))
        with self.assertRaises(ValueError):
            preflight.analyze_billing(self.metadata(0.02, 1, 1), self.rows(0.01))
        with self.assertRaises(ValueError):
            preflight.analyze_billing(self.metadata(0.02, 0, 0), [])
        rows = self.rows(0.01) + self.rows(0.02)
        result = preflight.analyze_billing(self.metadata(0.03, 2, 1), rows)
        self.assertEqual(result["prior_cost_bound_usd"], 0.03)

    def test_billing_lookup_is_grouped_readonly_and_does_not_follow_redirects(self):
        for amount in (0, 0.02):
            responses = [SimpleNamespace(
                json=lambda: {"metadata": self.metadata(amount, int(amount > 0), int(amount > 0))},
                raise_for_status=lambda: None,
            )]
            if amount:
                responses.append(SimpleNamespace(json=lambda: self.rows(amount), raise_for_status=lambda: None))
            client = mock.Mock(spec_set=["get"])
            client.get.side_effect = responses
            checked = preflight.billing_check(client)
            self.assertEqual(checked["observed_previous_cost_usd"], amount)
            self.assertEqual(client.get.call_count, 2 if amount else 1)
            for call in client.get.call_args_list:
                self.assertFalse(call.kwargs["allow_redirects"])
                self.assertEqual(call.kwargs["params"]["grouping"], "podId")
                self.assertEqual(call.kwargs["params"]["startTime"], "2026-08-27T00:00:00Z")

    def test_prior_allocation_must_be_reconciled_and_executed_sources_unchanged(self):
        source = b"offline source fixture"
        digest = hashlib.sha256(source).hexdigest()
        fixtures = {
            "RUN.json": {"pod_id": preflight.PRIOR_POD_ID, "creation_http_status": 201,
                         "creation_uncertain": False, "cleanup": {"owned_pod_absent": True}},
            "HTTP-FINAL-VERIFICATION-20260828-084114-539259.json": {
                "pod_id": preflight.PRIOR_POD_ID, "owned_pod_absent_verified": True,
                "create_requests_this_authorization": 1, "automatic_replacement_queued": False,
                "checks": {version: {"detail_http_status": 404, "inventory": []} for version in ("v1", "v2")},
                "guard_releases": {role: {"released": True, "pid_still_running": False}
                                   for role in ("http-controller", "http-watchdog")},
            },
            "TRANSPORT-FREEZE.json": {field: digest for field in
                                      ("controller_sha256", "bootstrap_sha256", "preflight_sha256")},
        }
        baseline = copy.deepcopy(fixtures)
        self.patch(preflight.Path, "read_text", lambda path, **kwargs: json.dumps(fixtures[path.name]))
        self.patch(preflight.Path, "read_bytes", lambda path: source)
        self.assertTrue(preflight.prior_attempt()["cleanup_verified"])
        for path, keys, value in (
            ("RUN.json", ("pod_id",), "unrelated"),
            ("RUN.json", ("cleanup", "owned_pod_absent"), False),
            ("HTTP-FINAL-VERIFICATION-20260828-084114-539259.json", ("create_requests_this_authorization",), 2),
            ("HTTP-FINAL-VERIFICATION-20260828-084114-539259.json", ("guard_releases", "http-watchdog", "pid_still_running"), True),
            ("HTTP-FINAL-VERIFICATION-20260828-084114-539259.json", ("checks", "v2", "inventory"), [{"id": FAKE_POD}]),
            ("TRANSPORT-FREEZE.json", ("controller_sha256",), "changed"),
        ):
            fixtures = copy.deepcopy(baseline)
            target = fixtures[path]
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value
            with self.subTest(path=path, keys=keys), self.assertRaises(RuntimeError):
                preflight.prior_attempt()


if __name__ == "__main__":
    unittest.main()
