import logging
import os

# Set up logging
log = logging.getLogger("mint-dynamic-theme")

try:
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("XApp", "1.0")

    from gi.repository import GLib, Gtk, XApp

    GUI_AVAILABLE = True

except ImportError as e:
    GUI_AVAILABLE = False
    log.warning(f"GUI Libraries not available: {e}")

from .config import CONFIG_MANAGER, MANUAL_WALL
from .daemon import Daemon
from .metadata import APP_INFO
from .theme import THEME_MAPPING, ThemeService
from .utils import get_daemon_status


def manage_autostart_desktop_file(enabled: bool) -> None:
    """Creates or removes the XDG Autostart .desktop file for the tray icon."""

    autostart_dir = os.path.expanduser("~/.config/autostart")
    desktop_file = os.path.join(autostart_dir, "mdt-tray.desktop")

    if enabled:
        try:
            os.makedirs(autostart_dir, exist_ok=True)

            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Exec=mdt tray\n"
                "Hidden=false\n"
                "NoDisplay=false\n"
                "X-GNOME-Autostart-enabled=true\n"
                "Name=Mint Dynamic Theme Tray\n"
                "Comment=Bandeja del sistema para Mint Dynamic Theme\n"
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
            raise RuntimeError(
                "GUI Gtk/XApp libraries are not available on this system."
            )

        # Native XApp tray icon
        self.icon = XApp.StatusIcon()

        self.icon.set_name("mint-dynamic-theme")
        self.icon.set_label("MDT")
        self.icon.set_tooltip_text("Mint Dynamic Theme")
        self.icon.set_icon_name("preferences-desktop-wallpaper")

        # Menu state variables
        self.status_item = None
        self.pause_item = None
        self.autostart_item = None

        # Build menu once
        self.menu = self.build_menu()

        # Let XApp handle popup/menu lifecycle
        self.icon.set_primary_menu(self.menu)

        # Polling refresh
        GLib.timeout_add_seconds(2, self.update_status_loop)

    def run(self) -> None:
        log.info("Starting GTK main loop for tray icon.")
        Gtk.main()

    def update_status_loop(self) -> bool:
        """Periodic status updater."""

        try:
            self.refresh_menu_labels()

        except Exception as e:
            log.error(f"Error updating tray status: {e}")

        return True

    def refresh_menu_labels(self) -> None:
        """Updates menu labels from daemon state."""

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

        # Status
        self.status_item = Gtk.MenuItem(label="Estado: Cargando...")

        self.status_item.set_sensitive(False)

        menu.append(self.status_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Pause/Resume
        self.pause_item = Gtk.MenuItem(label="Pausar Monitoreo")

        self.pause_item.connect("activate", self.on_toggle_pause)

        menu.append(self.pause_item)

        # Force color submenu
        color_menu_item = Gtk.MenuItem(label="Forzar Color de Tema")

        color_sub = Gtk.Menu()

        for color_name in sorted(THEME_MAPPING.keys()):
            item = Gtk.MenuItem(label=color_name)

            item.connect("activate", self.on_force_color, color_name)

            color_sub.append(item)

        color_menu_item.set_submenu(color_sub)

        menu.append(color_menu_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Clear history
        clear_history_item = Gtk.MenuItem(label="Limpiar Historial de Fondos")

        clear_history_item.connect("activate", self.on_clear_history)

        menu.append(clear_history_item)

        # Tray autostart
        self.autostart_item = Gtk.CheckMenuItem(label="Tray Icon")

        self.autostart_item.set_active(CONFIG_MANAGER.get_tray_autostart())

        self.autostart_item.connect("toggled", self.on_toggle_autostart)

        menu.append(self.autostart_item)

        # Tray Notification

        self.notification_item = Gtk.CheckMenuItem(label="Notificaciones")

        self.notification_item.set_active(CONFIG_MANAGER.get_notifications())

        self.notification_item.connect("toggled", self.on_toggle_notifications)

        menu.append(self.notification_item)

        menu.append(Gtk.SeparatorMenuItem())

        # About
        about_item = Gtk.MenuItem(label="Acerca de")

        about_item.connect("activate", self.on_about)

        menu.append(about_item)

        # Exit
        exit_item = Gtk.MenuItem(label="Cerrar Bandeja")

        exit_item.connect("activate", self.on_exit)

        menu.append(exit_item)

        menu.show_all()

        self.refresh_menu_labels()

        return menu

    def on_toggle_pause(self, menu_item: Gtk.MenuItem) -> None:

        is_paused = CONFIG_MANAGER.get_paused()

        new_state = not is_paused

        CONFIG_MANAGER.set_paused(new_state)

        if not new_state:
            log.info("Resuming theme monitor: forcing wallpaper color check.")

            try:
                d = Daemon()

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

        dialog = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Limpiar Historial de Fondos",
        )

        dialog.format_secondary_text(
            "Se eliminará todo el historial de wallpapers "
            "y colores asociados.\n\n"
            "Esta acción no se puede deshacer."
        )

        dialog.set_title("Mint Dynamic Theme")

        response = dialog.run()

        dialog.destroy()

        # User cancelled
        if response != Gtk.ResponseType.OK:
            return

        try:
            MANUAL_WALL.clear_history()

            log.info("History cleared from Tray Menu.")

        except Exception as e:
            log.error(f"Error clearing history: {e}")

    def on_toggle_autostart(self, check_item: Gtk.CheckMenuItem) -> None:

        state = check_item.get_active()

        # Enabling tray
        if state:
            manage_autostart_desktop_file(True)

            CONFIG_MANAGER.set_tray_autostart(True)

            return

        # Confirmation dialog before disabling tray
        dialog = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Desactivar Tray Icon",
        )

        dialog.format_secondary_text(
            "Si desactivas el tray icon, "
            "tendrás que volver a iniciarlo manualmente "
            "desde la terminal usando:\n\n"
            "mdt tray-autostart true"
        )

        dialog.set_title("Mint Dynamic Theme")

        response = dialog.run()

        dialog.destroy()

        # User cancelled
        if response != Gtk.ResponseType.OK:
            check_item.set_active(True)

            return

        # Disable autostart
        manage_autostart_desktop_file(False)

        # Update config
        CONFIG_MANAGER.set_tray_autostart(False)

        log.info("Tray icon disabled by user.")

        # Close tray app
        Gtk.main_quit()

    def on_toggle_notifications(self, check_item: Gtk.CheckMenuItem) -> None:

        state = check_item.get_active()

        CONFIG_MANAGER.set_notifications(state)

        self.refresh_menu_labels()

    def on_about(self, menu_item: Gtk.MenuItem) -> None:

        dialog = Gtk.AboutDialog()

        dialog.set_program_name(APP_INFO["app"])

        dialog.set_version(APP_INFO["version"])

        dialog.set_comments(APP_INFO["description"])

        dialog.set_authors([APP_INFO["author"]])

        dialog.set_license_type(Gtk.License.AGPL_3_0)

        dialog.set_copyright("© 2026 Axel Luna")

        dialog.set_website("https://axel-luna.com.ar")

        dialog.set_website_label("Web")

        dialog.set_logo_icon_name("preferences-desktop-wallpaper")

        dialog.set_modal(True)

        dialog.present()

        dialog.connect("response", lambda d, r: d.destroy())

    def on_exit(self, menu_item: Gtk.MenuItem) -> None:

        log.info("Exiting Tray App.")

        Gtk.main_quit()
