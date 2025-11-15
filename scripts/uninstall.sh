#!/usr/bin/env bash
set -euo pipefail

# Uninstall script for Panel app
# Removes virtualenv, instance data, env file, and optionally services

HERE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$HERE_DIR/.." && pwd)"
cd "$ROOT_DIR"

confirm() {
  local msg="$1"; shift
  local def="${1:-N}"; shift || true
  local ans
  read -rp "$msg [$def]: " ans || true
  ans="${ans:-$def}"
  case "$ans" in
    y|Y|yes|YES) return 0;;
    *) return 1;;
  esac
}

has_cmd() { command -v "$1" >/dev/null 2>&1; }
SUDO=""; if [[ ${EUID:-$(id -u)} -ne 0 ]] && has_cmd sudo; then SUDO="sudo"; fi

echo "=== Panel Uninstall ==="
echo "This will remove:"
echo "  - Python virtualenv (.venv)"
echo "  - Environment file (scripts/env.sh)"
echo "  - Instance directory (instance/)"
echo "  - Git hooks (.git/hooks/pre-commit)"
echo ""

if ! confirm "Continue with uninstall?" N; then
  echo "Uninstall cancelled."
  exit 0
fi

# Remove virtualenv
if [[ -d .venv ]]; then
  echo "Removing .venv..."
  rm -rf .venv
fi

# Remove env file
if [[ -f scripts/env.sh ]]; then
  echo "Removing scripts/env.sh..."
  rm -f scripts/env.sh
fi

# Remove instance directory
if confirm "Remove instance/ directory (contains database and uploads)?" N; then
  echo "Removing instance/..."
  rm -rf instance/
fi

# Remove git hooks
if [[ -f .git/hooks/pre-commit ]]; then
  if confirm "Remove git pre-commit hook?" Y; then
    echo "Removing .git/hooks/pre-commit..."
    rm -f .git/hooks/pre-commit
  fi
fi

# Remove Docker files
if [[ -f docker-compose.yml ]] || [[ -f Dockerfile ]]; then
  if confirm "Remove Docker files (docker-compose.yml, Dockerfile)?" N; then
    rm -f docker-compose.yml Dockerfile
    echo "Removed Docker files"
  fi
fi

# Remove GitHub Actions workflow
if [[ -f .github/workflows/ci.yml ]]; then
  if confirm "Remove GitHub Actions workflow?" N; then
    rm -f .github/workflows/ci.yml
    echo "Removed .github/workflows/ci.yml"
  fi
fi

# Remove systemd services
if has_cmd systemctl; then
  if systemctl list-unit-files | grep -q panel-gunicorn.service; then
    if confirm "Stop and remove panel-gunicorn systemd service?" N; then
      $SUDO systemctl stop panel-gunicorn.service || true
      $SUDO systemctl disable panel-gunicorn.service || true
      $SUDO rm -f /etc/systemd/system/panel-gunicorn.service
      $SUDO systemctl daemon-reload
      echo "Removed panel-gunicorn.service"
    fi
  fi
  
  if systemctl list-unit-files | grep -q rq-worker-supervised.service; then
    if confirm "Stop and remove rq-worker-supervised systemd service?" N; then
      $SUDO systemctl stop rq-worker-supervised.service || true
      $SUDO systemctl disable rq-worker-supervised.service || true
      $SUDO rm -f /etc/systemd/system/rq-worker-supervised.service
      $SUDO systemctl daemon-reload
      echo "Removed rq-worker-supervised.service"
    fi
  fi
fi

# Remove nginx config
if [[ -d /etc/nginx/sites-enabled ]]; then
  NGINX_CONFIGS=$(find /etc/nginx/sites-enabled -name "panel-*.conf" 2>/dev/null || true)
  if [[ -n "$NGINX_CONFIGS" ]]; then
    if confirm "Remove nginx configuration?" N; then
      for conf in $NGINX_CONFIGS; do
        $SUDO rm -f "$conf"
        # Remove from sites-available too
        AVAILABLE_CONF="/etc/nginx/sites-available/$(basename "$conf")"
        $SUDO rm -f "$AVAILABLE_CONF"
      done
      $SUDO nginx -t && $SUDO systemctl reload nginx || true
      echo "Removed nginx configuration"
    fi
  fi
fi

# Remove backup script
if [[ -f scripts/backup_db.sh ]]; then
  if confirm "Remove backup script?" Y; then
    rm -f scripts/backup_db.sh
    echo "Removed scripts/backup_db.sh"
  fi
fi

# Remove log directory
if [[ -d /var/log/panel ]]; then
  if confirm "Remove /var/log/panel directory?" N; then
    $SUDO rm -rf /var/log/panel
    echo "Removed /var/log/panel"
  fi
fi

echo ""
echo "Uninstall complete."
echo "Note: System packages (python3, redis-server, etc.) were not removed."
echo "Note: MySQL database '$DB_NAME' was not dropped (if it exists)."
