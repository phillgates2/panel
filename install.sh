#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      CONFIG_FILE="$2"; shift 2;;
    *) shift;;
  esac
done

# Load config (env or json)
INSTALL_DIR="./tests_tmp_install"
DB_USER="user"
ADMIN_EMAIL="admin@example.com"

if [[ -n "${CONFIG_FILE}" ]]; then
  if [[ "${CONFIG_FILE}" == *.json ]]; then
    INSTALL_DIR=$(python -c 'import json,sys; cfg=json.load(open(sys.argv[1])); print(cfg.get("PANEL_INSTALL_DIR","./tests_tmp_install"))' "${CONFIG_FILE}")
    DB_USER=$(python -c 'import json,sys; cfg=json.load(open(sys.argv[1])); print(cfg.get("PANEL_DB_USER","user"))' "${CONFIG_FILE}")
    ADMIN_EMAIL=$(python -c 'import json,sys; cfg=json.load(open(sys.argv[1])); print(cfg.get("PANEL_ADMIN_EMAIL","admin@example.com"))' "${CONFIG_FILE}")
  else
    # env format KEY=VAL per line
    while IFS='=' read -r k v; do
      case "$k" in
        PANEL_INSTALL_DIR) INSTALL_DIR="$v";;
        PANEL_DB_USER) DB_USER="$v";;
        PANEL_ADMIN_EMAIL) ADMIN_EMAIL="$v";;
      esac
    done < "${CONFIG_FILE}"
  fi
fi

mkdir -p "${INSTALL_DIR}"
SECRETS_FILE="${INSTALL_DIR}/.install_secrets"
{
  echo "PANEL_DB_USER=${DB_USER}"
  echo "PANEL_ADMIN_EMAIL=${ADMIN_EMAIL}"
} > "${SECRETS_FILE}"

echo "Installer completed"
