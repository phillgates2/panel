Notes:

- The state file path defaults to `/var/lib/panel_installer/state.json` when running as root, else `installer_state.json` in the CWD. This allows sandbox testing when not elevated.
- `state.rollback(...)` performs actions in reverse order and now preserves actions that failed to uninstall so operators can retry or inspect them. On success the corresponding action is removed from the state file; on failure it is left in place.
- Dry-run mode reports what would be done and does not mutate the state file.
- The uninstall functions default to `preserve_data=True` which prevents destructive removal of databases and other data by default.
