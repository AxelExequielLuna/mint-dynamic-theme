import os
import time
import logging
from typing import Optional, Tuple

from .config import MANUAL_WALL, CONFIG_PATHS
from .color import ColorService
from .theme import ThemeService
from .desktop.base import DesktopEnvironment
from .desktop.cinnamon import CinnamonDesktop
from .desktop.mate import MateDesktop
from .desktop.xfce import XfceDesktop

log = logging.getLogger("mint-dynamic-theme")

class Daemon:
    def __init__(self):
        self.last_wallpaper: Optional[str] = None
        self.last_theme: Optional[str] = None
        self.paused: bool = False
        self.running: bool = True
        self.desktop_env = self._detect_desktop()
        
    def _detect_desktop(self) -> DesktopEnvironment:
        de = os.getenv("XDG_CURRENT_DESKTOP", "").lower()
        if "cinnamon" in de: return CinnamonDesktop()
        if "mate" in de: return MateDesktop()
        if "xfce" in de: return XfceDesktop()
        return CinnamonDesktop() # Fallback

    def run(self) -> None:
        log.info(f"Starting daemon for {type(self.desktop_env).__name__}")
        import signal
        import sys

        def sigterm_handler(signum, frame):
            log.info("Received SIGTERM. Stopping daemon...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGTERM, sigterm_handler)

        try:
            self._process() # Initial run
            self.desktop_env.monitor_changes(self._process)
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            log.error(f"Daemon runtime error: {e}", exc_info=True)

    def stop(self) -> None:
        self.running = False
        self.desktop_env.stop_monitoring()

    def force_apply(self, color: str) -> Tuple[bool, str]:
        """Applies a theme for the current wallpaper manually.

        Registers the wallpaper->color association and applies the theme right
        away. Returns (applied_any, wallpaper_path).
        """
        from .config import MANUAL_WALL

        color = color.capitalize()
        wallpaper = self.desktop_env.get_wallpaper()
        if not wallpaper:
            return False, ""

        MANUAL_WALL.add_wall(wallpaper, color)

        themes = ThemeService.get_themes_for_color(color)
        applied_any = False
        for kind, name in themes.items():
            if ThemeService.theme_exists(kind, name):
                if self.desktop_env.apply_theme(kind, name):
                    applied_any = True

        if applied_any:
            ThemeService.notify_change(color)

        return applied_any, wallpaper

    def _process(self) -> None:
        from .config import CONFIG_MANAGER
        if CONFIG_MANAGER.get_paused() or not self.running: return

        try:
            wallpaper = self.desktop_env.get_wallpaper()
            if not wallpaper or wallpaper == self.last_wallpaper:
                return

            self.last_wallpaper = wallpaper # Update immediately to avoid recursion
            
            # Check manual override
            manual = MANUAL_WALL.get_current()
            manual_wp = manual.get("wallpaper")
            
            # Simple normalization for comparison
            def norm(p):
                 return os.path.normcase(os.path.realpath(p)) if p else ""
            
            is_manual = False
            theme_name = None
            
            # Check if this specific wallpaper has a manual override
            # The manual logic in original code was complex (checking history).
            # Here we simplify: get manual wall history, find if THIS wallpaper is there.
            
            # Rationale based on user code:
            # "Buscamos en el historial la entrada más reciente que coincida con este wallpaper."
            reversed_history = list(reversed(MANUAL_WALL.get_history()))
            for entry in reversed_history:
                wp = entry.get("wallpaper")
                if wp and norm(wp) == norm(wallpaper):
                    if entry.get("color"):
                        theme_name = entry.get("color").capitalize()
                        is_manual = True
                        break
            
            if not is_manual:
                rgb = ColorService.get_dominant_color(wallpaper)
                if not rgb: return
                theme_name = ColorService.get_theme_name_for_color(*rgb)

            if theme_name and theme_name != self.last_theme:
                log.info(f"Applying theme color: {theme_name} (Manual: {is_manual})")
                
                themes = ThemeService.get_themes_for_color(theme_name)
                applied_any = False
                
                # Apply gtk, icon, desktop themes
                for kind, name in themes.items():
                    if ThemeService.theme_exists(kind, name):
                         if self.desktop_env.apply_theme(kind, name):
                             applied_any = True
                
                if applied_any:
                    ThemeService.notify_change(theme_name)
                    self.last_theme = theme_name
                    
        except Exception as e:
            log.error(f"Error processing wallpaper change: {e}", exc_info=True)
