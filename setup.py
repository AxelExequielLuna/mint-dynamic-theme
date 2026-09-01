import os
import shutil
import subprocess

from setuptools import find_packages, setup
from setuptools.command.install import install

import mint_dynamic_theme

VERSION = mint_dynamic_theme.__version__


class PostInstallCommand(install):
    """
    Paso de instalación personalizado: copia mdt.service al directorio de
    unidades systemd del usuario (~/.config/systemd/user/) y recarga el daemon
    para que 'systemctl --user enable/start mdt' funcione inmediatamente después
    de la instalación.
    """

    def run(self):
        # Ejecutar la instalación estándar primero
        super().run()
        self._install_systemd_service()

    def _install_systemd_service(self):
        src = os.path.join(os.path.dirname(__file__), "mdt.service")
        if not os.path.isfile(src):
            print("[MDT] mdt.service not found – skipping systemd install.")
            return

        # Resolver destino: respetar $XDG_CONFIG_HOME si está definido
        xdg_config = os.environ.get(
            "XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")
        )
        dest_dir = os.path.join(xdg_config, "systemd", "user")
        dest = os.path.join(dest_dir, "mdt.service")

        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(src, dest)
            print(f"[MDT] Service installed → {dest}")

            # Recargar el daemon de systemd del usuario para que la nueva unidad sea visible
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=False,  # No abortar la instalación si systemd no está corriendo (ej. CI)
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
    packages=find_packages(),
    install_requires=[
        "colorthief==0.2.1",
        "watchdog==6.0.0",
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
