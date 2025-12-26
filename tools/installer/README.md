Panel Installer (PoC)

This folder contains an initial scaffold for a cross-platform
installer/uninstaller with CLI and a PySide6 GUI PoC.

PoC usage (dev):

- Install dependencies for development: `pip install -r requirements-dev.txt` (contains PySide6 for GUI and pytest for tests)
- Run GUI: `python -m tools.installer.gui`
- Run CLI: `python -m tools.installer` or `python -m tools.installer.cli install --domain example.com` (use `--dry-run` to simulate)
- Run unit tests: `pytest tests/test_installer_*.py`

Notes:

- Admin/elevation helpers are implemented for aware re-exec, but OS-specific nuances should be validated on each platform.
- Concrete installers implemented (Linux PoC): PostgreSQL, Redis, Nginx, Python env (venv). Packaging and cross-platform service management are TODO and will be implemented next.
