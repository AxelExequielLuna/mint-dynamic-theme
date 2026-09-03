import subprocess
import logging
import os
import time
from typing import Optional
from pathlib import Path
from .base import DesktopEnvironment
from ..config import CONFIG_PATHS

log = logging.getLogger("mint-dynamic-theme")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class XfceDesktop(DesktopEnvironment):
    def __init__(self):
        self.wallpaper_dir = CONFIG_PATHS.get("xfce_wallpaper_dir")
        self.observer = None
        self.running = False
        self.keys = {"gtk": "/Net/ThemeName", "icon": "/Net/IconThemeName"}

    def get_wallpaper(self) -> Optional[str]:
        try:
            dir_path = Path(self.wallpaper_dir)
            if not dir_path.exists():
                return None
            
            files = list(dir_path.rglob("*"))
            files = [f for f in files if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
            
            if not files:
                return None
                
            most_recent = max(files, key=lambda p: p.stat().st_mtime)
            return str(most_recent)
        except Exception as e:
            log.error(f"Error getting XFCE wallpaper: {e}")
            return None

    def apply_theme(self, theme_type: str, theme_name: str) -> bool:
        if theme_type not in self.keys:
            return False # XFCE might not support 'desktop' theme same way, mostly GTK/Icon
        try:
            subprocess.run(
                ["xfconf-query", "-c", "xsettings", "-p", self.keys[theme_type], "-s", theme_name],
                check=True, capture_output=True
            )
            return True
        except Exception as e:
            log.error(f"Error applying XFCE theme {theme_type}: {e}")
            return False

    def monitor_changes(self, callback) -> None:
        if not WATCHDOG_AVAILABLE:
            log.error("Watchdog missing for XFCE, falling back to polling")
            self._fallback_monitor(callback)
            return

        self.running = True
        
        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if not event.is_directory:
                    callback()

        self.observer = Observer()
        self.observer.schedule(Handler(), self.wallpaper_dir, recursive=False)
        self.observer.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            if self.observer:
                self.observer.stop()
                self.observer.join()

    def _fallback_monitor(self, callback):
        self.running = True
        while self.running:
            time.sleep(5)
            # Potentially check mtime manually here or just trigger simple polling
            # But the caller (Daemon) manages the logic, monitor just needs to notify
            # Since we don't know the last mtime here easily without state,
            # we simply call callback periodically? No, callback calls _process which checks file.
            callback()

    def stop_monitoring(self) -> None:
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
