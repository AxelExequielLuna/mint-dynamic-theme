from . import __version__

APP_INFO = {
    "app": "Mint Dynamic Theme",
    "version": __version__,
    "author": "Axel Luna",
    "description": (
        "Dynamic theme switcher for Linux Mint "
        "(Cinnamon, MATE, XFCE) based on wallpaper color."
    ),
    "commands": [
        "start",
        "stop",
        "status",
        "list",
        "set",
        "about",
        "notify",
        "clear-history",
        "tray",
        "tray-autostart",
    ],
}
