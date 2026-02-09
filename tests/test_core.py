import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mint_dynamic_theme.color import ColorService
from mint_dynamic_theme.theme import ThemeService
from mint_dynamic_theme.desktop.cinnamon import CinnamonDesktop
from mint_dynamic_theme.desktop.xfce import XfceDesktop

class TestColorService(unittest.TestCase):
    def test_rgb_to_hsl(self):
        # Red
        h, s, l = ColorService.rgb_to_hsl(255, 0, 0)
        self.assertAlmostEqual(h, 0, places=1)
        self.assertAlmostEqual(s, 1.0, places=1)
        self.assertAlmostEqual(l, 0.5, places=1)
        
        # White
        h, s, l = ColorService.rgb_to_hsl(255, 255, 255)
        self.assertAlmostEqual(l, 1.0, places=1)

    def test_get_theme_for_color(self):
        # Test specific known mappings
        self.assertEqual(ColorService.get_theme_name_for_color(255, 0, 0), "Red")
        self.assertEqual(ColorService.get_theme_name_for_color(0, 0, 255), "Blue")
        self.assertEqual(ColorService.get_theme_name_for_color(0, 255, 0), "Green")
        self.assertEqual(ColorService.get_theme_name_for_color(50, 50, 50), "Grey") # Dark

class TestThemeService(unittest.TestCase):
    def test_get_themes(self):
        themes = ThemeService.get_themes_for_color("Red")
        self.assertEqual(themes["gtk"], "Mint-Y-Dark-Red")
        
        # Test fallback
        themes = ThemeService.get_themes_for_color("NonExistent")
        self.assertEqual(themes["gtk"], "Mint-Y-Dark")

class TestDesktopEnvironments(unittest.TestCase):
    @patch("subprocess.run")
    def test_cinnamon_apply(self, mock_run):
        desktop = CinnamonDesktop()
        desktop.apply_theme("gtk", "Mint-Y-Dark-Red")
        
        mock_run.assert_called_with(
            ["gsettings", "set", "org.cinnamon.desktop.interface", "gtk-theme", "Mint-Y-Dark-Red"],
            check=True, capture_output=True
        )

    @patch("subprocess.run")
    def test_xfce_apply(self, mock_run):
        desktop = XfceDesktop()
        desktop.apply_theme("gtk", "Mint-Y-Dark-Red")
        
        mock_run.assert_called_with(
           ["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-s", "Mint-Y-Dark-Red"],
           check=True, capture_output=True
        )

if __name__ == '__main__':
    unittest.main()
