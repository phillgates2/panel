# Panel Installer Guide (GUI Only)

The interactive shell installer has been removed. Use the GUI installer.

## Quick Start

```bash
pip install PySide6 keyring
python -m tools.installer.gui
```

## Features
- Preflight checks and configuration validation
- Wizard flow (preflight ? config ? install ? health ? summary)
- Role-based presets (dev/staging/prod)
- Secrets stored via OS keyring
- Advanced logs (filter, search, severity, redacted export)
- Diagnostics (tail common component logs)
- Crash recovery (state-based rollback)
- Telemetry opt-in and sandbox mode toggles

## Headless/Automation
For servers without GUI:
- Prefer Docker Compose or manual setup documented in `README.md` and `config/README.md`.

## Uninstall
Use the GUI uninstall flow with `Preserve data` toggle.

## Support
- Issues: https://github.com/phillgates2/panel/issues
- Docs index: `docs/README.md`
