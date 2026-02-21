#!/bin/bash

# env_generator.sh: Generate a .env file with validation and optional encryption.

set -e

# Default .env template
ENV_TEMPLATE="""
# Example .env file
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql+psycopg2://paneluser:panelpass@127.0.0.1:5432/paneldb
REDIS_URL=redis://localhost:6379/0
LOG_FORMAT=text
"""

# Function to validate .env file
validate_env() {
  local env_file="$1"
  echo "Validating $env_file..."
  required_keys=("FLASK_ENV" "SECRET_KEY" "DATABASE_URL" "REDIS_URL" "LOG_FORMAT")
  for key in "${required_keys[@]}"; do
    if ! grep -q "^$key=" "$env_file"; then
      echo "Error: Missing required key '$key' in $env_file" >&2
      exit 1
    fi
  done
  echo "Validation passed."
}

# Function to encrypt .env file
encrypt_env() {
  local env_file="$1"
  local method="$2"
  local output_file="$env_file.enc"

  case "$method" in
    age)
      if ! command -v age &>/dev/null; then
        echo "Error: 'age' is not installed." >&2
        exit 1
      fi
      echo "Encrypting $env_file with age..."
      age -o "$output_file" "$env_file"
      ;;
    gpg)
      if ! command -v gpg &>/dev/null; then
        echo "Error: 'gpg' is not installed." >&2
        exit 1
      fi
      echo "Encrypting $env_file with gpg..."
      gpg --symmetric --cipher-algo AES256 -o "$output_file" "$env_file"
      ;;
    *)
      echo "Error: Unsupported encryption method '$method'. Use 'age' or 'gpg'." >&2
      exit 1
      ;;
  esac

  echo "Encrypted file saved as $output_file."
}

# Main script logic
output_file=".env"
while getopts "o:e:v" opt; do
  case $opt in
    o) output_file="$OPTARG" ;;
    e) encryption_method="$OPTARG" ;;
    v) validate_only=true ;;
    *) echo "Usage: $0 [-o output_file] [-e encryption_method] [-v validate_only]" >&2; exit 1 ;;
  esac
done

if [ "$validate_only" = true ]; then
  validate_env "$output_file"
  exit 0
fi

if [ -f "$output_file" ]; then
  echo "Warning: $output_file already exists. Overwrite? (y/N)"
  read -r confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborting."
    exit 1
  fi
fi

echo "Generating $output_file..."
echo -e "$ENV_TEMPLATE" > "$output_file"

validate_env "$output_file"

if [ -n "$encryption_method" ]; then
  encrypt_env "$output_file" "$encryption_method"
fi

echo "$output_file generated successfully."
