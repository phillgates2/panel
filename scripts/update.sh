#!/usr/bin/env bash
set -euo pipefail

# Update/migration script for Panel app
# Detects existing installation and updates dependencies or runs migrations

HERE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$HERE_DIR/.." && pwd)"
cd "$ROOT_DIR"

confirm() {
  local msg="$1"; shift
  local def="${1:-Y}"; shift || true
  local ans
  read -rp "$msg [$def]: " ans || true
  ans="${ans:-$def}"
  case "$ans" in
    y|Y|yes|YES) return 0;;
    *) return 1;;
  esac
}

echo "=== Panel Update/Migration Script ==="

# Check for existing installation
if [[ ! -d .venv ]]; then
  echo "Error: No virtualenv found at .venv"
  echo "Run scripts/install.sh to perform initial installation."
  exit 1
fi

if [[ ! -f scripts/env.sh ]]; then
  echo "Error: No environment file found at scripts/env.sh"
  echo "Run scripts/install.sh to perform initial installation."
  exit 1
fi

echo "Detected existing installation."
echo ""

# Activate virtualenv
# shellcheck disable=SC1091
source .venv/bin/activate

# Update pip and wheel
if confirm "Update pip and wheel?" Y; then
  pip install -U pip wheel
fi

# Update dependencies
if confirm "Update Python dependencies from requirements.txt?" Y; then
  echo "Updating dependencies..."
  pip install -r requirements.txt --upgrade
  echo "✓ Dependencies updated"
fi

# Update Playwright browsers
if confirm "Update Playwright browsers?" N; then
  python -m playwright install chromium || echo "Warning: Playwright update failed" >&2
fi

# Run database migrations
if confirm "Run database migrations (create new tables if needed)?" Y; then
  # shellcheck disable=SC1091
  source scripts/env.sh
  
  echo "Running database migrations..."
  python3 - <<PY
from app import app, db

with app.app_context():
    # Create all tables (existing tables won't be affected)
    db.create_all()
    print("✓ Database migrations complete")
PY
fi

# Reload systemd services if they exist
if command -v systemctl >/dev/null 2>&1; then
  RESTART_SERVICES=()
  
  if systemctl list-unit-files | grep -q panel-gunicorn.service; then
    if systemctl is-active --quiet panel-gunicorn.service; then
      RESTART_SERVICES+=(panel-gunicorn.service)
    fi
  fi
  
  if systemctl list-unit-files | grep -q rq-worker-supervised.service; then
    if systemctl is-active --quiet rq-worker-supervised.service; then
      RESTART_SERVICES+=(rq-worker-supervised.service)
    fi
  fi
  
  if [[ ${#RESTART_SERVICES[@]} -gt 0 ]]; then
    if confirm "Restart active services: ${RESTART_SERVICES[*]}?" Y; then
      for svc in "${RESTART_SERVICES[@]}"; do
        sudo systemctl restart "$svc"
        echo "✓ Restarted $svc"
      done
    fi
  fi
fi

echo ""
echo "Update complete!"
echo ""
echo "Next steps:"
echo "  - Review CHANGELOG.md for any breaking changes"
echo "  - Run tests: pytest -q"
echo "  - Monitor logs for any issues"
