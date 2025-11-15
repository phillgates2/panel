#!/usr/bin/env bash
set -euo pipefail

# Interactive installer for the Panel app
# - Creates a Python virtualenv and installs requirements
# - Writes an env file with configuration
# - Initializes the database and optionally creates an admin user
# - Sets up local instance directories
# - Optionally configures production services (nginx, systemd, SSL)

HERE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$HERE_DIR/.." && pwd)"
cd "$ROOT_DIR"

# Parse flags
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1; shift;;
    *) ;;
  esac
done

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "=== DRY RUN MODE - No changes will be made ==="
fi

prompt() {
  local msg="$1"; shift
  local def="${1-}"; shift || true
  local var
  if [[ -n "$def" ]]; then
    read -rp "$msg [$def]: " var || true
    echo "${var:-$def}"
  else
    read -rp "$msg: " var || true
    echo "$var"
  fi
}

prompt_secret() {
  local msg="$1"
  local var
  read -rsp "$msg: " var || true
  echo
  echo "$var"
}

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

# ----- Apt helpers -----
has_cmd() { command -v "$1" >/dev/null 2>&1; }
apt_available() { has_cmd apt; }
SUDO=""; if [[ ${EUID:-$(id -u)} -ne 0 ]] && has_cmd sudo; then SUDO="sudo"; fi
APT_UPDATED=0
apt_update_once() { if [[ $APT_UPDATED -eq 0 ]]; then [[ "$DRY_RUN" -eq 0 ]] && $SUDO apt update || echo "[DRY RUN] Would run: apt update"; APT_UPDATED=1; fi }
ensure_apt_pkgs() {
  # usage: ensure_apt_pkgs pkg1 pkg2 ...
  local missing=()
  for p in "$@"; do
    if ! dpkg -s "$p" >/dev/null 2>&1; then
      missing+=("$p")
    fi
  done
  if ((${#missing[@]})); then
    echo "Installing packages: ${missing[*]}"
    apt_update_once
    if [[ "$DRY_RUN" -eq 0 ]]; then
      $SUDO apt install -y "${missing[@]}"
    else
      echo "[DRY RUN] Would install: ${missing[*]}"
    fi
  else
    echo "All requested packages already installed."
  fi
}

# Pre-flight: ensure core tools via apt if missing
if ! has_cmd python3; then
  if apt_available; then
    echo "python3 not found. Attempting to install via apt..."
    ensure_apt_pkgs python3
  else
    echo "python3 not found and apt not available. Please install Python 3." >&2
    exit 1
  fi
fi

# 1) Environment selection
ENVIRONMENT="$(prompt "Environment (dev/prod)" "dev")"
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
  echo "Invalid environment: $ENVIRONMENT (expected 'dev' or 'prod')" >&2
  exit 1
fi

VENVDIR="$(prompt "Virtualenv directory" ".venv")"
REDIS_URL_DEFAULT="redis://127.0.0.1:6379/0"
REDIS_URL="$(prompt "Redis URL" "$REDIS_URL_DEFAULT")"

# System dependency checks and installation
if apt_available && confirm "Check and install missing system dependencies via apt?" Y; then
  # Essential for runtime and script features
  REQ_PKGS=(python3 python3-venv unzip espeak)
  # Helpful utilities used in repo/scripts and optional services
  OPT_PKGS=(gdb redis-server make)
  ensure_apt_pkgs "${REQ_PKGS[@]}" "${OPT_PKGS[@]}"
else
  echo "Skipping automatic system dependency installation."
fi

# Generate a secret key
SECRET_KEY="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"

USE_SQLITE=1
SQLITE_URI="sqlite:///panel_dev.db"
DB_USER="paneluser"
DB_PASS="panelpass"
DB_HOST="127.0.0.1"
DB_NAME="paneldb"
DISCORD_WEBHOOK=""

if [[ "$ENVIRONMENT" == "prod" ]]; then
  USE_SQLITE=0
  DB_USER="$(prompt "MariaDB user" "$DB_USER")"
  DB_PASS="$(prompt_secret "MariaDB password")"
  DB_HOST="$(prompt "MariaDB host" "$DB_HOST")"
  DB_NAME="$(prompt "MariaDB database name" "$DB_NAME")"
  
  # Optional: Create MariaDB database and user
  if confirm "Create MariaDB database and user (requires MariaDB root access)?" N; then
    DB_ROOT_PASS="$(prompt_secret "MariaDB root password")"
    if [[ "$DRY_RUN" -eq 0 ]]; then
      mysql -h "$DB_HOST" -u root -p"$DB_ROOT_PASS" <<SQL || {
        echo "Warning: MariaDB database creation failed. You may need to create it manually." >&2
      }
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';
FLUSH PRIVILEGES;
SQL
      echo "MariaDB database '$DB_NAME' and user '$DB_USER' created."
    else
      echo "[DRY RUN] Would create MariaDB database '$DB_NAME' and user '$DB_USER'"
    fi
  fi
else
  # dev: allow overriding SQLite URI
  SQLITE_URI="$(prompt "SQLite URI" "$SQLITE_URI")"
fi

# Optional Discord webhook
if confirm "Configure Discord webhook for notifications?" N; then
  DISCORD_WEBHOOK="$(prompt "Discord webhook URL" "")"
fi

CREATE_ADMIN=0
if confirm "Create an initial system admin user now?" N; then
  CREATE_ADMIN=1
  ADMIN_EMAIL="$(prompt "Admin email" "admin@example.com")"
  ADMIN_FIRST="$(prompt "Admin first name" "Admin")"
  ADMIN_LAST="$(prompt "Admin last name" "User")"
  ADMIN_DOB="$(prompt "Admin date of birth (YYYY-MM-DD)" "2000-01-01")"
  while true; do
    ADMIN_PASS1="$(prompt_secret "Admin password")"
    ADMIN_PASS2="$(prompt_secret "Confirm admin password")"
    if [[ "$ADMIN_PASS1" == "$ADMIN_PASS2" && -n "$ADMIN_PASS1" ]]; then
      break
    fi
    echo "Passwords do not match or empty. Please try again." >&2
  done
fi

# 2) Create virtualenv and install requirements
if [[ "$DRY_RUN" -eq 0 ]]; then
  python3 -m venv "$VENVDIR"
  # shellcheck disable=SC1090
  source "$VENVDIR/bin/activate"
  pip install -U pip wheel
  pip install -r requirements.txt
else
  echo "[DRY RUN] Would create virtualenv at $VENVDIR and install requirements"
fi

# 2.5) Optionally install Playwright browsers for E2E tests
INSTALL_PLAYWRIGHT=0
if confirm "Install Playwright Chromium for E2E tests?" N; then
  INSTALL_PLAYWRIGHT=1
  echo "Installing Playwright Chromium..."
  if [[ "$DRY_RUN" -eq 0 ]]; then
    python -m playwright install chromium || {
      echo "Warning: Playwright install failed. E2E tests may not run." >&2
    }
  else
    echo "[DRY RUN] Would install Playwright Chromium"
  fi
fi

# 2.6) Check Redis connectivity
echo "Checking Redis connection..."
if [[ "$DRY_RUN" -eq 0 ]]; then
  if has_cmd redis-cli; then
    if redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
      echo "✓ Redis is accessible at $REDIS_URL"
    else
      echo "⚠ Redis is not accessible at $REDIS_URL"
      if has_cmd systemctl && systemctl list-unit-files | grep -q redis-server.service; then
        if confirm "Start Redis service now?" Y; then
          $SUDO systemctl start redis-server || echo "Failed to start redis-server" >&2
          $SUDO systemctl enable redis-server || true
        fi
      else
        echo "Tip: Install and start Redis with: sudo apt install redis-server && sudo systemctl start redis-server"
      fi
    fi
  else
    echo "redis-cli not found. Install redis-tools to check connectivity."
  fi
else
  echo "[DRY RUN] Would check Redis connectivity"
fi

# 3) Create instance directories
if [[ "$DRY_RUN" -eq 0 ]]; then
  mkdir -p instance/theme_assets
else
  echo "[DRY RUN] Would create instance/theme_assets"
fi

# 3.5) Setup log directory for production
if [[ "$ENVIRONMENT" == "prod" ]]; then
  if confirm "Create /var/log/panel directory?" Y; then
    if [[ "$DRY_RUN" -eq 0 ]]; then
      $SUDO mkdir -p /var/log/panel
      # If panel user exists, set ownership
      if id -u panel >/dev/null 2>&1; then
        $SUDO chown -R panel:panel /var/log/panel
      else
        echo "Note: 'panel' user not found. You may need to create it and set ownership later."
      fi
    else
      echo "[DRY RUN] Would create /var/log/panel"
    fi
  fi
fi

# 4) Write environment file
ENV_FILE="scripts/env.sh"
ENV_CONTENT="#!/usr/bin/env bash
# Auto-generated by scripts/install.sh
export PANEL_SECRET_KEY=\"$SECRET_KEY\"
export PANEL_REDIS_URL=\"$REDIS_URL\""

if [[ "$USE_SQLITE" -eq 1 ]]; then
  ENV_CONTENT+="
export PANEL_USE_SQLITE=1
export PANEL_SQLITE_URI=\"$SQLITE_URI\""
else
  ENV_CONTENT+="
export PANEL_DB_USER=\"$DB_USER\"
export PANEL_DB_PASS=\"$DB_PASS\"
export PANEL_DB_HOST=\"$DB_HOST\"
export PANEL_DB_NAME=\"$DB_NAME\""
fi

if [[ -n "$DISCORD_WEBHOOK" ]]; then
  ENV_CONTENT+="
export PANEL_DISCORD_WEBHOOK=\"$DISCORD_WEBHOOK\""
fi

if [[ "$DRY_RUN" -eq 0 ]]; then
  echo "$ENV_CONTENT" > "$ENV_FILE"
  chmod +x "$ENV_FILE" || true
  echo "Wrote $ENV_FILE"
else
  echo "[DRY RUN] Would write $ENV_FILE with:"
  echo "$ENV_CONTENT"
fi

# 5) Initialize database and optionally create admin
# shellcheck disable=SC1090
if [[ "$DRY_RUN" -eq 0 ]]; then
  source "$ENV_FILE"
  python3 - <<PY
from datetime import date
from app import app, db, User

with app.app_context():
    db.create_all()
    print("Database tables created.")
PY
else
  echo "[DRY RUN] Would initialize database"
fi

if [[ "$CREATE_ADMIN" -eq 1 ]]; then
if [[ "$DRY_RUN" -eq 0 ]]; then
python3 - <<PY
from datetime import date
from app import app, db, User

email = "$ADMIN_EMAIL".lower().strip()
first = "$ADMIN_FIRST".strip()
last = "$ADMIN_LAST".strip()
dob_str = "$ADMIN_DOB".strip()
password = "$ADMIN_PASS1"

# parse DOB
try:
    y,m,d = [int(x) for x in dob_str.split('-')]
    dob = date(y,m,d)
except Exception:
    dob = date(2000,1,1)

with app.app_context():
    u = User.query.filter_by(email=email).first()
    if u is None:
        u = User(first_name=first, last_name=last, email=email, dob=dob, role='system_admin')
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        print(f"Created system admin user: {email}")
    else:
        print(f"User already exists: {email} (role={u.role})")
PY
else
  echo "[DRY RUN] Would create admin user: $ADMIN_EMAIL"
fi
fi

# 6) Git hooks setup
if confirm "Install pre-commit git hooks for linting/tests?" N; then
  if [[ "$DRY_RUN" -eq 0 ]]; then
    mkdir -p .git/hooks
    cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
# Pre-commit hook: run tests before allowing commit
set -e
source .venv/bin/activate 2>/dev/null || true
source scripts/env.sh 2>/dev/null || true
echo "Running tests before commit..."
python -m pytest -q --tb=short || {
  echo "Tests failed. Commit aborted."
  exit 1
}
echo "Tests passed. Proceeding with commit."
HOOK
    chmod +x .git/hooks/pre-commit
    echo "✓ Installed pre-commit hook"
  else
    echo "[DRY RUN] Would install pre-commit git hook"
  fi
fi

# 7) Production service setup
if [[ "$ENVIRONMENT" == "prod" ]]; then
  # nginx configuration
  if confirm "Install nginx configuration?" N; then
    DOMAIN="$(prompt "Domain name (e.g., game.example.com)" "localhost")"
    if [[ "$DRY_RUN" -eq 0 ]]; then
      if [[ -f "deploy/nginx_game_chrisvanek.conf" ]]; then
        NGINX_CONF="/etc/nginx/sites-available/panel-$DOMAIN.conf"
        # Copy and customize nginx config
        sed "s/game\.chrisvanek\.com/$DOMAIN/g" deploy/nginx_game_chrisvanek.conf | $SUDO tee "$NGINX_CONF" > /dev/null
        $SUDO ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
        $SUDO nginx -t && $SUDO systemctl reload nginx || echo "nginx config validation failed" >&2
        echo "✓ nginx configuration installed for $DOMAIN"
        
        # SSL/TLS setup with certbot
        if has_cmd certbot && confirm "Configure SSL/TLS with Let's Encrypt (certbot)?" Y; then
          $SUDO certbot --nginx -d "$DOMAIN" || echo "certbot setup failed" >&2
        fi
      else
        echo "Warning: deploy/nginx_game_chrisvanek.conf not found"
      fi
    else
      echo "[DRY RUN] Would install nginx config for $DOMAIN"
    fi
  fi
  
  # systemd service installation
  if confirm "Install systemd service (panel-gunicorn.service)?" N; then
    INSTALL_DIR="$(pwd)"
    if [[ "$DRY_RUN" -eq 0 ]]; then
      if [[ -f "deploy/panel-gunicorn.service" ]]; then
        # Customize service file with actual paths
        sed "s|WorkingDirectory=.*|WorkingDirectory=$INSTALL_DIR|g; s|Environment=\"PATH=.*|Environment=\"PATH=$INSTALL_DIR/.venv/bin\"|g" \
          deploy/panel-gunicorn.service | $SUDO tee /etc/systemd/system/panel-gunicorn.service > /dev/null
        $SUDO systemctl daemon-reload
        $SUDO systemctl enable panel-gunicorn.service
        if confirm "Start panel-gunicorn service now?" Y; then
          $SUDO systemctl start panel-gunicorn.service
          $SUDO systemctl status panel-gunicorn.service --no-pager || true
        fi
        echo "✓ systemd service installed"
      else
        echo "Warning: deploy/panel-gunicorn.service not found"
      fi
    else
      echo "[DRY RUN] Would install systemd service"
    fi
  fi
  
  # RQ worker service
  if confirm "Install RQ worker service (rq-worker-supervised.service)?" N; then
    if [[ "$DRY_RUN" -eq 0 ]]; then
      if [[ -f "deploy/rq-worker-supervised.service" ]]; then
        INSTALL_DIR="$(pwd)"
        sed "s|WorkingDirectory=.*|WorkingDirectory=$INSTALL_DIR|g; s|Environment=\"PATH=.*|Environment=\"PATH=$INSTALL_DIR/.venv/bin\"|g" \
          deploy/rq-worker-supervised.service | $SUDO tee /etc/systemd/system/rq-worker-supervised.service > /dev/null
        $SUDO systemctl daemon-reload
        $SUDO systemctl enable rq-worker-supervised.service
        $SUDO systemctl start rq-worker-supervised.service || true
        echo "✓ RQ worker service installed"
      fi
    else
      echo "[DRY RUN] Would install RQ worker service"
    fi
  fi
  
  # Firewall reminder
  cat <<'FIREWALL'

=== Firewall / Port Configuration ===
For production, ensure these ports are accessible:
  - Port 80 (HTTP) - for Let's Encrypt and HTTP->HTTPS redirect
  - Port 443 (HTTPS) - for secure access via nginx
  - Port 8080 is used internally by gunicorn (proxied by nginx)

Example ufw commands:
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw enable

FIREWALL
fi

# 8) Database backup script
if [[ "$ENVIRONMENT" == "prod" ]] && [[ "$USE_SQLITE" -eq 0 ]]; then
  if confirm "Generate MariaDB backup cron script?" N; then
    BACKUP_SCRIPT="scripts/backup_db.sh"
    if [[ "$DRY_RUN" -eq 0 ]]; then
      cat > "$BACKUP_SCRIPT" <<BACKUP
#!/usr/bin/env bash
# Auto-generated database backup script
set -euo pipefail
BACKUP_DIR="/var/backups/panel"
DATE=\$(date +%Y%m%d_%H%M%S)
mkdir -p "\$BACKUP_DIR"
mysqldump -h $DB_HOST -u $DB_USER -p'$DB_PASS' $DB_NAME | gzip > "\$BACKUP_DIR/panel_\${DATE}.sql.gz"
# Keep only last 7 days of backups
find "\$BACKUP_DIR" -name "panel_*.sql.gz" -mtime +7 -delete
echo "Backup completed: \$BACKUP_DIR/panel_\${DATE}.sql.gz"
BACKUP
      chmod +x "$BACKUP_SCRIPT"
      echo "✓ Created $BACKUP_SCRIPT"
      echo "  Add to crontab with: crontab -e"
      echo "  Example daily backup at 2am: 0 2 * * * $ROOT_DIR/$BACKUP_SCRIPT"
    else
      echo "[DRY RUN] Would create backup script at $BACKUP_SCRIPT"
    fi
  fi
fi

# 9) Health check
if confirm "Run post-install health check?" Y; then
  if [[ "$DRY_RUN" -eq 0 ]]; then
    echo "Running health check..."
    # shellcheck disable=SC1090
    source "$VENVDIR/bin/activate" 2>/dev/null || true
    source "$ENV_FILE" 2>/dev/null || true
    
    # Start app in background
    timeout 10 python app.py &
    APP_PID=$!
    sleep 3
    
    # Test HTTP endpoint
    if curl -s http://127.0.0.1:5000/ | grep -q "panel\|game\|login" 2>/dev/null; then
      echo "✓ Health check passed: App is responding"
    else
      echo "⚠ Health check warning: App may not be responding correctly"
    fi
    
    # Cleanup
    kill $APP_PID 2>/dev/null || true
    wait $APP_PID 2>/dev/null || true
  else
    echo "[DRY RUN] Would run health check"
  fi
fi

# 10) Docker option
if confirm "Generate docker-compose.yml for containerized deployment?" N; then
  if [[ "$DRY_RUN" -eq 0 ]]; then
    cat > docker-compose.yml <<DOCKER
version: '3.8'
services:
  panel:
    build: .
    ports:
      - "8080:8080"
    environment:
      - PANEL_SECRET_KEY=$SECRET_KEY
      - PANEL_REDIS_URL=redis://redis:6379/0
      - PANEL_DB_HOST=db
      - PANEL_DB_USER=$DB_USER
      - PANEL_DB_PASS=$DB_PASS
      - PANEL_DB_NAME=$DB_NAME
    depends_on:
      - db
      - redis
    volumes:
      - ./instance:/app/instance
  
  db:
    image: mariadb:10.11
    environment:
      - MARIADB_ROOT_PASSWORD=rootpass
      - MARIADB_DATABASE=$DB_NAME
      - MARIADB_USER=$DB_USER
      - MARIADB_PASSWORD=$DB_PASS
    volumes:
      - mariadb_data:/var/lib/mysql
  
  redis:
    image: redis:7-alpine
    
  worker:
    build: .
    command: python run_worker.py
    environment:
      - PANEL_REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

volumes:
  mariadb_data:
DOCKER
    
    # Create Dockerfile if missing
    if [[ ! -f Dockerfile ]]; then
      cat > Dockerfile <<DFILE
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y espeak && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8080", "app:app"]
DFILE
    fi
    echo "✓ Created docker-compose.yml and Dockerfile"
    echo "  Start with: docker-compose up -d"
  else
    echo "[DRY RUN] Would create docker-compose.yml"
  fi
fi

# 11) CI/CD workflow
if confirm "Generate GitHub Actions CI/CD workflow?" N; then
  if [[ "$DRY_RUN" -eq 0 ]]; then
    mkdir -p .github/workflows
    cat > .github/workflows/ci.yml <<'CI'
name: CI/CD

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          python -m playwright install chromium
      - name: Run tests
        env:
          PANEL_USE_SQLITE: 1
        run: pytest -q
      
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Lint
        run: |
          pip install flake8
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
CI
    echo "✓ Created .github/workflows/ci.yml"
  else
    echo "[DRY RUN] Would create GitHub Actions workflow"
  fi
fi

cat <<'OUT'

Installation complete.

Next steps (development):
  1) Activate the venv and env:
     source "${VENVDIR}/bin/activate"
     source scripts/env.sh
  2) Run the app:
     python app.py
OUT

if [[ "$INSTALL_PLAYWRIGHT" -eq 1 ]]; then
cat <<'OUT'
  3) Run tests (including E2E):
     pytest -q

OUT
else
cat <<'OUT'
  3) Run tests (note: E2E tests will be skipped without Playwright):
     pytest -q
     
     To enable E2E tests later:
       source .venv/bin/activate
       python -m playwright install chromium

OUT
fi

if [[ "$ENVIRONMENT" == "prod" ]]; then
cat <<'OUT'
Production deployment:
  - Services are configured and can be managed with systemctl
  - nginx is configured (if selected)
  - SSL/TLS is configured (if selected with certbot)
  - Database backups can be scheduled via cron (if generated)
  - Check firewall settings to ensure ports 80 and 443 are accessible

OUT
fi

cat <<'OUT'
Additional options:
  - Docker: Use docker-compose up -d (if generated)
  - Uninstall: Run scripts/uninstall.sh (if generated)
  - CI/CD: Push to trigger GitHub Actions (if workflow generated)

OUT
