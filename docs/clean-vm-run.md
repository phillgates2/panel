**Clean VM Run**

- **Purpose**: Steps and examples to run the `panel` installer on a clean VM (thorough option). This document provides a cloud-init user-data file, one-shot commands for an already-provisioned VM, verification steps, and troubleshooting guidance.

- **Files added**: `cloud-init/ubuntu-user-data.yaml` — an editable cloud-init user-data example targeting Ubuntu 22.04.

Quick summary (manual run on an existing Ubuntu VM):

1) SSH to VM and update packages:

```bash
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y git curl python3-venv python3-pip
```

2) Run installer non-interactively (SQLite example):

```bash
export PANEL_NON_INTERACTIVE=true
export PANEL_DB_TYPE=sqlite
export PANEL_ADMIN_EMAIL=admin@example.com
export PANEL_ADMIN_PASS='ChangeMeNow!'
export PANEL_INSTALL_DIR=/opt/panel
cd /tmp
git clone https://github.com/phillgates2/panel.git panel-src || (cd panel-src && git pull)
cd panel-src
bash install.sh --non-interactive --sqlite --dir /opt/panel
```

3) For PostgreSQL (managed on same host), set these instead (example):

```bash
export PANEL_DB_TYPE=postgresql
export PANEL_DB_PASS='StrongPostgresPass'
# Optionally provide DB_HOST, DB_PORT, DB_NAME, DB_USER
```

Cloud provider / user-data usage examples

- DigitalOcean: paste the contents of `cloud-init/ubuntu-user-data.yaml` into the "User Data" field when creating a droplet (Ubuntu 22.04). After droplet is provisioned, inspect the console or use `ssh` to view `/var/log/cloud-init-output.log`.

- AWS EC2: use the same file as EC2 user data when launching an instance (Ubuntu 22.04 AMI). Check `cloud-init` logs at `/var/log/cloud-init-output.log`.

Verification steps (after cloud-init or manual run completes)

- Check installer and service logs:

```bash
sudo journalctl -u nginx -n 200 --no-pager
sudo journalctl -u redis -n 200 --no-pager || sudo journalctl -u redis-server -n 200 --no-pager
ls -la /opt/panel
tail -n 100 /opt/panel/logs/panel.log || true
tail -n 100 /opt/panel/logs/worker.log || true
```

- Run the bundled health checker:

```bash
sudo bash /opt/panel/panel-health-check.sh || /opt/panel/panel-health-check.sh
# or
/opt/panel/panel-health-check.sh
```

- Test HTTP endpoints (from within VM):

```bash
curl -f -s http://localhost:8080/health || curl -f -s http://localhost:8080/ || true
```

Troubleshooting tips

- If nginx failed to start:
  - Check `/var/log/nginx/error.log` and `sudo systemctl status nginx`.
  - Ensure default site removed (`/etc/nginx/sites-enabled/default`) on Debian/Ubuntu.

- If Redis failed:
  - `sudo systemctl status redis` or `redis-server --daemonize yes` as fallback.
  - Confirm `redis-cli ping` returns `PONG`.

- If Python packages failed to install (
  - Inspect `/tmp/pip_install.log` if present in the install directory.
  - If building psycopg2 failed on Python 3.13, prefer `psycopg2-binary` or use system PostgreSQL dev packages.

- If the app is running but health checks fail immediately:
  - Expect up to 30 seconds on first-run; logs are the primary source: `/opt/panel/logs/panel.log`.
  - Increase patience: `sleep 30` then `curl` again.

Advanced: run installer in a disposable VM locally using multipass (Ubuntu) or an LXC container; the same cloud-init file is useful for that workflow.

If you want, I can also:
- Produce a matching `cloud-init` for a PostgreSQL-hosted single VM (installs Postgres and configures it), or
- Add an Alpine/dev-container recipe for testing the installer in CI.
