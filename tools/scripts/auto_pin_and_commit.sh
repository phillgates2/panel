#!/usr/bin/env bash
set -euo pipefail

# Auto upgrade, pin dependencies, run pip-audit, and create git commit if safe
# Usage: tools/scripts/auto_pin_and_commit.sh [venv-path] [requirements-output]

VENV_DIR="${1:-venv}"
OUTPUT_REQS="${2:-requirements/requirements-pinned.txt}"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DRY_RUN=${DRY_RUN:-false}

log(){ echo "[INFO] $*"; }
err(){ echo "[ERROR] $*" >&2; exit 1; }

if [[ ! -d "$VENV_DIR" ]]; then
  log "Creating venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# Activate
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

log "Upgrading pip tooling"
pip install --upgrade pip setuptools wheel pip-audit || true

log "Upgrading installed packages to latest"
# upgrade each outdated
outdated_json=$(pip list --outdated --format=json || echo '[]')
if python - <<PY
import json,sys
out=json.loads(sys.stdin.read())
if not out:
    sys.exit(2)
else:
    sys.exit(0)
PY <<< "$outdated_json"; then
  python - <<'PY'
import json,subprocess,sys
out=json.loads(sys.stdin.read())
for p in out:
    name=p['name']
    print('Upgrading',name)
    subprocess.run([sys.executable,'-m','pip','install','--upgrade',name])
PY <<< "$outdated_json"
else
  log "No outdated packages detected"
fi

log "Freezing pinned requirements to $OUTPUT_REQS"
mkdir -p "$(dirname "$OUTPUT_REQS")"
pip freeze > "$OUTPUT_REQS"

log "Running pip-audit"
pip-audit --format json --output pip-audit-report.json || true

# Check for high/critical vulnerabilities
if [[ -f pip-audit-report.json ]]; then
  if command -v jq >/dev/null 2>&1; then
    high_count=$(jq '[.[] | .vulns[]? | select(.severity=="HIGH" or .severity=="CRITICAL")] | length' pip-audit-report.json 2>/dev/null || echo "0")
  else
    # Fallback simple check
    high_count=$(grep -E '"severity": "(HIGH|CRITICAL)"' pip-audit-report.json | wc -l || true)
  fi
else
  high_count=0
fi

if [[ "$high_count" -gt 0 ]]; then
  err "pip-audit found $high_count high/critical vulnerabilities. Aborting commit. See pip-audit-report.json"
fi

# If safe, create git commit
if [[ "$DRY_RUN" == "true" ]]; then
  log "DRY RUN: Would commit $OUTPUT_REQS"
  exit 0
fi

cd "$REPO_ROOT"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  err "Not inside a git work tree"
fi

# Add and commit changes
git add "$OUTPUT_REQS" || true
if git diff --cached --quiet; then
  log "No changes to commit"
else
  git commit -m "chore(deps): upgrade and pin dependencies (automated)" || true
  log "Committed pinned requirements: $OUTPUT_REQS"
fi

# Provide guidance to push
log "Pinned requirements updated and committed locally. Review and push changes if desired."
