#!/usr/bin/env bash
set -euo pipefail

# Upgrade all installed Python packages in a venv (or create a temp venv),
# pin the updated versions to requirements/requirements-pinned.txt,
# and run a security audit (pip-audit / safety).

VENV_DIR="${1:-venv}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_REQS="$REPO_ROOT/requirements/requirements-pinned.txt"
DRY_RUN=${DRY_RUN:-false}

log(){ echo "[INFO] $*"; }
err(){ echo "[ERROR] $*" >&2; exit 1; }

create_venv(){
  if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating virtualenv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  else
    log "Using existing virtualenv at $VENV_DIR"
  fi
}

activate_venv(){
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
}

upgrade_packages(){
  log "Upgrading pip, setuptools, wheel"
  pip install --upgrade pip setuptools wheel || true

  log "Getting list of outdated packages..."
  outdated=$(pip list --outdated --format=freeze || true)
  if [[ -z "$outdated" ]]; then
    log "No outdated packages found"
  else
    log "Upgrading outdated packages"
    # pip list --outdated --format=json could be used, but use freeze parsing
    while IFS= read -r line; do
      pkg=$(echo "$line" | cut -d'=' -f1)
      if [[ -n "$pkg" ]]; then
        log "Upgrading $pkg"
        if [[ "$DRY_RUN" == "true" ]]; then
          echo "DRY RUN: pip install --upgrade $pkg"
        else
          pip install --upgrade "$pkg" || true
        fi
      fi
    done <<< "$outdated"
  fi

  log "Writing pinned requirements to $OUTPUT_REQS"
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "DRY RUN: pip freeze > $OUTPUT_REQS"
  else
    mkdir -p "$(dirname "$OUTPUT_REQS")"
    pip freeze > "$OUTPUT_REQS" || true
  fi
}

security_audit(){
  if command -v pip-audit >/dev/null 2>&1; then
    log "Running pip-audit"
    pip-audit || true
  elif command -v safety >/dev/null 2>&1; then
    log "Running safety"
    safety check || true
  else
    log "Installing pip-audit"
    pip install pip-audit || true
    pip-audit || true
  fi
}

main(){
  create_venv
  activate_venv
  upgrade_packages
  security_audit
  log "Upgrade and pin process complete. Pinned requirements: $OUTPUT_REQS"
}

main "$@"
