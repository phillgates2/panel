**Alpine Dev / Quick Test Recipe**

This is a short recipe to test the installer inside a disposable Alpine container. It's intended for quick local validation — the installer expects `systemctl` for some service starts and may need adaptation for production.

Important: Panel is PostgreSQL-only. SQLite-based quick-test modes referenced in older docs are legacy and no longer supported by the application/runtime.

Steps (local Docker):

1) Run an interactive Alpine container and install minimal tools:

```bash
docker run --rm -it --name panel-test alpine:3.18 /bin/sh
apk update
apk add --no-cache bash git curl python3 py3-pip py3-virtualenv build-base libffi-dev openssl-dev postgresql-dev
```

2) Clone repo and run the installer (PostgreSQL required):

```bash
git clone https://github.com/phillgates2/panel.git panel-src
cd panel-src
export PANEL_NON_INTERACTIVE=true
export PANEL_ADMIN_EMAIL=admin@example.com
export PANEL_ADMIN_PASS='ChangeMeNow!'
export PANEL_INSTALL_DIR=/tmp/panel-install

# Point Panel at a reachable PostgreSQL instance.
# Example (replace host/user/pass/db):
export DATABASE_URL='postgresql+psycopg2://paneluser:panelpass@YOUR_DB_HOST:5432/paneldb'

# Legacy install.sh flows may still exist, but the supported path is the Python installer entrypoint:
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/requirements.txt
python -m tools.installer --cli install --domain example.com --components redis,nginx,python --dry-run
```

Notes & caveats:
- Alpine doesn't use systemd by default; `install.sh` tries `systemctl` to start Redis/Nginx. For quick local tests, you can run Redis manually (`redis-server --daemonize yes`) or skip service checks by setting `PANEL_SKIP_DEPS=true` and manually installing dependencies.
- To test the web app quickly, start the panel manually inside the container:

```bash
cd /tmp/panel-install
python3 -m venv venv
source venv/bin/activate
python3 app.py
# In another shell: curl http://localhost:8080/
```

- If Python packages fail to build (psycopg2 on Alpine), install the build deps (`postgresql-dev`, `gcc`, etc.) or use a glibc-based environment for closer production parity.

If you want, I can also create a ready-to-use `.devcontainer` for VS Code that uses Ubuntu 22.04 for easier parity with the installer.
