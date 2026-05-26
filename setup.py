import os
import shutil
import subprocess
from setuptools import setup, find_packages
from setuptools.command.install import install


class PostInstallCommand(install):
    """
    Custom install step: copies mdt.service to the user's systemd unit
    directory (~/.config/systemd/user/) and reloads the daemon so that
    'systemctl --user enable/start mdt' works immediately after install.
    """
    def run(self):
        # Run the standard install first
        super().run()
        self._install_systemd_service()

    def _install_systemd_service(self):
        src = os.path.join(os.path.dirname(__file__), "mdt.service")
        if not os.path.isfile(src):
            print("[MDT] mdt.service not found – skipping systemd install.")
            return

        # Resolve destination: honour $XDG_CONFIG_HOME if set
        xdg_config = os.environ.get(
            "XDG_CONFIG_HOME",
            os.path.join(os.path.expanduser("~"), ".config")
        )
        dest_dir = os.path.join(xdg_config, "systemd", "user")
        dest = os.path.join(dest_dir, "mdt.service")

        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(src, dest)
            print(f"[MDT] Service installed → {dest}")

            # Reload the systemd user daemon so the new unit is visible
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=False   # Don't abort install if systemd isn't running (e.g. CI)
            )
            print("[MDT] systemctl --user daemon-reload  ✓")
            print("[MDT] You can now run:  systemctl --user enable --now mdt")
        except Exception as exc:
            print(f"[MDT] Warning: could not install systemd service: {exc}")


setup(
    name="mint-dynamic-theme",
    version="4.0.0",
    description="Dynamic theme switcher for Linux Mint (Cinnamon, MATE, XFCE) based on wallpaper color.",
    author="Axeleif",
    packages=find_packages(),
    install_requires=[
        "colorthief",
        "watchdog",
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
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.6",
)
