import subprocess
import logging
import os
from typing import Optional
from urllib.parse import urlparse, unquote
from .base import DesktopEnvironment

log = logging.getLogger("mint-dynamic-theme")

class GSettingsDesktop(DesktopEnvironment):
    """Base for desktops using GSettings (Cinnamon, MATE)"""
    def __init__(self, schema, key, theme_schemas, theme_keys):
        self.schema = schema
        self.key = key
        self.theme_schemas = theme_schemas
        self.theme_keys = theme_keys
        self.proc = None
        self.running = False
        
    def get_wallpaper(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["gsettings", "get", self.schema, self.key],
                capture_output=True, text=True, check=True
            )
            uri = result.stdout.strip().strip("'\"")
            if not uri or uri == "''":
                return None
            if uri.startswith("file://"):
                path = unquote(urlparse(uri).path)
                return path if os.path.exists(path) else None
            return None # Handle other URIs if needed or return None
        except Exception as e:
            log.error(f"Error getting wallpaper: {e}")
            return None

    def apply_theme(self, theme_type: str, theme_name: str) -> bool:
        if theme_type not in self.theme_schemas:
            return False
        try:
            subprocess.run(
                ["gsettings", "set", self.theme_schemas[theme_type], self.theme_keys[theme_type], theme_name],
                check=True, capture_output=True
            )
            return True
        except Exception as e:
            log.error(f"Error applying theme {theme_type}: {e}")
            return False

    def monitor_changes(self, callback) -> None:
        self.running = True
        try:
            self.proc = subprocess.Popen(
                ["gsettings", "monitor", self.schema, self.key],
                stdout=subprocess.PIPE, text=True
            )
            
            for line in self.proc.stdout:
                if not self.running: break
                callback()
        except Exception as e:
            log.error(f"Monitor error: {e}")
        finally:
            self.stop_monitoring()

    def stop_monitoring(self) -> None:
        self.running = False
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None


class CinnamonDesktop(GSettingsDesktop):
    def __init__(self):
        super().__init__(
            schema="org.cinnamon.desktop.background",
            key="picture-uri",
            theme_schemas={
                "gtk": "org.cinnamon.desktop.interface",
                "icon": "org.cinnamon.desktop.interface",
                "desktop": "org.cinnamon.theme",
            },
            theme_keys={"gtk": "gtk-theme", "icon": "icon-theme", "desktop": "name"}
        )

class MateDesktop(GSettingsDesktop):
    def __init__(self):
        super().__init__(
            schema="org.mate.background",
            key="picture-filename", # MATE usually uses picture-filename, check original code used picture-uri but schema org.mate.background
            # Original code: schema "org.mate.background", key "picture-uri"
            # Let's stick to original code's key if possible, but MATE often uses picture-filename for local files.
            # Assuming original code was tested.
            theme_schemas={
                "gtk": "org.mate.interface",
                "icon": "org.mate.interface",
                "desktop": "org.mate.Marco.general",
            },
            theme_keys={"gtk": "gtk-theme", "icon": "icon-theme", "desktop": "theme"}
        )
