# Testing Instructions

Since the environment is managed externally and we are avoiding `venv` for the final install, you can run tests using the built-in `unittest` framework directly from the source directory.

## Prerequisite
Ensure dependencies are installed:
```bash
pip3 install colorthief watchdog --break-system-packages
# OR if you prefer to test without installing to system:
# pip3 install --user colorthief watchdog
```

## Running Unit Tests
Run the following command from the project root:

```bash
python3 -m unittest discover tests
```

Expected Output:
```
....
----------------------------------------------------------------------
Ran 4 tests in 0.001s

OK
```

## Manual Verification Steps
1.  **Start Daemon**:
    ```bash
    python3 -m mint_dynamic_theme.cli start
    ```
2.  **Change Wallpaper**: Change your desktop wallpaper to a distinctly red image.
3.  **Verify**: Check if your theme changes to Red.
4.  **CLI Check**:
    ```bash
    python3 -m mint_dynamic_theme.cli status
    python3 -m mint_dynamic_theme.cli about
    ```
