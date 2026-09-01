import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mint_dynamic_theme.desktop.cinnamon import CinnamonDesktop


class TestGSettingsDesktop(unittest.TestCase):
    def setUp(self):
        self.desktop = CinnamonDesktop()

    def test_get_wallpaper_file_uri(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            path = tmp.name
        try:
            mock_out = MagicMock()
            mock_out.stdout = f"'file://{path}'"

            with patch(
                "mint_dynamic_theme.desktop.base.subprocess.run",
                return_value=mock_out,
            ):
                result = self.desktop.get_wallpaper()

            self.assertEqual(result, path)
        finally:
            os.unlink(path)

    @patch("mint_dynamic_theme.desktop.base.subprocess.run")
    def test_get_wallpaper_invalid_uri(self, mock_run):
        mock_out = MagicMock()
        mock_out.stdout = "'http://example.com/wall.jpg'"
        mock_run.return_value = mock_out

        self.assertIsNone(self.desktop.get_wallpaper())

    @patch("mint_dynamic_theme.desktop.base.subprocess.run")
    def test_apply_theme_invalid_type(self, mock_run):
        self.assertFalse(self.desktop.apply_theme("nope", "Whatever"))
        mock_run.assert_not_called()

    @patch(
        "mint_dynamic_theme.desktop.base.subprocess.run",
        side_effect=OSError("boom"),
    )
    def test_apply_theme_subprocess_error(self, mock_run):
        self.assertFalse(self.desktop.apply_theme("gtk", "Mint-Y-Dark-Red"))

    def test_monitor_runs_callback_per_line(self):
        proc = MagicMock()
        proc.stdout = iter(["file:///x"] * 3)

        cb = MagicMock()
        with patch(
            "mint_dynamic_theme.desktop.base.subprocess.Popen",
            return_value=proc,
        ):
            self.desktop.monitor_changes(cb)

        self.assertEqual(cb.call_count, 3)
        self.assertIsNone(self.desktop.proc)


if __name__ == "__main__":
    unittest.main()