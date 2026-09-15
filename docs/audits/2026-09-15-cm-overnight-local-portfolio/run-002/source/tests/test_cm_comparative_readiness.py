from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cmbench.comparative.readiness import (
    READINESS_SCHEMA,
    cgroup_v2_relative,
    environment_record,
    parse_cpu_list,
    parse_cpu_max,
    parse_key_values,
    parse_limit,
    read_cgroup_v2,
    validate_allocation,
)


class ComparativeReadinessTests(unittest.TestCase):
    def test_strict_cgroup_parsers(self):
        self.assertEqual(parse_cpu_list("0-2,5,8-9\n"), (0, 1, 2, 5, 8, 9))
        self.assertEqual(parse_cpu_max("200000 100000"), {"quota_us": 200000, "period_us": 100000})
        self.assertEqual(parse_cpu_max("max 100000"), {"quota_us": None, "period_us": 100000})
        self.assertIsNone(parse_limit("max\n"))
        self.assertEqual(parse_limit("0"), 0)
        self.assertEqual(parse_key_values("populated 1\nfrozen 0\n"), {"populated": 1, "frozen": 0})
        self.assertEqual(cgroup_v2_relative("0::/tenant/pod\n"), "tenant/pod")
        for value in ("1,0", "2-1", "0,,1", "a", "1-1000002"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_cpu_list(value)
        for value in ("", "1", "zero 100", "1 0", "-1 100", "1 2 3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_cpu_max(value)
        with self.assertRaises(ValueError):
            parse_key_values("populated 1\npopulated 0\n")
        with self.assertRaises(ValueError):
            cgroup_v2_relative("1:name=/legacy\n")

    def test_read_cgroup_retains_observed_missing_and_malformed_fields(self):
        with tempfile.TemporaryDirectory(prefix="cm-ready-") as directory:
            root = Path(directory)
            proc = root / "proc"
            cgroup = root / "cgroup"
            base = cgroup / "tenant" / "pod"
            (proc / "self").mkdir(parents=True)
            base.mkdir(parents=True)
            (proc / "self" / "cgroup").write_text("0::/tenant/pod\n", encoding="ascii")
            values = {
                "cpu.max": "200000 100000\n",
                "cpuset.cpus.effective": "40,104\n",
                "memory.max": "4294967296\n",
                "memory.current": "1234\n",
                "pids.max": "32\n",
                "pids.current": "1\n",
                "cgroup.events": "populated 1\nfrozen 0\n",
                "cpu.stat": "usage_usec 10\n",
            }
            for name, value in values.items():
                (base / name).write_text(value, encoding="ascii")
            (base / "memory.peak").write_text("bad\n", encoding="ascii")
            result = read_cgroup_v2(proc_root=proc, cgroup_root=cgroup)
            self.assertEqual(result["version"], 2)
            self.assertEqual(result["fields"]["cpu.max"]["value"]["quota_us"], 200000)
            self.assertEqual(result["fields"]["cpuset.cpus.effective"]["value"], [40, 104])
            self.assertEqual(result["fields"]["memory.peak"]["status"], "malformed")

            (base / "memory.peak").unlink()
            result = read_cgroup_v2(proc_root=proc, cgroup_root=cgroup)
            self.assertEqual(result["fields"]["memory.peak"], {"status": "unavailable", "value": None})

    def test_environment_uses_affinity_for_allocation_not_host_count(self):
        with patch("cmbench.comparative.readiness.sys.platform", "linux"), \
                patch("cmbench.comparative.readiness.os.sched_getaffinity", return_value={40, 104}, create=True), \
                patch("cmbench.comparative.readiness.os.cpu_count", return_value=128), \
                patch("cmbench.comparative.readiness.read_cgroup_v2", return_value={"version": 2, "fields": {}}), \
                patch("cmbench.comparative.readiness.extension_identity", return_value={"status": "fixture"}):
            record = environment_record()
        self.assertEqual(record["schema"], READINESS_SCHEMA)
        self.assertEqual(record["cpu"]["host_logical_visible"], 128)
        self.assertEqual(record["cpu"]["affinity"], [40, 104])
        self.assertEqual(record["cpu"]["allocated_logical_from_affinity"], 2)
        validate_allocation(record, expected_affinity_cpus=2)
        with self.assertRaises(ValueError):
            validate_allocation(record, expected_affinity_cpus=128)
        self.assertFalse(record["native_execution_performed"])
        self.assertFalse(record["performance_ranking_permitted"])


if __name__ == "__main__":
    unittest.main()
