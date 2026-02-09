import os
import subprocess
import logging
from typing import Dict
from .config import CONFIG_MANAGER

log = logging.getLogger("mint-dynamic-theme")

THEME_MAPPING = {
    "Green": {"gtk": "Mint-Y-Dark", "icon": "Mint-Y", "desktop": "Mint-Y-Dark"},
    "Aqua": {"gtk": "Mint-Y-Dark-Aqua", "icon": "Mint-Y-Aqua", "desktop": "Mint-Y-Dark-Aqua"},
    "Blue": {"gtk": "Mint-Y-Dark-Blue", "icon": "Mint-Y-Blue", "desktop": "Mint-Y-Dark-Blue"},
    "Brown": {"gtk": "Mint-Y-Dark-Brown", "icon": "Mint-Y-Brown", "desktop": "Mint-Y-Dark-Brown"},
    "Grey": {"gtk": "Mint-Y-Dark-Grey", "icon": "Mint-Y-Grey", "desktop": "Mint-Y-Dark-Grey"},
    "Orange": {"gtk": "Mint-Y-Dark-Orange", "icon": "Mint-Y-Orange", "desktop": "Mint-Y-Dark-Orange"},
    "Pink": {"gtk": "Mint-Y-Dark-Pink", "icon": "Mint-Y-Pink", "desktop": "Mint-Y-Dark-Pink"},
    "Purple": {"gtk": "Mint-Y-Dark-Purple", "icon": "Mint-Y-Purple", "desktop": "Mint-Y-Dark-Purple"},
    "Red": {"gtk": "Mint-Y-Dark-Red", "icon": "Mint-Y-Red", "desktop": "Mint-Y-Dark-Red"},
    "Sand": {"gtk": "Mint-Y-Dark-Sand", "icon": "Mint-Y-Sand", "desktop": "Mint-Y-Dark-Sand"},
    "Teal": {"gtk": "Mint-Y-Dark-Teal", "icon": "Mint-Y-Teal", "desktop": "Mint-Y-Dark-Teal"},
    "Cyan": {"gtk": "Mint-Y-Dark-Teal", "icon": "Mint-Y-Cyan", "desktop": "Mint-Y-Dark-Teal"},
    "Navy": {"gtk": "Mint-Y-Dark-Teal", "icon": "Mint-Y-Navy", "desktop": "Mint-Y-Dark-Teal"},
    "Yellow": {"gtk": "Mint-Y-Dark-Sand", "icon": "Mint-Y-Sand", "desktop": "Mint-Y-Dark-Sand"},
}

class ThemeService:
    @staticmethod
    def theme_exists(theme_type: str, theme_name: str) -> bool:
        base_dir = "/usr/share/themes" if theme_type in ["gtk", "desktop"] else "/usr/share/icons"
        theme_path = os.path.join(base_dir, theme_name)
        return os.path.exists(theme_path) and os.path.isdir(theme_path)

    @staticmethod
    def get_themes_for_color(color_name: str) -> Dict[str, str]:
        return THEME_MAPPING.get(color_name, THEME_MAPPING["Green"])

    @staticmethod
    def notify_change(color: str):
        if CONFIG_MANAGER.get_notifications():
            try:
                subprocess.run(
                    ["notify-send", "Tema Dinámico", f"Tema aplicado: {color}"],
                    check=False, timeout=5,
                    capture_output=True
                )
            except Exception as e:
                log.error(f"Error sending notification: {e}")
