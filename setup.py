from setuptools import setup, find_packages

setup(
    name="mint-dynamic-theme",
    version="1.6.0",
    description="Dynamic theme switcher for Linux Mint (Cinnamon, MATE, XFCE) based on wallpaper color.",
    author="Axeleif",
    packages=find_packages(),
    install_requires=[
        "colorthief",
        "watchdog"
    ],
    entry_points={
        "console_scripts": [
            "mdt=mint_dynamic_theme.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.6',
)
