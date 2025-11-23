#!/bin/bash
# Configuration Management Script
# Manage multi-environment configurations securely

set -e

# Configuration
CONFIG_DIR="config"
ENVIRONMENTS=("development" "staging" "production" "testing")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment name
validate_environment() {
    local env=$1
    for valid_env in "${ENVIRONMENTS[@]}"; do
        if [ "$env" = "$valid_env" ]; then
            return 0
        fi
    done
    return 1
}

# Setup environment
setup_environment() {
    local env=$1

    if ! validate_environment "$env"; then
        log_error "Invalid environment: $env"
        echo "Valid environments: ${ENVIRONMENTS[*]}"
        exit 1
    fi

    log_info "Setting up environment: $env"

    # Create .env file
    python3 -c "
from src.panel.config_manager import ConfigManager
manager = ConfigManager()
manager.create_env_file('$env')
"

    # Validate configuration
    if python3 -c "
from src.panel.config_manager import ConfigManager
manager = ConfigManager()
errors = manager.validate_config('$env')
if errors:
    print('Configuration validation failed:')
    for error in errors:
        print(f'  - {error}')
    exit(1)
else:
    print('Configuration validation passed')
"; then
        log_success "Environment $env setup complete"
    else
        log_error "Configuration validation failed for $env"
        exit 1
    fi
}

# Validate all configurations
validate_configs() {
    log_info "Validating all environment configurations..."

    python3 -c "
from src.panel.config_manager import ConfigManager
manager = ConfigManager()
all_valid = True

for env_name in manager.list_environments():
    errors = manager.validate_config(env_name)
    if errors:
        print(f'? {env_name} configuration has errors:')
        for error in errors:
            print(f'  - {error}')
        all_valid = False
    else:
        print(f'? {env_name} configuration is valid')

if not all_valid:
    exit(1)
"

    if [ $? -eq 0 ]; then
        log_success "All configurations are valid"
    else
        log_error "Some configurations have errors"
        exit 1
    fi
}

# List environments
list_environments() {
    log_info "Available environments:"

    python3 -c "
from src.panel.config_manager import ConfigManager
manager = ConfigManager()

for env_name in manager.list_environments():
    info = manager.get_environment_info(env_name)
    status = '?' if info['is_valid'] else '?'
    features = f\"{info['features_enabled']}/{info['total_features']}\"
    print(f\"{status} {env_name}\")
    print(f\"   Features: {features} enabled\")
    print(f\"   Database: {'Yes' if info['has_database'] else 'No'}\")
    print(f\"   Redis: {'Yes' if info['has_redis'] else 'No'}\")
    print(f\"   CDN: {'Yes' if info['has_cdn'] else 'No'}\")
    if info['validation_errors']:
        print(f\"   Errors: {len(info['validation_errors'])}\")
    print()
"
}

# Update configuration
update_config() {
    local env=$1
    local key=$2
    local value=$3

    if ! validate_environment "$env"; then
        log_error "Invalid environment: $env"
        exit 1
    fi

    if [ -z "$key" ] || [ -z "$value" ]; then
        log_error "Key and value are required"
        echo "Usage: $0 update <env> <key> <value>"
        exit 1
    fi

    log_info "Updating $env config: $key = $value"

    python3 -c "
from src.panel.config_manager import ConfigManager
manager = ConfigManager()
manager.update_config('$env', {'$key': '$value'})
print('Configuration updated')
"

    log_success "Configuration updated"
}

# Show environment info
show_environment() {
    local env=$1

    if ! validate_environment "$env"; then
        log_error "Invalid environment: $env"
        exit 1
    fi

    log_info "Environment information: $env"

    python3 -c "
import json
from src.panel.config_manager import ConfigManager
manager = ConfigManager()
info = manager.get_environment_info('$env')
print(json.dumps(info, indent=2))
"
}

# Encrypt sensitive data
encrypt_secret() {
    local key=$1
    local value=$2

    if [ -z "$key" ] || [ -z "$value" ]; then
        log_error "Key and value are required"
        echo "Usage: $0 encrypt <key> <value>"
        exit 1
    fi

    log_info "Encrypting secret: $key"

    python3 -c "
from src.panel.config_manager import SecretManager
manager = SecretManager()
encrypted = manager.encrypt_secret('$value')
print(f'Encrypted value: {encrypted}')
manager.set_secret('$key', '$value')
print('Secret stored securely')
"

    log_success "Secret encrypted and stored"
}

# Decrypt sensitive data
decrypt_secret() {
    local key=$1

    if [ -z "$key" ]; then
        log_error "Key is required"
        echo "Usage: $0 decrypt <key>"
        exit 1
    fi

    log_info "Decrypting secret: $key"

    python3 -c "
from src.panel.config_manager import SecretManager
manager = SecretManager()
value = manager.get_secret('$key')
if value:
    print(f'Decrypted value: {value}')
else:
    print('Secret not found')
"
}

# Create backup of configurations
backup_configs() {
    local backup_dir="config/backup/$(date +%Y%m%d_%H%M%S)"

    log_info "Creating configuration backup: $backup_dir"

    mkdir -p "$backup_dir"

    # Copy all config files
    cp -r config/*.json "$backup_dir/" 2>/dev/null || true
    cp .secrets "$backup_dir/" 2>/dev/null || true
    cp .config_key "$backup_dir/" 2>/dev/null || true

    # Create archive
    tar -czf "${backup_dir}.tar.gz" -C config backup/ 2>/dev/null || true

    log_success "Configuration backup created: ${backup_dir}.tar.gz"
}

# Restore configurations from backup
restore_configs() {
    local backup_file=$1

    if [ -z "$backup_file" ]; then
        log_error "Backup file is required"
        echo "Usage: $0 restore <backup_file>"
        exit 1
    fi

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_info "Restoring configuration from: $backup_file"

    # Extract backup
    temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir"

    # Restore files
    cp -r "$temp_dir"/* config/ 2>/dev/null || true

    # Cleanup
    rm -rf "$temp_dir"

    log_success "Configuration restored from backup"
}

# Initialize configuration system
init_configs() {
    log_info "Initializing configuration system..."

    # Create config directory
    mkdir -p config

    # Create default configurations
    python3 -c "
from src.panel.config_manager import create_environment_configs
create_environment_configs()
"

    # Setup encryption key
    if [ ! -f .config_key ]; then
        log_info "Generating encryption key..."
        python3 -c "
from src.panel.config_manager import SecretManager
manager = SecretManager()
_ = manager._get_key()  # This generates the key
print('Encryption key generated')
"
    fi

    log_success "Configuration system initialized"
}

# Main function
main() {
    case "$1" in
        "setup")
            setup_environment "$2"
            ;;
        "validate")
            validate_configs
            ;;
        "list")
            list_environments
            ;;
        "update")
            update_config "$2" "$3" "$4"
            ;;
        "show")
            show_environment "$2"
            ;;
        "encrypt")
            encrypt_secret "$2" "$3"
            ;;
        "decrypt")
            decrypt_secret "$2"
            ;;
        "backup")
            backup_configs
            ;;
        "restore")
            restore_configs "$2"
            ;;
        "init")
            init_configs
            ;;
        *)
            echo "Configuration Management Script"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  init                    Initialize configuration system"
            echo "  setup <env>            Setup environment configuration"
            echo "  validate               Validate all configurations"
            echo "  list                   List all environments"
            echo "  show <env>             Show environment information"
            echo "  update <env> <key> <val> Update configuration value"
            echo "  encrypt <key> <val>    Encrypt and store secret"
            echo "  decrypt <key>          Decrypt and show secret"
            echo "  backup                 Create configuration backup"
            echo "  restore <file>         Restore from backup"
            echo ""
            echo "Environments: ${ENVIRONMENTS[*]}"
            exit 1
            ;;
    esac
}

main "$@"