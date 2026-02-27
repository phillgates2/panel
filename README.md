# Panel

Panel is a Flask-based control panel for managing game servers and related operational tooling.

[![CI/CD](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml)
[![Security](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What’s In Here

- Web app: Flask + SQLAlchemy
- Datastores: PostgreSQL (required), Redis (optional but recommended)
- Installers: GUI, CLI, SSH (wizard + non-interactive flags)
- Deploy options: Docker Compose or direct-venv

Important: SQLite is not supported. Some legacy docs/scripts in this repo still mention SQLite; treat those as historical and not part of the supported setup.

## Quick Start (Recommended)

```bash
git clone https://github.com/phillgates2/panel.git
cd panel
```

### Option A: GUI installer (desktop environment)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/requirements-gui.txt

# Default entrypoint prefers GUI when available
python -m tools.installer
```

GUI notes:

- PostgreSQL-only DB configuration (host/port/dbname/user/password)
- Supports `search_path` (schema) and Postgres SSL options
- Installs “extra features” dependencies by default (see “Extras”)

### Option B: CLI installer (scriptable)

```bash
python3 -m tools.installer --cli --help

# Dry-run
python3 -m tools.installer --cli install \
  --domain example.com \
  --components postgres,redis,nginx,python \
  --dry-run --json
```

Database flags (PostgreSQL only):

```bash
printf '%s' "$PANEL_DB_PASS" | python3 -m tools.installer --cli install \
  --domain example.com \
  --components postgres,redis,nginx,python \
  --db-host 127.0.0.1 --db-port 5432 --db-name paneldb --db-user paneluser \
  --db-password-stdin \
  --db-search-path "public" \
  --db-sslmode require \
  --json
```

### Option C: SSH installer (terminal + wizard)

```bash
# Wizard (prompts for DB/search_path/SSL)
python3 -m tools.installer --ssh wizard

# Or non-interactive
python3 -m tools.installer --ssh install \
  --domain example.com \
  --components postgres,redis,nginx,python \
  --db-uri 'postgresql+psycopg2://user:pass@db:5432/paneldb?sslmode=require' \
  --db-search-path public \
  --json
```

Notes:

- CLI/SSH modes can be selected by default with `PANEL_INSTALLER_MODE=cli` or `PANEL_INSTALLER_MODE=ssh`.
- CLI/SSH installers stream progress lines prefixed with `PROGRESS:` and can emit a final JSON summary with `--json`.
- On Linux hosts without a service manager (common in LXC containers), the installer can start Panel via a detached background process and logs to `/var/log/panel/app.out` when possible.

## Docker Compose

```bash
docker compose up -d
# App at http://localhost:8080
```

Compose variants:

- `docker-compose.yml` (base)
- `docker-compose.monitoring.yml` (Prometheus/Grafana)

## Manual (venv)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/requirements.txt

cp .env.example .env
# Edit .env (see config/README.md)

python -m alembic upgrade head
python app.py
```

## Configuration

Panel is configured via environment variables (local `.env`, or `/etc/panel/panel.env` when installed).

PostgreSQL-only options:

```env
# Preferred: full URL (supports SSL query params)
DATABASE_URL=postgresql+psycopg2://paneluser:strong_password@127.0.0.1:5432/paneldb?sslmode=require

# Or parts (installer writes these too)
PANEL_DB_HOST=127.0.0.1
PANEL_DB_PORT=5432
PANEL_DB_NAME=paneldb
PANEL_DB_USER=paneluser
PANEL_DB_PASS=strong_password

# Schema/search_path
PANEL_DB_SEARCH_PATH=public
```

More details: `config/README.md`.

## Extras (Advanced Features)

Some functionality depends on optional/heavier dependencies in:

- `requirements/requirements-extras.txt` (AI/ML/cloud/blockchain/monitoring/realtime)
- `requirements/requirements-ml.txt` (TensorFlow)

GUI behavior:

- The GUI installer attempts to install these extras automatically.
- If extras installation fails, the GUI install fails (strict mode).
- On musl-based systems (e.g., Alpine), ML extras may be skipped because TensorFlow wheels are often unavailable.

## Troubleshooting

Common checks:

- App logs: `/var/log/panel/app.out` (installer background-start) or the installer log output
- Nginx logs: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- Postgres connectivity:

```bash
psql -h 127.0.0.1 -p 5432 -U paneluser -d paneldb -c 'SELECT 1'
```

Installer docs:

- `tools/installer/README.md`
- `docs/INSTALLER_GUIDE.md`

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements/requirements-test.txt
python -m pytest -q
```

Docs index: `docs/README.md`.

## License

MIT. See `LICENSE`.
