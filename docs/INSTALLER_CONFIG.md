# Installer Configuration File

This document explains the `--config` option for the installer and the accepted file formats.

Supported formats
- Shell-style `.env` / key=value files (sourced)
- JSON files (`.json`) — simple flat key/value mappings
- YAML files (`.yml` / `.yaml`) — requires `PyYAML` (`pip install pyyaml`)

How to pass a config file

Use the `--config` option to point the installer at a configuration file. Example:

```bash
bash install.sh --config /path/to/panel.env
```

Or when piping from curl:

```bash
PANEL_NON_INTERACTIVE=true PANEL_SAVE_SECRETS=true \
  curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash -s -- --config ./panel.yml
```

Example `.env` (shell-style)

```ini
PANEL_INSTALL_DIR=/opt/panel
PANEL_BRANCH=main
PANEL_DB_TYPE=postgresql
PANEL_DB_HOST=127.0.0.1
PANEL_DB_PORT=5432
PANEL_DB_NAME=panel
PANEL_DB_USER=panel_user
PANEL_DB_PASS=supersecret
PANEL_ADMIN_EMAIL=admin@example.com
PANEL_ADMIN_PASS=adminpass
PANEL_NON_INTERACTIVE=true
PANEL_SAVE_SECRETS=true
```

Example `config.json`

```json
{
  "PANEL_INSTALL_DIR": "/opt/panel",
  "PANEL_DB_HOST": "127.0.0.1",
  "PANEL_DB_PASS": "supersecret",
  "PANEL_ADMIN_EMAIL": "admin@example.com",
  "PANEL_ADMIN_PASS": "adminpass"
}
```

Example `config.yaml` (requires PyYAML)

```yaml
PANEL_INSTALL_DIR: /opt/panel
PANEL_DB_HOST: 127.0.0.1
PANEL_DB_PASS: supersecret
PANEL_ADMIN_EMAIL: admin@example.com
PANEL_ADMIN_PASS: adminpass
```

Supported variables (common)
- `PANEL_INSTALL_DIR` — installation path
- `PANEL_BRANCH` — git branch to install
- `PANEL_DB_TYPE` — (ignored; installer enforces PostgreSQL)
- `PANEL_DB_HOST`, `PANEL_DB_PORT`, `PANEL_DB_NAME`, `PANEL_DB_USER`, `PANEL_DB_PASS`
- `PANEL_ADMIN_EMAIL`, `PANEL_ADMIN_PASS`
- `PANEL_NON_INTERACTIVE` — set to `true` for unattended installs
- `PANEL_SAVE_SECRETS` — if `true`, generated secrets are written to `$INSTALL_DIR/.install_secrets`

Notes
- YAML parsing requires the `PyYAML` Python package. If it's not present, the installer will print an error and exit when attempting to parse YAML.
- When running non-interactively, missing secrets (DB password, admin password) are auto-generated. Use `PANEL_SAVE_SECRETS=true` to have the installer save them to `$INSTALL_DIR/.install_secrets` with `chmod 600`.

Security
- The installer writes sensitive values to `$INSTALL_DIR/.db_credentials` and optionally to `$INSTALL_DIR/.install_secrets` using `chmod 600`. Treat these files as sensitive and remove them once you've stored values securely elsewhere.
