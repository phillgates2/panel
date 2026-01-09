<div align="center">

# Panel

Enterprise game server management platform — Cloud-ready, secure, and observable.

[![CI/CD](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml)
[![Security](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml)
[![Release](https://img.shields.io/github/v/release/phillgates2/panel)](https://github.com/phillgates2/panel/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

Panel is a modern platform for running and managing multiplayer game servers at scale. It includes:
- Orchestration (RCON, server templates, provisioning)
- Secure auth (OAuth2/OIDC, JWT) and RBAC
- Observability (Prometheus metrics, Grafana dashboards, structured logs)
- A GUI installer that sets up PostgreSQL, Redis, Nginx, and a Python environment
- DevOps-ready deployment via Docker Compose

Use Panel to host, monitor, and operate servers with enterprise-grade features.

---

## Getting the Installer and Files

You can install Panel using the GUI installer or via Docker/manual setup.

### 1) Download the repository
```bash
# Clone the repo
git clone https://github.com/phillgates2/panel.git
cd panel
```

### 2) GUI Installer (recommended)
Requirements: Python 3.10+, pip.
```bash
pip install PySide6 keyring psycopg2-binary
python -m tools.installer.gui
```
Features:
- Wizard (preflight → config → install → health → summary)
- Role-based presets (dev/staging/prod)
- Secrets via OS keyring
- Advanced logs (filter/search/severity, redacted export)
- Diagnostics (tail common logs), crash recovery (state rollback)
- Telemetry opt-in and sandbox simulation mode

Installer files live in `tools/installer/`.

### 3) Docker Compose (fastest setup)
```bash
# From the repo root
docker-compose up -d
# App at http://localhost:8080
```
Compose variants:
- `docker-compose.yml` — base stack
- `docker-compose.monitoring.yml` — Prometheus/Grafana

### 4) Manual installation (venv)
```bash
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements/requirements.txt
cp .env.example .env
# edit .env with your settings
flask db upgrade
python app.py
```

---

## Quick Start

After installation:
- Access the app: `http://localhost:8080` (or your domain)
- Sign in with the admin user configured during setup
- Create servers via Servers → Add New
- Visit `/metrics` for Prometheus metrics

---

## Key Features

- Game servers: multi-game, RCON, templates, health checks
- Community: forum/CMS, real-time chat, roles
- Security: OAuth2/OIDC, JWT, RBAC, CSP/HSTS, rate limiting
- Analytics: app metrics at `/metrics`, Grafana dashboards
- Operations: backups, Alembic migrations, structured logging

---

## Architecture

- Backend: Python (Flask), SQLAlchemy
- Data: PostgreSQL, Redis
- Frontend: Bootstrap 5, Jinja2
- Monitoring: Prometheus, Grafana
- Deploy: Docker Compose

See `docs/README.md` for the detailed diagram and component guides.

---

## Configuration

Configure via environment (`.env`). Example:
```env
FLASK_ENV=production
DATABASE_URL=postgresql://panel_user:password@localhost:5432/panel_db
REDIS_URL=redis://localhost:6379/0
PROMETHEUS_ENABLED=true
```
More in `config/README.md`.

---

## Installer Highlights

- Preflight checks and configuration validation
- Role-based presets and wizard flow
- Secrets saved to OS keyring
- Advanced logging (filters/search/severity, redaction)
- Diagnostics (tail nginx/postgres logs)
- Crash recovery (state rollback)
- Telemetry opt-in and sandbox mode

Docs: `tools/installer/README.md` and `docs/INSTALLER_GUIDE.md`.

---

## Monitoring & Troubleshooting

### Health & Metrics
- Health endpoints: `GET /health`, `GET /health/detailed`
- Metrics endpoint: `GET /metrics`

### Logs
- App logs: see your configured logging directory or the GUI installer Logs tab
- Nginx logs: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- PostgreSQL logs: typically `/var/log/postgresql/*.log`

### Common Panel Issues & Fixes
- Port conflict on 8080/80/443
  - Check with: `netstat -tlnp | grep 8080` (Linux) or `Get-NetTCPConnection -LocalPort 8080` (Windows)
  - Change `PANEL_PORT` or stop the conflicting service
- Database connection failure
  - Verify PostgreSQL: `sudo systemctl status postgresql`
  - Test: `psql -U panel_user -d panel_db -h localhost -c "SELECT 1"`
  - Check `DATABASE_URL` in `.env`
- Redis not reachable
  - `redis-cli ping` should return `PONG`
  - Check `REDIS_URL`
- Health check fails
  - Ensure app running: `ps aux | grep app.py` (Linux)
  - Review logs for stack traces and config errors

### Installer Troubleshooting
- GUI won’t start
  - Ensure PySide6 installed: `pip show PySide6`
  - Try `python -m tools.installer.gui` from repo root
- Preflight reports ports in use
  - Free the ports or adjust panel/nginx ports in Settings
- Elevation/Admin required errors
  - Run installer with admin/sudo or enable elevation
- Crash recovery needed
  - Use the GUI “Crash Recovery” to rollback recorded actions
- Secrets storage issues
  - Install `keyring` and ensure OS keychain is accessible

---

## Development

```bash
pip install -r requirements/requirements-dev.txt
make lint format test
```
Contribution guide: `docs/CONTRIBUTING.md`.

---

## Roadmap

Planned improvements: cloud installers, deeper game integrations, workflow automation.
Track progress in `docs/README.md` and issues.

---

## License

MIT © Contributors. See `LICENSE`.

---

## Links

- Docs index: `docs/README.md`
- Installer guide: `docs/INSTALLER_GUIDE.md`
- Issues: https://github.com/phillgates2/panel/issues
- Discussions: https://github.com/phillgates2/panel/discussions
