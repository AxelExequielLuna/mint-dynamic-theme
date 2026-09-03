import os
import sys
import unittest
from unittest.mock import mock_open, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from mint_dynamic_theme.utils import (
    get_daemon_status,
    is_mdt_process,
    is_pid_running,
    pid_file_manager,
)


class TestIsPidRunning(unittest.TestCase):
    @patch("mint_dynamic_theme.utils.os.kill")
    def test_running(self, mock_kill):
        self.assertTrue(is_pid_running(1234))

    @patch("mint_dynamic_theme.utils.os.kill", side_effect=ProcessLookupError)
    def test_not_running(self, mock_kill):
        self.assertFalse(is_pid_running(9999))

    @patch("mint_dynamic_theme.utils.os.kill", side_effect=PermissionError)
    def test_permission_considered_running(self, mock_kill):
        self.assertTrue(is_pid_running(1234))


class TestIsMdtProcess(unittest.TestCase):
    def test_current_process_is_mdt(self):
        # unittest runs under `python3 -m unittest ...`; its cmdline may or may
        # not reference mint_dynamic_theme, so only assert a boolean result.
        self.assertIn(is_mdt_process(os.getpid()), (True, False))

    @patch(
        "builtins.open",
        mock_open(
            read_data=b"/home/user/.local/bin/mdt\x00start\x00"
        ),
    )
    def test_mdt_console_script(self):
        self.assertTrue(is_mdt_process(1234))

    @patch(
        "builtins.open",
        mock_open(
            read_data=b"/usr/bin/python3\x00/home/axel/.local/bin/mdt\x00start\x00"
        ),
    )
    def test_mdt_running_via_shebang(self):
        self.assertTrue(is_mdt_process(1234))

    @patch(
        "builtins.open",
        mock_open(
            read_data=b"/usr/bin/python3\x00-m\x00mint_dynamic_theme.cli\x00start\x00"
        ),
    )
    def test_mdt_python_module(self):
        self.assertTrue(is_mdt_process(1234))

    @patch(
        "builtins.open",
        mock_open(
            read_data=b"/home/user/.local/bin/mdt\x00tray\x00"
        ),
    )
    def test_mdt_tray_is_not_daemon(self):
        self.assertFalse(is_mdt_process(1234))

    @patch(
        "builtins.open",
        mock_open(read_data=b"/usr/bin/mpris-proxy\x00"),
    )
    def test_recycled_foreign_pid(self):
        self.assertFalse(is_mdt_process(1234))

    @patch(
        "builtins.open",
        mock_open(read_data=b"/usr/bin/python3\x00-m\x00unittest\x00"),
    )
    def test_other_process(self):
        self.assertFalse(is_mdt_process(1234))

    def test_nonexistent_pid(self):
        self.assertFalse(is_mdt_process(1999999999))


class TestPidFileManager(unittest.TestCase):
    def test_creates_and_removes(self):
        pid_path = "/tmp/test_daemon.pid"
        if os.path.exists(pid_path):
            os.remove(pid_path)

        with pid_file_manager(pid_path) as path:
            self.assertEqual(path, pid_path)
            with open(pid_path) as f:
                self.assertEqual(f.read().strip(), str(os.getpid()))

        self.assertFalse(os.path.exists(pid_path))

    def test_removes_stale_pid(self):
        pid_path = "/tmp/test_daemon_stale.pid"
        with open(pid_path, "w") as f:
            f.write("99999")

        with pid_file_manager(pid_path):
            pass

        self.assertFalse(os.path.exists(pid_path))


class TestGetDaemonStatus(unittest.TestCase):
    def test_no_pid_file(self):
        with patch(
            "mint_dynamic_theme.utils.CONFIG_PATHS",
            {"pid_file": "/tmp/does_not_exist.pid"},
        ):
            self.assertEqual(get_daemon_status(), {"status": "stopped"})

    @patch("mint_dynamic_theme.utils.is_pid_running", return_value=True)
    @patch("mint_dynamic_theme.utils.is_mdt_process", return_value=True)
    def test_running(self, mock_mdt, mock_is_running):
        pid_path = "/tmp/existing.pid"
        with open(pid_path, "w") as f:
            f.write("12345")
        try:
            with patch(
                "mint_dynamic_theme.utils.CONFIG_PATHS", {"pid_file": pid_path}
            ):
                self.assertEqual(
                    get_daemon_status(), {"status": "running", "pid": 12345}
                )
        finally:
            os.remove(pid_path)

    @patch("mint_dynamic_theme.utils.is_pid_running", return_value=True)
    @patch("mint_dynamic_theme.utils.is_mdt_process", return_value=False)
    def test_recycled_pid_treated_as_dead(self, mock_mdt, mock_is_running):
        pid_path = "/tmp/existing.pid"
        with open(pid_path, "w") as f:
            f.write("12345")
        try:
            with patch(
                "mint_dynamic_theme.utils.CONFIG_PATHS", {"pid_file": pid_path}
            ):
                self.assertEqual(
                    get_daemon_status(),
                    {"status": "dead", "pid": 12345, "stale": True},
                )
        finally:
            os.remove(pid_path)

    @patch("mint_dynamic_theme.utils.is_pid_running", return_value=False)
    def test_dead(self, mock_is_running):
        pid_path = "/tmp/existing.pid"
        with open(pid_path, "w") as f:
            f.write("12345")
        try:
            with patch(
                "mint_dynamic_theme.utils.CONFIG_PATHS", {"pid_file": pid_path}
            ):
                self.assertEqual(
                    get_daemon_status(), {"status": "dead", "pid": 12345}
                )
        finally:
            os.remove(pid_path)


if __name__ == "__main__":
    unittest.main()