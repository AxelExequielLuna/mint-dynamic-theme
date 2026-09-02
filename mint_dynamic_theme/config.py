import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Optional

log = logging.getLogger("mint-dynamic-theme")

# ==================== CONSTANTS ====================
HOME = os.path.expanduser("~")
XDG_CONFIG_HOME = os.getenv("XDG_CONFIG_HOME", f"{HOME}/.config")
CONFIG_DIR = f"{XDG_CONFIG_HOME}/mint-dynamic-theme"

CONFIG_FILE = f"{CONFIG_DIR}/config.json"

DEFAULT_COLOR_QUALITY = 20
DEFAULT_CACHE_SIZE = 32
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB

CONFIG_PATHS = {
    "color_quality": int(os.getenv("COLOR_QUALITY", str(DEFAULT_COLOR_QUALITY))),
    "cache_size": int(os.getenv("CACHE_SIZE", str(DEFAULT_CACHE_SIZE))),
    "log_file": f"{CONFIG_DIR}/errors.log",
    "pid_file": f"{CONFIG_DIR}/daemon.pid",
    "wall_file": f"{CONFIG_DIR}/wallpaper.json",
    "xfce_wallpaper_dir": f"{HOME}/.cache/xfce4/desktop",
}

# Ensure config directory exists
os.makedirs(CONFIG_DIR, exist_ok=True)


class DynamicConfig:
    """
    Manages persistent configuration with automatic reload.
    Thread-safe for reads.
    """

    def __init__(self):
        import threading

        self.file = CONFIG_FILE
        self.mtime = 0
        self._lock = threading.RLock()
        self.data = {"notifications": True, "tray_autostart": False, "paused": False}
        self.load()

    def load(self) -> None:
        """Loads configuration from file if it has been modified"""
        with self._lock:
            if not os.path.exists(self.file):
                self.save()
                return

            try:
                mtime = os.path.getmtime(self.file)
                if mtime <= self.mtime:
                    return

                with open(self.file, "r") as f:
                    content = f.read()
                    if not content.strip():
                        self.data = {
                            "notifications": True,
                            "tray_autostart": False,
                            "paused": False,
                        }
                    else:
                        loaded_data = json.loads(content)
                        if not isinstance(loaded_data, dict):
                            log.error("Config file contains invalid data")
                            self.data = {
                                "notifications": True,
                                "tray_autostart": False,
                                "paused": False,
                            }
                        else:
                            self.data = {
                                **{
                                    "notifications": True,
                                    "tray_autostart": False,
                                    "paused": False,
                                },
                                **loaded_data,
                            }

                self.mtime = mtime

            except json.JSONDecodeError as e:
                log.error(f"Error parsing JSON in config: {e}")
                self.data = {
                    "notifications": True,
                    "tray_autostart": False,
                    "paused": False,
                }
            except OSError as e:
                log.error(f"Error reading config file: {e}")

    def save(self) -> None:
        """Saves the configuration to file"""
        with self._lock:
            try:
                # Write to a temporary file first (atomic write)
                temp_file = f"{self.file}.tmp"
                fd = os.open(
                    temp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
                )
                with os.fdopen(fd, "w") as f:
                    json.dump(self.data, f, indent=2)

                # Rename (atomic operation on UNIX)
                os.replace(temp_file, self.file)
                self.mtime = os.path.getmtime(self.file)

            except OSError as e:
                log.error(f"Error saving config: {e}")
            except Exception as e:
                log.error(f"Unexpected error saving config: {e}", exc_info=True)

    def get_notifications(self) -> bool:
        """Gets the notification state."""
        with self._lock:
            self.load()
            return bool(self.data.get("notifications", True))

    def set_notifications(self, state: bool) -> None:
        """
        Sets the notification state.
        state: True to enable, False to disable
        """
        with self._lock:
            self.data["notifications"] = bool(state)
            self.save()

    def get_tray_autostart(self) -> bool:
        """Gets whether the tray icon should start automatically."""
        with self._lock:
            self.load()
            return bool(self.data.get("tray_autostart", False))

    def set_tray_autostart(self, state: bool) -> None:
        """Sets whether the tray icon should start automatically."""
        with self._lock:
            self.data["tray_autostart"] = bool(state)
            self.save()

    def get_paused(self) -> bool:
        """Gets whether the monitoring daemon is paused."""
        with self._lock:
            self.load()
            return bool(self.data.get("paused", False))

    def set_paused(self, state: bool) -> None:
        """Sets whether the monitoring daemon is paused."""
        with self._lock:
            self.data["paused"] = bool(state)
            self.save()


class ManualWallpaper:
    """
    Manages the persistent set of wallpaper->color associations.
    Only stores the wallpaper and the color (without timestamps).
    Thread-safe for reads/writes.
    """

    def __init__(self, max_entries: int = 256):
        self.file = CONFIG_PATHS["wall_file"]
        self.mtime = 0
        self.history = []  # type: list
        self.max_entries = max_entries
        import threading

        self._lock = threading.RLock()
        self.load()

    def _normalize_value(self, v):
        if isinstance(v, str) and v.lower() == "none":
            return None
        return v

    def _normalize_entry(self, wp, col) -> dict:
        wp = self._normalize_value(wp)
        col = self._normalize_value(col)
        return {"wallpaper": wp, "color": col}

    def load(self) -> None:
        """Loads associations from file if it has been modified"""
        with self._lock:
            if not os.path.exists(self.file):
                try:
                    dirn = os.path.dirname(self.file)
                    if dirn:
                        os.makedirs(dirn, exist_ok=True)
                except Exception:
                    pass
                self.history = []
                self.save()
                return

            try:
                mtime = os.path.getmtime(self.file)
                if mtime <= self.mtime:
                    return

                with open(self.file, "r") as f:
                    content = f.read()
                    if not content.strip():
                        self.history = []
                    else:
                        loaded = json.loads(content)
                        raw_entries = []

                        # Backward compatibility with different old formats
                        if isinstance(loaded, dict):
                            if "walls" in loaded:
                                walls = loaded["walls"]
                                raw_entries = (
                                    walls if isinstance(walls, list) else [walls]
                                )
                            elif "history" in loaded:
                                raw_entries = loaded["history"]
                            elif "wallpaper" in loaded:
                                raw_entries = [loaded]
                            else:
                                raw_entries = []
                        elif isinstance(loaded, list):
                            raw_entries = loaded

                        # Normalize and deduplicate keeping the last one
                        dedup_map = {}
                        order = []
                        for item in raw_entries:
                            if isinstance(item, dict) and (
                                "wallpaper" in item or "color" in item
                            ):
                                wp = self._normalize_value(item.get("wallpaper"))
                                col = self._normalize_value(item.get("color"))
                                key = wp
                                if key in dedup_map:
                                    try:
                                        order.remove(key)
                                    except ValueError:
                                        pass
                                dedup_map[key] = col
                                order.append(key)

                        normalized = []
                        for k in order:
                            normalized.append(
                                {"wallpaper": k, "color": dedup_map.get(k)}
                            )

                        if len(normalized) > self.max_entries:
                            normalized = normalized[-self.max_entries :]

                        self.history = normalized

                self.mtime = mtime

            except (json.JSONDecodeError, OSError) as e:
                log.error(f"Error reading wall file: {e}")

    def save(self) -> None:
        """Saves the associations to file (atomic write)"""
        with self._lock:
            try:
                temp_file = f"{self.file}.tmp"
                payload = {"walls": self.history}
                fd = os.open(
                    temp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
                )
                with os.fdopen(fd, "w") as f:
                    json.dump(payload, f, indent=2)

                os.replace(temp_file, self.file)
                try:
                    self.mtime = os.path.getmtime(self.file)
                except OSError:
                    pass

            except OSError as e:
                log.error(f"Error saving wall file: {e}")

    def get_current(self) -> dict:
        """Returns the most recent association"""
        with self._lock:
            self.load()
            if not self.history:
                return {"wallpaper": None, "color": None}
            last = self.history[-1]
            return {"wallpaper": last.get("wallpaper"), "color": last.get("color")}

    def get_history(self) -> list:
        with self._lock:
            self.load()
            return [dict(entry) for entry in self.history]

    def add_wall(self, wallpaper: Optional[str], color: Optional[str]) -> None:
        """Adds or updates the wallpaper->color association"""
        with self._lock:
            self.load()
            entry = self._normalize_entry(wallpaper, color)

            if self.history:
                last = self.history[-1]
                if (
                    last.get("wallpaper") == entry["wallpaper"]
                    and last.get("color") == entry["color"]
                ):
                    return

            new_history = [
                e for e in self.history if e.get("wallpaper") != entry["wallpaper"]
            ]
            new_history.append(entry)

            if len(new_history) > self.max_entries:
                new_history = new_history[-self.max_entries :]

            self.history = new_history
            self.save()

    def clear_history(self) -> None:
        with self._lock:
            self.history = []
            self.save()


# Global instances
CONFIG_MANAGER = DynamicConfig()
MANUAL_WALL = ManualWallpaper()
