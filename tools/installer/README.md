Panel Installer (GUI)

This folder contains a PySide6 GUI installer PoC for cross-platform installation/uninstallation.

Usage:

- Install dev dependencies: `pip install -r requirements-dev.txt`
- Run GUI: `python -m tools.installer.gui`

Notes:

- Admin/elevation helpers exist but platform-specific behavior should be validated.
- Concrete installers implemented (Linux PoC): PostgreSQL, Redis, Nginx, Python env (venv).
- State tracking supports rollback and crash recovery via the GUI.

Enhancements:

- Role-based presets (dev/staging/prod)
- Wizard flow (preflight ? validate ? install ? health ? summary)
- Secrets via OS keyring (DB password)
- Advanced logs (filter/search/severity, redacted export)
- Diagnostics (tail component logs)
- Telemetry opt-in toggle and sandbox mode toggle.
