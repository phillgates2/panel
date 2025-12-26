Notes:
- The state file path defaults to `/var/lib/panel_installer/state.json` when running as root, else `installer_state.json` in the CWD. This allows sandbox testing when not elevated.
- `state.rollback(...)` performs actions in reverse order and clears the state file after attempting rollback. This is a best-effort approach; future improvements should allow partial rollbacks and leave state when errors occur.
- The uninstall functions default to `preserve_data=True` which prevents destructive removal of databases and other data by default.
