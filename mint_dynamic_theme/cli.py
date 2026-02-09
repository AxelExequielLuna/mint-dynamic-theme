import sys
import argparse
import logging
from .utils import setup_logging, get_daemon_status, pid_file_manager
from .config import CONFIG_PATHS
from .daemon import Daemon
from .theme import ThemeService, THEME_MAPPING
from .color import ColorService
from .desktop.cinnamon import CinnamonDesktop # as default or factory needed? 
# actually Daemon detects environment.

# We need to expose a way to run the daemon from CLI

def cmd_start():
    if get_daemon_status()["status"] == "running":
        print("Daemon is already running.")
        return

    # Daemonize? 
    # Systemd service handles daemonization usually. 
    # But if running manually 'mdt start', we might want to just run blocking or fork.
    # The original script ran blocking but had logic for PID file.
    
    # We will run blocking here, assuming systemd or user puts it in background.
    # But to be true to 'start' command, maybe we should just run the Daemon.run() 
    
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
    import signal
    import os
    import time
    
    status = get_daemon_status()
    if status["status"] != "running":
        print("Daemon not running.")
        return
        
    pid = status["pid"]
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
    from .config import MANUAL_WALL
    from .daemon import Daemon
    
    color = args.color.capitalize()
    if color not in THEME_MAPPING:
        print(f"Invalid color: {color}")
        return

    # Update manual config
    # We need to know current wallpaper to set association
    # We can instantiate a Daemon temporarily to get the desktop env and wallpaper
    # or just use the Desktop classes directly.
    
    d = Daemon() 
    wp = d.desktop_env.get_wallpaper()
    
    if wp:
        MANUAL_WALL.add_wall(wp, color)
        print(f"Associated {wp} with {color}")
        
        # If daemon is running, it should pick this up on next cycle/check.
        # But commonly we want to apply it NOW.
        # If daemon is running, we might need to signal it? 
        # The daemon monitors file changes (except for manual wall config which is internal).
        # Actually Daemon._process reads MANUAL_WALL every time.
        # So we just need to trigger a check.
        # OR we just apply it directly here.
        
        themes = ThemeService.get_themes_for_color(color)
        applied_any = False
        for k, v in themes.items():
            if d.desktop_env.apply_theme(k, v):
                applied_any = True
        
        if applied_any:
            ThemeService.notify_change(color)
            print(f"Applied {color} theme.")
    else:
        print("Could not detect current wallpaper.")


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

def cmd_about():
    about_info = {
        "app": "Mint Dynamic Theme",
        "version": "1.6.0",
        "author": "Axeleif",
        "description": "Dynamic theme switcher for Linux Mint (Cinnamon, MATE, XFCE) based on wallpaper color.",
        "commands": ["start", "stop", "status", "list", "set", "about", "notify"]
    }
    # Print as JSON for consistency with original or just text? Original used JSON.
    import json
    print(json.dumps(about_info, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Mint Dynamic Theme (mdt)")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("start", help="Start the daemon")
    subparsers.add_parser("stop", help="Stop the daemon")
    subparsers.add_parser("status", help="Show daemon status")
    subparsers.add_parser("list", help="List available themes")
    subparsers.add_parser("about", help="Show app information")
    
    notify_parser = subparsers.add_parser("notify", help="Enable/Disable notifications")
    notify_parser.add_argument("state", help="on/off")
    
    set_parser = subparsers.add_parser("set", help="Manually set theme for current wallpaper")
    set_parser.add_argument("color", help="Color name (e.g. Red, Blue)")

    args = parser.parse_args()

    if args.command == "start":
        cmd_start()
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "status":
        cmd_status()
    elif args.command == "list":
        cmd_list()
    elif args.command == "about":
        cmd_about()
    elif args.command == "notify":
        cmd_notify(args)
    elif args.command == "set":
        cmd_set(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
