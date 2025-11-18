**Alpine Dev / Quick Test Recipe**

This is a short recipe to test the installer inside a disposable Alpine container. It's intended for quick local validation — the installer expects `systemctl` for some service starts and may need adaptation for production.

Steps (local Docker):

1) Run an interactive Alpine container and install minimal tools:

```bash
docker run --rm -it --name panel-test alpine:3.18 /bin/sh
apk update
apk add --no-cache bash git curl python3 py3-pip py3-virtualenv build-base libffi-dev openssl-dev postgresql-dev
```

2) Clone repo and run installer (SQLite mode recommended for quick tests):

```bash
git clone https://github.com/phillgates2/panel.git panel-src
cd panel-src
export PANEL_NON_INTERACTIVE=true
export PANEL_DB_TYPE=sqlite
export PANEL_ADMIN_EMAIL=admin@example.com
export PANEL_ADMIN_PASS='ChangeMeNow!'
export PANEL_INSTALL_DIR=/tmp/panel-install
bash install.sh --non-interactive --sqlite --dir /tmp/panel-install
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

- If Python packages fail to build (psycopg2 on Alpine), prefer `PANEL_DB_TYPE=sqlite` or install `psycopg2` build deps (`postgresql-dev` and `gcc` are included above).

If you want, I can also create a ready-to-use `.devcontainer` for VS Code that uses Ubuntu 22.04 for easier parity with the installer.
