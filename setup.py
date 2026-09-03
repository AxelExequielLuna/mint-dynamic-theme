import os
import re
import shutil
import subprocess
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.install import install

PROJECT_ROOT = Path(__file__).resolve().parent

_VERSION_RE = re.compile(r'__version__\s*=\s*["\']([^"\']+)["\']')


def read_version() -> str:
    init = PROJECT_ROOT / "src" / "mint_dynamic_theme" / "__init__.py"
    m = _VERSION_RE.search(init.read_text(encoding="utf-8"))
    if not m:
        raise RuntimeError("could not find __version__ in the package")
    return m.group(1)


VERSION = read_version()


class PostInstallCommand(install):
    """
    Custom install step: copies mdt.service to the user's systemd unit
    directory (~/.config/systemd/user/) and reloads the daemon so that
    'systemctl --user enable/start mdt' works immediately after
    installation.
    """

    def run(self):
        # Run the standard install first
        super().run()
        self._install_systemd_service()

    def _install_systemd_service(self):
        src = PROJECT_ROOT / "packaging" / "files" / "mdt.service"
        if not src.is_file():
            print("[MDT] mdt.service not found – skipping systemd install.")
            return

        # Resolve destination: respect $XDG_CONFIG_HOME if defined
        xdg_config = os.environ.get(
            "XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")
        )
        dest_dir = os.path.join(xdg_config, "systemd", "user")
        dest = os.path.join(dest_dir, "mdt.service")

        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(src, dest)
            print(f"[MDT] Service installed → {dest}")

            # Reload the user systemd daemon so that the new unit is visible
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=False,  # Do not abort the install if systemd is not running (e.g. CI)
            )
            print("[MDT] systemctl --user daemon-reload  ✓")
            print("[MDT] You can now run:  systemctl --user enable --now mdt")
        except Exception as exc:
            print(f"[MDT] Warning: could not install systemd service: {exc}")


setup(
    name="mint-dynamic-theme",
    version=VERSION,
    description="Dynamic theme switcher for Linux Mint (Cinnamon, MATE, XFCE) based on wallpaper color.",
    author="Axeleif",
    packages=find_packages("src"),
    package_dir={"": "src"},
    package_data={
        "mint_dynamic_theme": ["locales/*/messages.json"],
    },
    include_package_data=True,
    install_requires=[
        "colorthief==0.2.1",
        "watchdog==6.0.0",
        "Pillow==11.1.0",
    ],
    entry_points={
        "console_scripts": [
            "mdt=mint_dynamic_theme.cli:main",
        ],
    },
    cmdclass={
        "install": PostInstallCommand,
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.8",
)
