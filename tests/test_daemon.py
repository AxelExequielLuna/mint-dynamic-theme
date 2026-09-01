import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mint_dynamic_theme.config import CONFIG_MANAGER
from mint_dynamic_theme.daemon import Daemon


class TestDaemonDetectDesktop(unittest.TestCase):
    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "X-Cinnamon"})
    def test_detect_cinnamon(self):
        from mint_dynamic_theme.desktop.cinnamon import CinnamonDesktop

        self.assertIsInstance(Daemon().desktop_env, CinnamonDesktop)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "MATE"})
    def test_detect_mate(self):
        from mint_dynamic_theme.desktop.mate import MateDesktop

        self.assertIsInstance(Daemon().desktop_env, MateDesktop)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "XFCE"})
    def test_detect_xfce(self):
        from mint_dynamic_theme.desktop.xfce import XfceDesktop

        self.assertIsInstance(Daemon().desktop_env, XfceDesktop)

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": ""})
    def test_detect_fallback(self):
        from mint_dynamic_theme.desktop.cinnamon import CinnamonDesktop

        self.assertIsInstance(Daemon().desktop_env, CinnamonDesktop)


class TestDaemonProcess(unittest.TestCase):
    def setUp(self):
        self.daemon = Daemon()
        self.daemon.desktop_env = MagicMock()
        self.themes = {
            "gtk": "Mint-Y-Dark-Red",
            "icon": "Mint-Y-Red",
            "desktop": "Mint-Y-Dark-Red",
        }

    @patch("mint_dynamic_theme.daemon.ColorService.get_dominant_color")
    @patch("mint_dynamic_theme.daemon.ColorService.get_theme_name_for_color")
    @patch("mint_dynamic_theme.daemon.ThemeService.get_themes_for_color")
    @patch.object(CONFIG_MANAGER, "get_paused", return_value=False)
    def test_process_applies_theme(
        self, mock_paused, mock_themes, mock_name, mock_color
    ):
        self.daemon.desktop_env.get_wallpaper.return_value = "/tmp/wall.jpg"
        mock_color.return_value = (200, 40, 40)
        mock_name.return_value = "Red"
        mock_themes.return_value = self.themes

        with patch("mint_dynamic_theme.daemon.MANUAL_WALL") as mock_manual:
            mock_manual.get_history.return_value = []
            mock_manual.get_current.return_value = {"wallpaper": None, "color": None}
            with patch(
                "mint_dynamic_theme.daemon.ThemeService.theme_exists",
                return_value=True,
            ):
                with patch(
                    "mint_dynamic_theme.daemon.ThemeService.notify_change"
                ) as mock_notify:
                    self.daemon._process()

        self.assertEqual(self.daemon.last_theme, "Red")
        self.assertEqual(self.daemon.desktop_env.apply_theme.call_count, 3)
        mock_notify.assert_called_once_with("Red")

    @patch.object(CONFIG_MANAGER, "get_paused", return_value=False)
    def test_process_ignores_same_wallpaper(self, mock_paused):
        self.daemon.desktop_env.get_wallpaper.return_value = "/tmp/wall.jpg"
        self.daemon.last_wallpaper = "/tmp/wall.jpg"

        with patch("mint_dynamic_theme.daemon.MANUAL_WALL"):
            self.daemon._process()

        self.assertFalse(self.daemon.desktop_env.apply_theme.called)

    @patch("mint_dynamic_theme.daemon.ColorService.get_dominant_color")
    @patch("mint_dynamic_theme.daemon.ColorService.get_theme_name_for_color")
    @patch("mint_dynamic_theme.daemon.ThemeService.get_themes_for_color")
    @patch.object(CONFIG_MANAGER, "get_paused", return_value=True)
    def test_process_respects_pause(
        self, mock_paused, mock_themes, mock_name, mock_color
    ):
        self.daemon.desktop_env.get_wallpaper.return_value = "/tmp/wall.jpg"

        with patch("mint_dynamic_theme.daemon.MANUAL_WALL"):
            self.daemon._process()

        self.assertFalse(self.daemon.desktop_env.apply_theme.called)
        self.assertIsNone(self.daemon.last_theme)

    @patch("mint_dynamic_theme.daemon.ColorService.get_dominant_color")
    @patch("mint_dynamic_theme.daemon.ThemeService.get_themes_for_color")
    @patch.object(CONFIG_MANAGER, "get_paused", return_value=False)
    def test_process_manual_override(
        self, mock_paused, mock_themes, mock_color
    ):
        self.daemon.desktop_env.get_wallpaper.return_value = "/tmp/wall.jpg"
        mock_themes.return_value = self.themes

        with patch("mint_dynamic_theme.daemon.MANUAL_WALL") as mock_manual:
            mock_manual.get_history.return_value = [
                {"wallpaper": "/tmp/wall.jpg", "color": "Red"}
            ]
            mock_manual.get_current.return_value = {
                "wallpaper": "/tmp/wall.jpg",
                "color": "Red",
            }
            with patch(
                "mint_dynamic_theme.daemon.ThemeService.theme_exists",
                return_value=True,
            ):
                with patch(
                    "mint_dynamic_theme.daemon.ThemeService.notify_change"
                ) as mock_notify:
                    self.daemon._process()

        mock_color.assert_not_called()
        self.assertEqual(self.daemon.last_theme, "Red")
        mock_notify.assert_called_once_with("Red")

    @patch.object(CONFIG_MANAGER, "get_paused", return_value=False)
    def test_process_no_wallpaper(self, mock_paused):
        self.daemon.desktop_env.get_wallpaper.return_value = None

        with patch("mint_dynamic_theme.daemon.MANUAL_WALL"):
            self.daemon._process()

        self.assertFalse(self.daemon.desktop_env.apply_theme.called)


if __name__ == "__main__":
    unittest.main()