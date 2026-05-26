import os
import sys
import logging
from typing import Optional

# Set up logging
log = logging.getLogger("mint-dynamic-theme")

try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('XApp', '1.0')
    from gi.repository import Gtk, XApp, GLib
    GUI_AVAILABLE = True
except ImportError as e:
    GUI_AVAILABLE = False
    log.warning(f"GUI Libraries not available: {e}")

from .config import CONFIG_MANAGER, MANUAL_WALL
from .utils import get_daemon_status
from .theme import THEME_MAPPING, ThemeService
from .daemon import Daemon

def manage_autostart_desktop_file(enabled: bool) -> None:
    """Creates or removes the XDG Autostart .desktop file for the tray icon."""
    autostart_dir = os.path.expanduser("~/.config/autostart")
    desktop_file = os.path.join(autostart_dir, "mdt-tray.desktop")
    
    if enabled:
        try:
            os.makedirs(autostart_dir, exist_ok=True)
            # We use 'mdt tray' as Exec which is the CLI entrypoint installed in user path
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Exec=mdt tray\n"
                "Hidden=false\n"
                "NoDisplay=false\n"
                "X-GNOME-Autostart-enabled=true\n"
                "Name=Mint Dynamic Theme Tray\n"
                "Comment=Bandeja del sistema nativa para el daemon de Mint Dynamic Theme\n"
                "Icon=preferences-desktop-wallpaper\n"
                "Categories=Utility;Settings;\n"
            )
            with open(desktop_file, "w") as f:
                f.write(content)
            log.info(f"Created autostart file: {desktop_file}")
        except Exception as e:
            log.error(f"Error creating autostart file: {e}")
    else:
        if os.path.exists(desktop_file):
            try:
                os.remove(desktop_file)
                log.info(f"Removed autostart file: {desktop_file}")
            except Exception as e:
                log.error(f"Error removing autostart file: {e}")


class MDTTrayApp:
    def __init__(self):
        if not GUI_AVAILABLE:
            raise RuntimeError("GUI Gtk/XApp libraries are not available on this system.")
            
        # Initialize native XApp StatusIcon
        self.icon = XApp.StatusIcon()
        self.icon.set_name("mint-dynamic-theme")
        self.icon.set_label("MDT")
        self.icon.set_tooltip_text("Mint Dynamic Theme")
        self.icon.set_icon_name("preferences-desktop-wallpaper")
        
        # XApp.StatusIcon emits 'activate' with (icon, button, time).
        # Both left and right clicks arrive here; we use the button number
        # to distinguish them if needed, but we always show the menu.
        self.icon.connect("activate", self.on_activate)
        
        # Menu state variables
        self.menu = None
        self.status_item = None
        self.pause_item = None
        self.autostart_item = None
        
        # Polling status updates every 2 seconds
        GLib.timeout_add_seconds(2, self.update_status_loop)

    def run(self) -> None:
        log.info("Starting GTK main loop for tray icon.")
        Gtk.main()

    def update_status_loop(self) -> bool:
        """Periodic status updater to keep menu items synchronized with daemon state."""
        try:
            self.refresh_menu_labels()
        except Exception as e:
            log.error(f"Error updating tray status: {e}")
        return True # Continue timer

    def refresh_menu_labels(self) -> None:
        """Reads daemon and config state and updates the menu UI elements."""
        status_info = get_daemon_status()
        is_running = status_info["status"] == "running"
        is_paused = CONFIG_MANAGER.get_paused()
        
        if self.status_item:
            if is_running:
                if is_paused:
                    self.status_item.set_label("Estado: Pausado ⏸")
                else:
                    self.status_item.set_label("Estado: Activo 🟢")
            else:
                self.status_item.set_label("Estado: No Ejecutando 🔴")
                
        if self.pause_item:
            self.pause_item.set_sensitive(is_running)
            if is_paused:
                self.pause_item.set_label("Reanudar Monitoreo")
            else:
                self.pause_item.set_label("Pausar Monitoreo")

    def build_menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()
        
        # 1. Status Label (Header)
        self.status_item = Gtk.MenuItem(label="Estado: Cargando...")
        self.status_item.set_sensitive(False)
        menu.append(self.status_item)
        
        # Separator
        menu.append(Gtk.SeparatorMenuItem())
        
        # 2. Pause/Resume Toggle
        self.pause_item = Gtk.MenuItem(label="Pausar Monitoreo")
        self.pause_item.connect("activate", self.on_toggle_pause)
        menu.append(self.pause_item)
        
        # 3. Force Color Submenu
        color_menu_item = Gtk.MenuItem(label="Forzar Color de Tema")
        color_sub = Gtk.Menu()
        
        for color_name in sorted(THEME_MAPPING.keys()):
            item = Gtk.MenuItem(label=color_name)
            item.connect("activate", self.on_force_color, color_name)
            color_sub.append(item)
            
        color_menu_item.set_submenu(color_sub)
        menu.append(color_menu_item)
        
        # Separator
        menu.append(Gtk.SeparatorMenuItem())
        
        # 4. Clear History
        clear_history_item = Gtk.MenuItem(label="Limpiar Historial de Fondos")
        clear_history_item.connect("activate", self.on_clear_history)
        menu.append(clear_history_item)
        
        # 5. Autostart Toggle
        self.autostart_item = Gtk.CheckMenuItem(label="Autoiniciar con el Escritorio")
        self.autostart_item.set_active(CONFIG_MANAGER.get_tray_autostart())
        self.autostart_item.connect("toggled", self.on_toggle_autostart)
        menu.append(self.autostart_item)
        
        # Separator
        menu.append(Gtk.SeparatorMenuItem())
        
        # 6. Exit Tray App
        exit_item = Gtk.MenuItem(label="Cerrar Bandeja")
        exit_item.connect("activate", self.on_exit)
        menu.append(exit_item)
        
        menu.show_all()
        self.refresh_menu_labels()
        return menu

    def on_activate(self, icon: XApp.StatusIcon, button: int, time: int) -> None:
        """Handle click on the tray icon (any mouse button)."""
        self.popup_menu(button, time)

    def popup_menu(self, button: int, time: int) -> None:
        if not self.menu:
            self.menu = self.build_menu()
        else:
            self.refresh_menu_labels()
        self.menu.popup(None, None, None, None, button, time)

    def on_toggle_pause(self, menu_item: Gtk.MenuItem) -> None:
        is_paused = CONFIG_MANAGER.get_paused()
        new_state = not is_paused
        CONFIG_MANAGER.set_paused(new_state)
        
        # If unpausing/resuming, force an immediate check of the background theme
        if not new_state:
            log.info("Resuming theme monitor: forcing wallpaper color check.")
            try:
                d = Daemon()
                # Run headless process check once to instantly apply colors
                GLib.idle_add(d._process)
            except Exception as e:
                log.error(f"Error executing immediate check on resume: {e}")
                
        self.refresh_menu_labels()

    def on_force_color(self, menu_item: Gtk.MenuItem, color_name: str) -> None:
        log.info(f"Tray menu forced theme color: {color_name}")
        try:
            d = Daemon()
            wp = d.desktop_env.get_wallpaper()
            if wp:
                MANUAL_WALL.add_wall(wp, color_name)
                themes = ThemeService.get_themes_for_color(color_name)
                applied_any = False
                for k, v in themes.items():
                    if d.desktop_env.apply_theme(k, v):
                        applied_any = True
                if applied_any:
                    ThemeService.notify_change(color_name)
                    log.info(f"Theme successfully applied from Tray: {color_name}")
        except Exception as e:
            log.error(f"Error applying forced color from Tray: {e}")

    def on_clear_history(self, menu_item: Gtk.MenuItem) -> None:
        try:
            MANUAL_WALL.clear_history()
            log.info("History cleared from Tray Menu.")
        except Exception as e:
            log.error(f"Error clearing history: {e}")

    def on_toggle_autostart(self, check_item: Gtk.CheckMenuItem) -> None:
        state = check_item.get_active()
        manage_autostart_desktop_file(state)
        CONFIG_MANAGER.set_tray_autostart(state)

    def on_exit(self, menu_item: Gtk.MenuItem) -> None:
        log.info("Exiting Tray App.")
        Gtk.main_quit()
