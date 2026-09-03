import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import json
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from mint_dynamic_theme.config import ManualWallpaper, DynamicConfig

class TestManualWallpaper(unittest.TestCase):
    def setUp(self):
        # Patch open to avoid reading actual files
        self.wall_file_path = "/tmp/test_wallpaper.json"
        
        # We need to patch os.path.exists and open within the module where they are used
        # or mock the file attribute of the instance.
        
        # Better approach: subclass or instance with overridden file path
        # But ManualWallpaper inits with a constant. We can patch the constant or 
        # modify the instance after init, but init calls load().
        
        # Let's patch CONFIG_PATHS in config module before importing? 
        # Too late if already imported.
        
        # We will reset the file path on the instance and clear history
        # But we need to mock file operations to avoid side effects.
        pass

    @patch("mint_dynamic_theme.config.os.path.exists")
    @patch("mint_dynamic_theme.config.open", new_callable=mock_open, read_data='{"walls": []}')
    @patch("mint_dynamic_theme.config.os.makedirs")
    def test_init_load(self, mock_mkdirs, mock_file, mock_exists):
        mock_exists.return_value = True
        mw = ManualWallpaper()
        self.assertEqual(mw.history, [])

    @patch("mint_dynamic_theme.config.os.path.exists")
    @patch("mint_dynamic_theme.config.open", new_callable=mock_open)
    @patch("mint_dynamic_theme.config.os.replace")
    @patch("mint_dynamic_theme.config.os.path.getmtime")
    def test_add_wall(self, mock_mtime, mock_replace, mock_file, mock_exists):
        # Setup: File doesn't exist initially, so it starts empty.
        mock_exists.return_value = False
        mock_mtime.return_value = 100.0
        
        mw = ManualWallpaper()
        # After init, it saved and set mtime to 100.0
        
        # Now simulate file exists for subsequent calls so it checks mtime
        mock_exists.return_value = True
        
        # add_wall calls load(). load() checks mtime. 100 <= 100 -> return. 
        # So it uses in-memory history.
        mw.add_wall("/path/to/wall.jpg", "Red")
        
        self.assertEqual(len(mw.history), 1)
        self.assertEqual(mw.history[0]["wallpaper"], "/path/to/wall.jpg")
        self.assertEqual(mw.history[0]["color"], "Red")
        
        # Test update (duplicate wallpaper)
        mw.add_wall("/path/to/wall.jpg", "Blue")
        self.assertEqual(len(mw.history), 1)
        self.assertEqual(mw.history[0]["color"], "Blue")
        
        # Test new entry
        mw.add_wall("/path/another.jpg", "Green")
        self.assertEqual(len(mw.history), 2)
        
        # Verify get_current return last added
        current = mw.get_current()
        self.assertEqual(current["wallpaper"], "/path/another.jpg")
        self.assertEqual(current["color"], "Green")

    @patch("mint_dynamic_theme.config.os.path.exists")
    @patch("mint_dynamic_theme.config.open", new_callable=mock_open)
    @patch("mint_dynamic_theme.config.os.replace")
    @patch("mint_dynamic_theme.config.os.path.getmtime")
    def test_clear_history(self, mock_mtime, mock_replace, mock_file, mock_exists):
        mock_exists.return_value = False
        mock_mtime.return_value = 100.0
        
        mw = ManualWallpaper()
        mock_exists.return_value = True
        
        mw.add_wall("a", "Red")
        mw.add_wall("b", "Blue")
        
        self.assertEqual(len(mw.history), 2)
        
        mw.clear_history()
        self.assertEqual(len(mw.history), 0)

class TestDynamicConfig(unittest.TestCase):
    @patch("mint_dynamic_theme.config.os.path.exists")
    @patch("mint_dynamic_theme.config.open", new_callable=mock_open, read_data='{"notifications": false}')
    @patch("mint_dynamic_theme.config.os.path.getmtime")
    def test_load_config(self, mock_mtime, mock_file, mock_exists):
        mock_exists.return_value = True
        mock_mtime.return_value = 100
        
        dc = DynamicConfig()
        # Init calls load
        
        self.assertFalse(dc.get_notifications())

    @patch("mint_dynamic_theme.config.os.path.exists")
    @patch("mint_dynamic_theme.config.open", new_callable=mock_open)
    @patch("mint_dynamic_theme.config.os.replace")
    @patch("mint_dynamic_theme.config.os.path.getmtime")
    def test_set_notifications(self, mock_mtime, mock_replace, mock_file, mock_exists):
        mock_exists.return_value = False
        mock_mtime.return_value = 1
        
        dc = DynamicConfig()
        # Default is True
        self.assertTrue(dc.get_notifications())
        
        dc.set_notifications(False)
        self.assertFalse(dc.get_notifications())
        
        # Verify persistence interaction
        self.assertTrue(mock_replace.called)

if __name__ == '__main__':
    unittest.main()
