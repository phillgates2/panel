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

Enhancements:

- Configurable venv path: use `--venv-path /custom/path` with `install` to set Python venv target. The path is recorded in state for accurate rollback.
- Service mappings per OS: installer now uses OS-specific service names (Linux/macOS/Windows) when enabling/starting services.
- Richer state details: state file includes per-action timestamps, host OS/arch, and a meta section with `last_action_ts`. Rollback preserves meta and returns it in results.

CLI examples:

- Install with custom venv path:
  `python -m tools.installer.cli install --domain example.com --components postgres,redis,nginx,python --venv-path C:\\panel\\venv`
- Uninstall dry-run without elevation:
  `python -m tools.installer.cli uninstall --dry-run --no-elevate`
