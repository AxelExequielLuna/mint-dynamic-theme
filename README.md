# Mint Dynamic Theme Daemon (MDT)

A daemon that automatically changes your GTK, Icon, and Desktop theme based on your current wallpaper's dominant color.

## Features
- **Automatic Detection**: Extracts dominant color from current wallpaper.
- **Optimized**: Uses smart resizing to process 4K wallpapers instantly.
- **Multi-DE Support**: Works on Cinnamon, MATE, and XFCE.
- **Manual Override**: Remember your preferred theme for specific wallpapers.

## Installation

### Prerequisites
- Python 3.6+
- `colorthief` (automatically installed)
- `watchdog` (automatically installed)

### Recommended: install the .deb package

Prebuilt `.deb` packages are provided for every base distribution
(`ubuntu-24.04` and `ubuntu-22.04` for the Mint Ubuntu edition; `debian-12`
and `debian-13` for LMDE). Each package bundles an isolated Python venv, a
`/usr/bin/mdt` launcher, a systemd user unit and the tray autostart.

1. Grab the `.deb` matching your system
   (`mint-dynamic-theme_<ver>-1_all.deb`) and verify its SHA-256 checksum
   against `SHA256SUMS-<ver>.txt`:
   ```bash
   sha256sum -c SHA256SUMS-4.0.1.txt --ignore-missing
   ```
2. Install it (apt resolves the GTK/XApp dependencies automatically):
   ```bash
   sudo apt install ./mint-dynamic-theme_4.0.1-1_all.deb
   ```
3. Enable the daemon for auto-start:
   ```bash
   systemctl --user enable --now mdt
   mdt status
   ```
   The tray icon starts automatically on your next login.

To upgrade later, install the newer `.deb` the same way (your config in
`~/.config/mint-dynamic-theme/` is preserved). `sudo apt remove
mint-dynamic-theme` keeps that config; `sudo apt purge mint-dynamic-theme`
deletes it.

### Alternative: install from source (pip)
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd MintAutoThemeDaemon
   ```

2. Install in user mode:
   If you have `pipx` installed (recommended for tools):
   ```bash
   pipx install .
   ```
   
   Or using standard pip (user level):
   ```bash
   pip3 install --user . --break-system-packages
   ```
   
   **To update the already installed version:**
   ```bash
   pip3 install --user --upgrade . --break-system-packages
   ```

   *Note: On recent Debian/Ubuntu/Mint versions, `--break-system-packages` is required to install outside a venv/apt, even for user installs. This is safe for user-level tools.*

3. Install Systemd Service (Optional but recommended for auto-start):
   ```bash
   mkdir -p ~/.config/systemd/user/
   cp mdt.service ~/.config/systemd/user/
   # Ensure the ExecStart path in mdt.service points to valid `mdt` executable
   # usually ~/.local/bin/mdt
   nano ~/.config/systemd/user/mdt.service 
   systemctl --user daemon-reload
   systemctl --user enable --now mdt.service
   ```

## Usage

Control the daemon using the `mdt` command:

- **Start**: `mdt start` (starts the daemon process)
- **Stop**: `mdt stop`
- **Status**: `mdt status`
- **List Themes**: `mdt list`
- **Manual Override**: `mdt set Red` (Forces 'Red' theme for current wallpaper and remembers it)
- **Notifications**: `mdt notify on|off`
- **Clear History**: `mdt clear-history`
- **About**: `mdt about`
- **Tray Icon**: `mdt tray` (native XApp tray icon)
- **Tray Autostart**: `mdt tray-autostart on|off`

> **Note:** `mdt start` runs the daemon in the **foreground** (blocking).
> The recommended deployment for auto-start is the systemd user service
> (see below). The tray icon (`mdt tray`) is an alternative way to run it.

## Configuration
Configuration is stored in `$XDG_CONFIG_HOME/mint-dynamic-theme/`
(i.e. `~/.config/mint-dynamic-theme/config.json` by default).
Logs are in the same directory at `errors.log`.
Set `MDT_LOG_LEVEL` (e.g. `DEBUG`, `INFO`) to change the log verbosity
(defaults to `ERROR`).

## Development
To run from source without installing:
```bash
python3 -m mint_dynamic_theme.cli start
```

### Build the .deb package
Requires Docker (`podman` can be adapted). From the repo root:
```bash
python3 scripts/build_deb.py                                     # build every out-of-date target
python3 scripts/build_deb.py --targets debian:13 --force         # rebuild one target
python3 scripts/build_deb.py --check                             # show what would be rebuilt
```
The version is read from `mint_dynamic_theme/__init__.py`. On a version bump
the script regenerates `requirements.lock`, `debian/changelog`, the `.deb` for
every target and `dist/deb/SHA256SUMS-<ver>.txt`. Artifacts land in `dist/deb/`
(ignored by git).
