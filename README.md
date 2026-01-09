<div align="center">



# Panel



Enterprise game server management. Cloud-ready. Secure. Observable.



[![CI/CD](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml)
[![Security](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml)
[![Release](https://img.shields.io/github/v/release/phillgates2/panel)](https://github.com/phillgates2/panel/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)



</div>

---



## What is Panel?



Panel is a modern platform for running and managing multiplayer game servers. It ships with:

 

- Game server orchestration (RCON, templates, provisioning)

- Secure Auth (OAuth2/OIDC, JWT) and RBAC

- Observability (Prometheus metrics, Grafana dashboards, structured logs)

- Installer (GUI/CLI) that sets up Postgres, Redis, Nginx, Python env

- DevOps-ready deployment with Docker Compose

Use it to host, monitor, and operate servers with enterprise-grade features.



---



## Quick start



Pick one of the following.

  

- Interactive installer

  ```bash

  # GUI

  python -m tools.installer.gui
  
  # CLI

  python -m tools.installer.cli install --domain example.com --components postgres,redis,nginx,python

  ```



- Docker Compose

  ```bash

  git clone https://github.com/phillgates2/panel.git

  cd panel

  docker-compose up -d

  # App: http://localhost:8080

  ```



- Manual (venv)

  ```bash

  python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate

  pip install -r requirements/requirements.txt

  cp .env.example .env && edit .env

  flask db upgrade

  python app.py

  ```



---



## Key features



- Game servers: multi-game, RCON, templates, health checks

- Community: forum/CMS, real-time chat, roles

- Security: OAuth2/OIDC, JWT, RBAC, CSP/HSTS, rate limiting

- Analytics: app metrics at `/metrics`, Grafana dashboards

- Operations: backups, migrations (Alembic), structured logging



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



Configure via environment variables (`.env`). Example:

```env

FLASK_ENV=production

DATABASE_URL=postgresql://panel_user:password@localhost:5432/panel_db

REDIS_URL=redis://localhost:6379/0

PROMETHEUS_ENABLED=true

```

More in `config/README.md`.



---



## Installer highlights



The installer aligns GUI and CLI options:

- Install: `--domain`, `--components postgres,redis,nginx,python`, `--dry-run`

- Uninstall: `--preserve-data`, `--dry-run`

- GUI extras: presets (dev/staging/prod), wizard mode, i18n, secrets via OS keyring, logs with filters/search.

Docs: `tools/installer/README.md`.



---



## Monitoring & troubleshooting



- Health: `GET /health`, `GET /health/detailed`

- Metrics: `GET /metrics`

- Logs: structured; advanced filtering in GUI

- Dashboards: see `docs/MONITORING_DASHBOARD_README.md`

- Troubleshooting: `docs/TROUBLESHOOTING.md`



---



## Security



Built-in best practices:

- OAuth2/OIDC, JWT, RBAC

- Hardened headers (CSP, HSTS), rate limiting

- Audit logging, GDPR helpers



Checklist: `docs/SECURITY_HARDENING_README.md`.



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

- Issues: https://github.com/phillgates2/panel/issues

- Discussions: https://github.com/phillgates2/panel/discussions
