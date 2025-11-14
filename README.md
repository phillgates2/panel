# panel — Game server panel scaffold

This repository contains a minimal scaffold for a game server panel targeted at ET:Legacy with n!tmod. It includes:

- Flask backend with MySQL (user registration/login/forgot password local flow)
- Local captcha generation (image via Pillow, audio via `espeak`)
- Password complexity checks and a client-side strength meter
- A basic RCON client module `rcon_client.py` which sends UDP `rcon` commands (placeholder)
- Utilities: memory watcher, autodeploy script, example `systemd` unit, and `nginx` config

Important notes and next steps

- This is a scaffold — you should review and harden before production.
- Install Python deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- Install system dependencies:

```bash
sudo apt update
sudo apt install -y espeak gdb unzip
```

- Configure MySQL and environment variables (example):

```bash
export PANEL_DB_USER=paneluser
export PANEL_DB_PASS=panelpass
export PANEL_DB_HOST=127.0.0.1
export PANEL_DB_NAME=paneldb
export PANEL_SECRET_KEY="change-this-secret"
```

- Run the app (development):

```bash
python app.py
```

- Production WSGI (gunicorn) + systemd

1. Create a virtualenv and install deps in `/opt/panel` (example):

```bash
python3 -m venv /opt/panel/.venv
source /opt/panel/.venv/bin/activate
pip install -r requirements.txt
```

2. Adjust `deploy/gunicorn.service` `WorkingDirectory` and `PATH` to match your installation, then install:

```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/panel-gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable --now panel-gunicorn.service
```

3. Nginx

Place `deploy/nginx_game_chrisvanek.conf` into `/etc/nginx/sites-available/` and symlink to `sites-enabled`, then reload nginx.

```bash
sudo cp deploy/nginx_game_chrisvanek.conf /etc/nginx/sites-available/game.chrisvanek.conf
sudo ln -s /etc/nginx/sites-available/game.chrisvanek.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

4. Obtain TLS certificate (Certbot, example):

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d game.chrisvanek.com
```

5. Systemd for ET server

Place `deploy/etlegacy.service` into `/etc/systemd/system/` and enable it (adjust ExecStart to your start script):

```bash
sudo cp deploy/etlegacy.service /etc/systemd/system/etlegacy.service
sudo systemctl daemon-reload
sudo systemctl enable --now etlegacy

Server utilities

- Memwatch (periodic core dump when Buffers > 1GB): copy `deploy/memwatch.service` and `deploy/memwatch.timer` to `/etc/systemd/system/` and enable the timer:

```bash
sudo cp deploy/memwatch.service /etc/systemd/system/
sudo cp deploy/memwatch.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now memwatch.timer
```

- Autodeploy (periodic auto-downloader): copy `deploy/autodeploy.service` and `deploy/autodeploy.timer` and enable the timer. Configure `DOWNLOAD_URL` and optionally `DOWNLOAD_CHECKSUM` in `/etc/default/etlegacy` or via environment for the service:

```bash
sudo cp deploy/autodeploy.service /etc/systemd/system/
sudo cp deploy/autodeploy.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now autodeploy.timer
```

Note: The service files assume the scripts are installed at `/opt/panel/scripts/` and that `/etc/default/etlegacy` (optional) can be used to set `DOWNLOAD_URL`, `INSTALL_DIR`, `SERVICE_NAME`, etc. Adjust paths as needed.

Panel user and permissions

- It's safer to run the panel and game server under a dedicated `panel` user instead of `root` or `www-data`.
- Create the user and group, adjust ownership of installed files:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin panel
sudo mkdir -p /opt/panel /opt/etlegacy /var/log/panel
sudo chown -R panel:panel /opt/panel /opt/etlegacy /var/log/panel
```

- The example systemd units `deploy/panel-gunicorn.service` and `deploy/panel-etlegacy.service` run as the `panel` user. Ensure the `panel` user has permissions to execute the server start script and read/write to the configured directories.

```text
# Allow web user (www-data) to run the panel wrapper which validates inputs
www-data ALL=(root) NOPASSWD: /opt/panel/bin/panel-wrapper *
```


Wrapper build & install

The repository includes a small, audited wrapper binary that validates inputs and sanitizes the environment before running `autodeploy` or `memwatch`. Build and install it as follows (on the server):

```bash
# build
cd /path/to/panel/tools
make

# install to /opt/panel/bin (Makefile has an 'install' target that copies and sets permissions)
sudo make install

# ensure the wrapper is owned by root and not writable by others
sudo chown root:root /opt/panel/bin/panel-wrapper
sudo chmod 750 /opt/panel/bin/panel-wrapper
```

The wrapper accepts two commands:
- `panel-wrapper autodeploy [download_url]` — optional `download_url` must start with `http://` or `https://` and will be set as `DOWNLOAD_URL` in the environment passed to the deploy script.
- `panel-wrapper memwatch [pid_file]` — optional `pid_file` must be an absolute path under `/var/run`, `/var/tmp`, or `/tmp` and will be set as `ET_PID_FILE`.

The wrapper logs invocations to `/var/log/panel/panel-wrapper.log` and enforces that the target scripts are owned by `panel` or `root` and are executable.

Asynchronous tasks (RQ + Redis)

- The panel now supports running long-running admin tasks (autodeploy, memwatch) asynchronously using RQ and Redis. Install Redis and start a worker to process jobs.

Install Redis and run a worker:

```bash
sudo apt install redis-server
sudo systemctl enable --now redis
# create and activate the venv, then install dependencies
source /opt/panel/.venv/bin/activate
pip install -r requirements.txt
# run an RQ worker in the background (or as systemd):
python run_worker.py
```

The admin UI enqueues tasks and returns an RQ job id. Check job status with `/admin/job/<job_id>`.

RQ worker systemd unit

To run the RQ worker as the `panel` user via systemd, copy the provided unit file and enable it:

```bash
sudo cp deploy/rq-worker-supervised.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rq-worker-supervised.service
sudo systemctl status rq-worker-supervised.service
```

Adjust `WorkingDirectory` and `Environment` in the unit to match your installation path if you installed the panel elsewhere.

Supervised worker and logs

- A supervised worker unit `deploy/rq-worker-supervised.service` is provided which redirects worker stdout to `/var/log/panel/worker.log`.
- Install it and ensure `/var/log/panel` exists and is owned by `panel`:

```bash
sudo mkdir -p /var/log/panel
sudo chown panel:panel /var/log/panel
sudo cp deploy/rq-worker-supervised.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rq-worker-supervised.service
sudo systemctl status rq-worker-supervised.service
```

Worker health check & timer

- A watch script `tools/check_worker.sh` plus `deploy/check-worker.service` and `deploy/check-worker.timer` will periodically check the worker service, restart it if inactive, and send a Discord alert after repeated failures. Install the timer:

```bash
sudo cp deploy/check-worker.service /etc/systemd/system/
sudo cp deploy/check-worker.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now check-worker.timer
sudo systemctl status check-worker.timer
```

Edit `/opt/panel/tools/check_worker.sh` or environment variables to tune `MAX_FAILS` and `STATE_DIR`.

Discord webhook improvements

- Scripts now post richer embed-style notifications to the configured `PANEL_DISCORD_WEBHOOK`. Set `PANEL_DISCORD_WEBHOOK` in the environment or `/etc/default/etlegacy`.

Log rotation

- A `deploy/panel-logrotate.conf` file is included to rotate `/var/log/panel/*.log` weekly. Install with:

```bash
sudo cp deploy/panel-logrotate.conf /etc/logrotate.d/panel
sudo logrotate -f /etc/logrotate.d/panel
```
```

Security and functional items to finish

- Harden RCON implementation and confirm exact protocol/port for your ET:Legacy + n!tmod build.
- Wire n!tmod to use MySQL backend — the placeholder here is for the panel's user DB.
- Add HTTPS/TLS (Let's Encrypt) for `game.chrisvanek.com` on the nginx layer.
- Add tests, input sanitization, CSRF protection and production WSGI server (gunicorn/uwsgi).
# panel
oz panel

## Release note

The repository's initial scaffold and admin UI were merged into `main` on 2025-11-14.

- Tag: `scaffold-initial-2025-11-14`
- Contents: Flask backend, admin pages, templates, deploy/systemd examples, tests (unit + Playwright E2E placeholder), and CI workflow.

If you cloned the repository before this date, sync with the updated `main`:

```bash
git fetch origin
git checkout main
git reset --hard origin/main
```

To run tests and E2E locally, install dependencies and Playwright browsers:

```bash
python -m pip install -r requirements.txt
python -m playwright install
```


Theme Editor
------------

A lightweight Theme Editor is available in the admin UI for system administrators. It allows editing a single CSS file (`static/css/custom_theme.css`) that is applied site-wide.

- URL: `/admin/theme` (requires a `system_admin` user)
- The editor provides a textarea with the current CSS and saves changes to `static/css/custom_theme.css`.
- Changes take effect immediately after saving.

If you'd prefer multi-theme support or database-stored themes, I can extend the editor to support previews and named themes.

