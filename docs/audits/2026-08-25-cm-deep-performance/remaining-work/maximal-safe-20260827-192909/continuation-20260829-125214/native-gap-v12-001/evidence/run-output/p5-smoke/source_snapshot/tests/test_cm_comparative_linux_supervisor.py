from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cmbench.comparative import linux_supervisor as supervisor


class ComparativeLinuxSupervisorTests(unittest.TestCase):
    def test_limits_and_command_refuse_before_launch(self):
        for key, value in (
            ("timeout_seconds", True),
            ("timeout_seconds", 61),
            ("sample_seconds", 0),
            ("rss_stop_bytes", 1),
            ("processes", 65),
            ("stdout_bytes", 0),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                replace(supervisor.Limits(), **{key: value}).validate()
        with patch.object(supervisor.subprocess, "Popen") as launch:
            for command in ([], "python", ["python", "-c", "pass"], [str(Path.cwd().anchor), None]):
                with self.subTest(command=command), self.assertRaises(ValueError):
                    supervisor.run(command)
        launch.assert_not_called()

    def test_proc_parsers_handle_spaces_and_strict_memory_units(self):
        pid, pgid, state = supervisor.parse_proc_stat("123 (worker name) R 1 123 123 0 0")
        self.assertEqual((pid, pgid, state), (123, 123, "R"))
        self.assertEqual(
            supervisor.parse_proc_status("Name:\tworker\nVmRSS:\t12 kB\nVmHWM:\t20 kB\n"),
            {"rss_bytes": 12 * 1024, "hwm_bytes": 20 * 1024},
        )
        for value in ("", "1 worker R 0 1", "x (w) R 1 2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                supervisor.parse_proc_stat(value)
        with self.assertRaises(ValueError):
            supervisor.parse_proc_status("VmRSS: 1 kB\nVmRSS: 2 kB\n")

    def test_group_snapshot_aggregates_only_live_owned_group(self):
        with tempfile.TemporaryDirectory(prefix="cm-proc-") as directory:
            root = Path(directory)

            def process(pid, pgid, rss, hwm, state="S"):
                path = root / str(pid)
                path.mkdir()
                (path / "stat").write_text(f"{pid} (worker {pid}) {state} 1 {pgid} {pgid} 0 0\n", encoding="ascii")
                (path / "status").write_text(f"VmRSS:\t{rss} kB\nVmHWM:\t{hwm} kB\n", encoding="ascii")

            process(100, 100, 10, 12)
            process(101, 100, 20, 24)
            process(102, 102, 999, 999)
            process(103, 100, 999, 999, state="Z")
            raced = root / "104"
            raced.mkdir()
            result = supervisor.group_snapshot(root, 100)
            self.assertEqual(result["pids"], [100, 101])
            self.assertEqual(result["rss_bytes"], 30 * 1024)
            self.assertEqual(result["per_process_hwm_bytes"], {100: 12 * 1024, 101: 24 * 1024})
            self.assertEqual(result["unreadable_group_entries"], 0)
            self.assertEqual(result["proc_scan_races"], 1)

    def test_group_snapshot_skips_all_terminal_kernel_states(self):
        with tempfile.TemporaryDirectory(prefix="cm-proc-") as directory:
            root = Path(directory)
            for pid, state in ((100, "Z"), (101, "X"), (102, "x")):
                path = root / str(pid)
                path.mkdir()
                (path / "stat").write_text(
                    f"{pid} (finished {pid}) {state} 1 100 100 0 0\n", encoding="ascii"
                )
            result = supervisor.group_snapshot(root, 100)
        self.assertEqual(result["pids"], [])
        self.assertEqual(result["rss_bytes"], 0)
        self.assertEqual(result["unreadable_group_entries"], 0)

    def test_group_snapshot_only_downgrades_proven_terminal_transition_to_race(self):
        with tempfile.TemporaryDirectory(prefix="cm-proc-") as directory:
            root = Path(directory)
            process = root / "100"
            process.mkdir()
            stat = process / "stat"
            stat.write_text("100 (fast worker) R 1 100 100 0 0\n", encoding="ascii")
            (process / "status").write_text("Name:\tfast worker\n", encoding="ascii")
            original = Path.read_text
            stat_reads = 0

            def transitioning_read(path, *args, **kwargs):
                nonlocal stat_reads
                if path == stat:
                    stat_reads += 1
                    if stat_reads == 2:
                        return "100 (fast worker) X 1 100 100 0 0\n"
                return original(path, *args, **kwargs)

            with patch.object(Path, "read_text", new=transitioning_read):
                result = supervisor.group_snapshot(root, 100)
        self.assertEqual(result["pids"], [])
        self.assertEqual(result["unreadable_group_entries"], 0)
        self.assertEqual(result["proc_scan_races"], 1)

    def test_group_snapshot_keeps_live_missing_rss_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="cm-proc-") as directory:
            root = Path(directory)
            process = root / "100"
            process.mkdir()
            (process / "stat").write_text("100 (live worker) S 1 100 100 0 0\n", encoding="ascii")
            (process / "status").write_text("Name:\tlive worker\n", encoding="ascii")
            result = supervisor.group_snapshot(root, 100)
        self.assertEqual(result["pids"], [100])
        self.assertEqual(result["unreadable_group_entries"], 1)

    def test_group_snapshot_recovers_when_live_rss_appears_on_bounded_retry(self):
        with tempfile.TemporaryDirectory(prefix="cm-proc-") as directory:
            root = Path(directory)
            process = root / "100"
            process.mkdir()
            (process / "stat").write_text("100 (starting worker) R 1 100 100 0 0\n", encoding="ascii")
            status = process / "status"
            status.write_text("Name:\tstarting worker\n", encoding="ascii")
            original = Path.read_text
            status_reads = 0

            def delayed_rss(path, *args, **kwargs):
                nonlocal status_reads
                if path == status:
                    status_reads += 1
                    if status_reads >= 2:
                        return "Name:\tstarting worker\nVmRSS:\t12 kB\nVmHWM:\t20 kB\n"
                return original(path, *args, **kwargs)

            with patch.object(Path, "read_text", new=delayed_rss):
                result = supervisor.group_snapshot(root, 100)
        self.assertEqual(result["pids"], [100])
        self.assertEqual(result["rss_bytes"], 12 * 1024)
        self.assertEqual(result["unreadable_group_entries"], 0)

    def test_unsupported_platform_refuses_without_launch(self):
        command = [str(Path(__file__).resolve()), "unused"]
        with patch.object(supervisor, "platform_supported", return_value=False), \
                patch.object(supervisor.subprocess, "Popen") as launch:
            result = supervisor.run(command)
        self.assertEqual(result.status, "refused")
        self.assertFalse(result.resources["launched"])
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
