import argparse
import logging
import os
import sys

from . import __version__
from .color import ColorService
from .config import CONFIG_PATHS
from .daemon import Daemon
from .theme import THEME_MAPPING
from .utils import get_daemon_status, pid_file_manager, setup_logging


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write(f"mdt: error: {message}\n")
        sys.stderr.write(f"Try 'mdt -h' for help.\n")
        sys.exit(2)

# actually Daemon detects environment.

# We need to expose a way to run the daemon from CLI


def cmd_start():
    status = get_daemon_status()
    if status["status"] == "running":
        print("Daemon is already running.")
        return

    # The pid file may refer to a dead process or to a recycled PID
    # from another process. It is removed so that the daemon can start.
    try:
        if os.path.exists(CONFIG_PATHS["pid_file"]):
            os.remove(CONFIG_PATHS["pid_file"])
    except OSError as e:
        print(f"Warning: could not remove stale pid file: {e}")

    print("Starting daemon in foreground (Ctrl+C to stop).")
    print("Tip: use the systemd user service for background autostart.")
    print("     systemctl --user enable --now mdt")

    log = setup_logging()

    # Create PID file
    try:
        with pid_file_manager(CONFIG_PATHS["pid_file"]):
            daemon = Daemon()
            daemon.run()
    except Exception as e:
        print(f"Error starting daemon: {e}")
        log.error(f"Startup error: {e}")


def cmd_stop():
    # Helper to stop via PID
    import os
    import signal
    import time

    from .utils import is_mdt_process

    status = get_daemon_status()
    if status["status"] != "running":
        print("Daemon not running.")
        return

    pid = status["pid"]
    if not is_mdt_process(pid):
        print(
            f"Refusing to stop PID {pid}: it does not look like the mdt daemon "
            "(possible recycled PID). Remove the stale pid file manually if needed."
        )
        return

    try:
        os.kill(pid, signal.SIGTERM)
        # Wait
        for _ in range(50):
            if not get_daemon_status()["status"] == "running":
                print("Stopped.")
                return
            time.sleep(0.1)
        os.kill(pid, signal.SIGKILL)
        print("Killed.")
    except Exception as e:
        print(f"Error stopping: {e}")


def cmd_status():
    st = get_daemon_status()
    print(f"Status: {st['status']}")
    if st.get("pid"):
        print(f"PID: {st['pid']}")


def cmd_list():
    print("Available Color Themes:")
    for color in THEME_MAPPING.keys():
        print(f" - {color}")


def cmd_set(args):
    from .daemon import Daemon

    color = args.color.capitalize()
    if color not in THEME_MAPPING:
        print(f"Invalid color: {color}")
        return

    applied_any, wp = Daemon().force_apply(color)

    if wp:
        if applied_any:
            print(f"Applied {color} theme.")
        else:
            print(f"Associated {wp} with {color}, but could not apply any theme.")


def cmd_notify(args):
    from .config import CONFIG_MANAGER

    state = args.state.lower()
    if state in ["on", "true", "1"]:
        CONFIG_MANAGER.set_notifications(True)
        print("✓ Notifications enabled.")
    elif state in ["off", "false", "0"]:
        CONFIG_MANAGER.set_notifications(False)
        print("✓ Notifications disabled.")
    else:
        print("Error: Use 'on' or 'off'")


def cmd_clear_history():
    from .config import MANUAL_WALL

    try:
        MANUAL_WALL.clear_history()
        print("✓ Manual wallpaper history cleared.")
    except Exception as e:
        print(f"Error clearing history: {e}")


def cmd_history():
    from .config import MANUAL_WALL

    history = MANUAL_WALL.get_history()
    if not history:
        print("No wallpaper associations in history.")
        return

    print(f"Wallpaper history ({len(history)} entries):")
    for i, entry in enumerate(history, 1):
        wp = entry.get("wallpaper") or "(none)"
        color = entry.get("color") or "(auto)"
        print(f"  {i}. {wp} -> {color}")


def cmd_about():
    import json

    from .metadata import APP_INFO

    print(json.dumps(APP_INFO, indent=2))


def cmd_tray():
    try:
        from .tray import MDTTrayApp

        print("Starting native Tray Icon...")
        app = MDTTrayApp()
        app.run()
    except Exception as e:
        print(f"Error starting tray app: {e}")


def cmd_tray_autostart(args):
    from .config import CONFIG_MANAGER
    from .tray import manage_autostart_desktop_file

    state = args.state.lower()
    if state in ["on", "true", "1"]:
        manage_autostart_desktop_file(True)
        CONFIG_MANAGER.set_tray_autostart(True)
        print("✓ Tray autostart enabled.")
    elif state in ["off", "false", "0"]:
        manage_autostart_desktop_file(False)
        CONFIG_MANAGER.set_tray_autostart(False)
        print("✓ Tray autostart disabled.")
    else:
        print("Error: Use 'on' or 'off'")


def main():
    parser = _Parser(
        prog="mdt",
        usage="mdt [-h] [--version] <command> ...",
        description="Mint Dynamic Theme (mdt)",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("start", help="Start the daemon")
    subparsers.add_parser("stop", help="Stop the daemon")
    subparsers.add_parser("status", help="Show daemon status")
    subparsers.add_parser("list", help="List available themes")
    subparsers.add_parser("history", help="List wallpaper-color associations")
    subparsers.add_parser("about", help="Show app information")

    notify_parser = subparsers.add_parser("notify", help="Enable/Disable notifications")
    notify_parser.add_argument("state", help="on/off")

    set_parser = subparsers.add_parser(
        "set", help="Manually set theme for current wallpaper"
    )
    set_parser.add_argument("color", help="Color name (e.g. Red, Blue)")

    subparsers.add_parser("clear-history", help="Clear manual wallpaper history")

    subparsers.add_parser("tray", help="Start the native tray icon")

    tray_autostart_parser = subparsers.add_parser(
        "tray-autostart", help="Enable/Disable tray autostart with the desktop"
    )
    tray_autostart_parser.add_argument("state", help="on/off")

    args = parser.parse_args()

    if args.command == "start":
        cmd_start()
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "status":
        cmd_status()
    elif args.command == "list":
        cmd_list()
    elif args.command == "history":
        cmd_history()
    elif args.command == "about":
        cmd_about()
    elif args.command == "notify":
        cmd_notify(args)
    elif args.command == "set":
        cmd_set(args)
    elif args.command == "clear-history":
        cmd_clear_history()
    elif args.command == "tray":
        cmd_tray()
    elif args.command == "tray-autostart":
        cmd_tray_autostart(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
