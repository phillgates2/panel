Panel Installer (PoC)

This folder contains an initial scaffold for a cross-platform
installer/uninstaller with CLI and a PySide6 GUI PoC.

PoC usage (dev):

- Install dependencies for development: `pip install -r requirements-dev.txt` (contains PySide6 for GUI and pytest for tests)
- Run GUI: `python -m tools.installer.gui`
- Run CLI: `python -m tools.installer` or `python -m tools.installer.cli install --domain example.com` (use `--dry-run` to simulate)
- Manage/Retry Rollback via GUI: use "Manage Rollback" button to view recorded actions, run a dry-run, execute rollback, or retry failed actions
- Run unit and integration tests: `pytest tests/test_installer_*.py tests/test_integration_install_uninstall.py`

Notes:

- Admin/elevation helpers are implemented for aware re-exec, but OS-specific nuances should be validated on each platform.
- Concrete installers implemented (Linux PoC): PostgreSQL, Redis, Nginx, Python env (venv). Packaging and cross-platform service management are TODO and will be implemented next.
