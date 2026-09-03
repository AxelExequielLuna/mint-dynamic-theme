import os
import subprocess
import logging
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urlparse, unquote

log = logging.getLogger("mint-dynamic-theme")

class DesktopEnvironment(ABC):
    @abstractmethod
    def get_wallpaper(self) -> Optional[str]:
        """Returns the current wallpaper path."""
        pass

    @abstractmethod
    def apply_theme(self, theme_type: str, theme_name: str) -> bool:
        """Applies a specific theme setting."""
        pass

    @abstractmethod
    def monitor_changes(self, callback) -> None:
        """Starts monitoring for wallpaper changes. Should block or run a loop."""
        pass
    
    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stops the monitoring process."""
        pass


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
