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

### Install
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

## Configuration
Configuration is stored in `~/.cache/mint-dynamic-theme/config.json`.
Logs are in `~/.cache/mint-dynamic-theme/errors.log`.

## Development
To run from source without installing:
```bash
python3 -m mint_dynamic_theme.cli start
```
