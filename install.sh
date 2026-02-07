#!/usr/bin/env bash
set -euo pipefail

# Top-level wrapper installer for Panel project
# - Detect OS and package manager
# - Install system deps (git, python3, docker) where possible
# - Create venv and install/upgrade Python deps (supports requirements, Pipfile, pyproject)
# - Run project dependency update and security checks
# - Launch the project installer at tools/scripts/install.sh

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "$0")"
DRY_RUN=false
NON_INTERACTIVE=false
YES=false
FORCE=false
CONFIG_FILE=""
INSTALL_DIR="${PANEL_INSTALL_DIR:-$HERE}"
VENV_DIR="$INSTALL_DIR/venv"
PYTHON_CMD=python3

log(){ echo "[INFO] $*"; }
warn(){ echo "[WARN] $*" >&2; }
err(){ echo "[ERROR] $*" >&2; exit 1; }

detect_pkg_manager(){
  if command -v apt-get >/dev/null 2>&1; then echo apt-get
  elif command -v dnf >/dev/null 2>&1; then echo dnf
  elif command -v yum >/dev/null 2>&1; then echo yum
  elif command -v pacman >/dev/null 2>&1; then echo pacman
  elif command -v apk >/dev/null 2>&1; then echo apk
  elif command -v brew >/dev/null 2>&1; then echo brew
  else echo ""; fi
}

run_or_dry(){
  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY RUN: $*"
  else
    eval "$*"
  fi
}

install_system_packages(){
  PKG=$(detect_pkg_manager)
  log "Detected package manager: ${PKG:-none}"
  case "$PKG" in
    apt-get)
      run_or_dry sudo apt-get update -y
      run_or_dry sudo apt-get install -y git curl wget python3 python3-venv python3-pip docker.io docker-compose || true
      ;;
    dnf|yum)
      run_or_dry sudo $PKG install -y git curl wget python3 python3-venv python3-pip docker docker-compose || true
      ;;
    pacman)
      run_or_dry sudo pacman -S --noconfirm git curl wget python python-virtualenv python-pip docker docker-compose || true
      ;;
    brew)
      run_or_dry brew install git curl wget python docker docker-compose || true
      ;;
    apk)
      run_or_dry sudo apk add git curl wget python3 py3-venv py3-pip docker docker-compose || true
      ;;
    *)
      warn "No supported package manager detected; please install git, python3, pip and docker manually"
      ;;
  esac
}

create_venv_and_install(){
  mkdir -p "$INSTALL_DIR"
  if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating virtualenv at $VENV_DIR"
    run_or_dry "$PYTHON_CMD -m venv '$VENV_DIR'"
  else
    log "Virtualenv exists at $VENV_DIR"
  fi

  # Activate and install
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
  pip install --upgrade pip setuptools wheel || true

  if [[ -f "$INSTALL_DIR/requirements/requirements.txt" ]]; then
    log "Installing from requirements/requirements.txt"
    run_or_dry pip install --upgrade -r "$INSTALL_DIR/requirements/requirements.txt" || true
  elif [[ -f "$INSTALL_DIR/requirements.txt" ]]; then
    log "Installing from requirements.txt"
    run_or_dry pip install --upgrade -r "$INSTALL_DIR/requirements.txt" || true
  elif [[ -f "$INSTALL_DIR/Pipfile" ]]; then
    log "Pipfile detected - using pipenv to install into venv"
    pip install pipenv || true
    run_or_dry pipenv install --deploy --system --ignore-pipfile || true
  elif [[ -f "$INSTALL_DIR/pyproject.toml" ]]; then
    log "pyproject.toml detected - performing PEP517 install"
    pip install --upgrade build || true
    run_or_dry pip install --upgrade "$INSTALL_DIR" || true
  else
    log "No Python dependency manifest detected - skipping pip install"
  fi
}

update_project_dependencies(){
  # Use existing helper if present
  if [[ -x "scripts/update-dependencies.sh" ]]; then
    log "Running scripts/update-dependencies.sh all"
    run_or_dry bash scripts/update-dependencies.sh all || true
  elif [[ -x "tools/scripts/update-dependencies.sh" ]]; then
    log "Running tools/scripts/update-dependencies.sh all"
    run_or_dry bash tools/scripts/update-dependencies.sh all || true
  else
    log "No update-dependencies helper found; upgrading installed packages in venv"
    source "$VENV_DIR/bin/activate"
    python - <<'PY'
import json,subprocess,sys
out = subprocess.check_output([sys.executable,'-m','pip','list','--outdated','--format','json'])
out = out.decode()
if out.strip():
    outdated = json.loads(out)
else:
    outdated = []
for p in outdated:
    name = p['name']
    print('Upgrading',name)
    subprocess.check_call([sys.executable,'-m','pip','install','--upgrade',name])
PY
    pip freeze > "$INSTALL_DIR/requirements/requirements-updated.txt" 2>/dev/null || true
  fi
}

security_audit(){
  source "$VENV_DIR/bin/activate" || return
  if command -v pip-audit >/dev/null 2>&1; then
    log "Running pip-audit"
    run_or_dry pip-audit || true
  elif command -v safety >/dev/null 2>&1; then
    log "Running safety"
    run_or_dry safety check || true
  else
    log "pip-audit/safety not installed; installing pip-audit"
    run_or_dry pip install pip-audit || true
    run_or_dry pip-audit || true
  fi
}

config_only_mode(){
  if [[ -z "$CONFIG_FILE" ]]; then
    err "No config file provided for --config"
  fi

  if [[ ! -f "$CONFIG_FILE" ]]; then
    err "Config file not found: $CONFIG_FILE"
  fi

  local ext
  ext="${CONFIG_FILE##*.}"

  # Determine install directory from config contents, falling back to env or default
  if [[ "$ext" == "json" ]]; then
    INSTALL_DIR="$(python3 - "$CONFIG_FILE" <<'PY'
import json, sys
cfg_path = sys.argv[1]
with open(cfg_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
install_dir = data.get('PANEL_INSTALL_DIR', './tests_tmp_install_json')
print(install_dir)
PY
)"
  else
    INSTALL_DIR="./tests_tmp_install"
    while IFS='=' read -r key val; do
      key="${key%% *}"
      if [[ "$key" == "PANEL_INSTALL_DIR" ]]; then
        INSTALL_DIR="${val}"
        break
      fi
    done < "$CONFIG_FILE"
  fi

  mkdir -p "$INSTALL_DIR"
  local secrets_path
  secrets_path="$INSTALL_DIR/.install_secrets"
  cp "$CONFIG_FILE" "$secrets_path" || {
    # Fallback: write non-empty lines
    grep -v '^[[:space:]]*$' "$CONFIG_FILE" > "$secrets_path" || true
  }

  log "Config-only installer wrote secrets to $secrets_path"
}

run_project_installer(){
  if [[ -x "tools/scripts/install.sh" ]]; then
    log "Launching tools/scripts/install.sh"
    run_or_dry bash tools/scripts/install.sh --non-interactive || true
  else
    warn "tools/scripts/install.sh not found or not executable"
  fi
}

show_help(){
  cat <<EOF
$SCRIPT_NAME - Top-level Panel installer wrapper

Usage:
  $SCRIPT_NAME --install [--install-dir DIR] [--non-interactive] [--dry-run] [--yes]
  $SCRIPT_NAME --uninstall [--install-dir DIR] [--dry-run] [--yes]
  $SCRIPT_NAME --update-deps [--install-dir DIR]
  $SCRIPT_NAME --config PATH   # Parse config file and write .install_secrets only

Options:
  --install       Run full installation
  --uninstall     Run uninstaller wrapper (calls tools/scripts/uninstall.sh)
  --update-deps   Update Python dependencies to latest inside venv
  --install-dir   Set installation directory (default repo root)
  --non-interactive  Use defaults
  --dry-run       Show actions without executing
  --yes           Assume yes prompts
  --help          Show this help
EOF
}

if [[ $# -eq 0 ]]; then show_help; exit 0; fi
ACTION=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --install) ACTION=install; shift;;
    --uninstall) ACTION=uninstall; shift;;
    --update-deps) ACTION=update-deps; shift;;
    --config)
      CONFIG_FILE="$2"
      ACTION=config-only
      shift 2
      ;;
    --install-dir) INSTALL_DIR="$2"; VENV_DIR="$INSTALL_DIR/venv"; shift 2;;
    --non-interactive) NON_INTERACTIVE=true; shift;;
    --dry-run) DRY_RUN=true; shift;;
    --yes|-y) YES=true; shift;;
    --force) FORCE=true; shift;;
    --help|-h) show_help; exit 0;;
    *) err "Unknown arg: $1";;
  esac
done

case "$ACTION" in
  install)
    install_system_packages
    create_venv_and_install
    update_project_dependencies
    security_audit
    run_project_installer
    ;;
  uninstall)
    if [[ -x "tools/scripts/uninstall.sh" ]]; then
      run_or_dry bash tools/scripts/uninstall.sh
    else
      warn "tools/scripts/uninstall.sh not found"
    fi
    ;;
  update-deps)
    if [[ -d "$VENV_DIR" ]]; then
      create_venv_and_install
      update_project_dependencies
      security_audit
    else
      err "Virtualenv not found at $VENV_DIR. Run --install first."
    fi
    ;;
  config-only)
    config_only_mode
    ;;
  *) show_help; exit 1;;
esac
