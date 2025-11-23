#!/bin/bash
# Azure Deployment Script for Panel Application
# Handles infrastructure provisioning and application deployment

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INFRA_DIR="$PROJECT_ROOT/infrastructure/azure"
ENV_FILE="$PROJECT_ROOT/.env.azure"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Azure CLI
    if ! command -v az >/dev/null 2>&1; then
        log_error "Azure CLI is not installed. Please install it first."
        exit 1
    fi

    # Check Terraform
    if ! command -v terraform >/dev/null 2>&1; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi

    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi

    # Check Azure login
    if ! az account show >/dev/null 2>&1; then
        log_error "Not logged in to Azure. Please run 'az login'."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Setup Terraform backend
setup_terraform_backend() {
    log_info "Setting up Terraform backend..."

    # Create resource group for Terraform state (if it doesn't exist)
    az group create --name panel-terraform-state --location eastus --output none 2>/dev/null || true

    # Create storage account for Terraform state
    az storage account create \
        --name panelterraformstate \
        --resource-group panel-terraform-state \
        --location eastus \
        --sku Standard_LRS \
        --output none 2>/dev/null || true

    # Create storage container
    az storage container create \
        --name tfstate \
        --account-name panelterraformstate \
        --output none 2>/dev/null || true

    log_success "Terraform backend ready"
}

# Initialize infrastructure
init_infrastructure() {
    log_info "Initializing infrastructure..."

    cd "$INFRA_DIR"

    # Initialize Terraform
    terraform init

    # Validate configuration
    terraform validate

    log_success "Infrastructure initialized"
}

# Plan infrastructure changes
plan_infrastructure() {
    log_info "Planning infrastructure changes..."

    cd "$INFRA_DIR"

    terraform plan -var-file=production.tfvars -out=tfplan

    log_success "Infrastructure plan created"
}

# Apply infrastructure changes
apply_infrastructure() {
    log_info "Applying infrastructure changes..."

    cd "$INFRA_DIR"

    terraform apply tfplan

    log_success "Infrastructure deployed"
}

# Build and push Docker image
build_and_push_image() {
    log_info "Building and pushing Docker image..."

    cd "$PROJECT_ROOT"

    # Get ACR login server from Terraform output
    ACR_SERVER=$(cd "$INFRA_DIR" && terraform output -raw acr_login_server)

    # Build Docker image
    docker build -f Dockerfile.azure -t panel:latest .

    # Login to ACR
    az acr login --name "${ACR_SERVER%%.*}"

    # Tag and push
    docker tag panel:latest "$ACR_SERVER/panel:latest"
    docker push "$ACR_SERVER/panel:latest"

    log_success "Docker image built and pushed"
}

# Deploy application
deploy_application() {
    log_info "Deploying application..."

    # The Container App will automatically pick up the new image
    # since we're using the latest tag

    log_info "Waiting for deployment to complete..."

    # Wait for the container app to be ready
    sleep 30

    # Check if the app is responding
    CONTAINER_URL=$(cd "$INFRA_DIR" && terraform output -raw container_app_url)

    for i in {1..30}; do
        if curl -f -s "$CONTAINER_URL/api/health" >/dev/null 2>&1; then
            break
        fi
        echo "Waiting for application to be ready... ($i/30)"
        sleep 10
    done

    if curl -f -s "$CONTAINER_URL/api/health" >/dev/null 2>&1; then
        log_success "Application deployed and healthy"
    else
        log_error "Application deployment failed - health check failed"
        exit 1
    fi
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring..."

    # Get resource group name
    RG_NAME=$(cd "$INFRA_DIR" && terraform output -raw resource_group_name 2>/dev/null || echo "")

    if [ -n "$RG_NAME" ]; then
        log_info "Monitoring setup completed via Terraform"
    fi

    log_success "Monitoring setup completed"
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."

    # Get Container App URL
    CONTAINER_URL=$(cd "$INFRA_DIR" && terraform output -raw container_app_url)

    # Run health checks
    if curl -f -s "$CONTAINER_URL/api/health" >/dev/null 2>&1; then
        log_success "Application health check passed"
    else
        log_error "Application health check failed"
        exit 1
    fi
}

# Create Azure environment file
create_env_file() {
    log_info "Creating Azure environment file..."

    # Get infrastructure outputs
    cd "$INFRA_DIR"
    CONTAINER_URL=$(terraform output -raw container_app_url)
    FRONTDOOR_URL=$(terraform output -raw frontdoor_endpoint)
    DB_SERVER=$(terraform output -raw database_server)
    REDIS_HOST=$(terraform output -raw redis_hostname)
    STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)
    KEY_VAULT=$(terraform output -raw key_vault_name)
    OPENAI_ENDPOINT=$(terraform output -raw openai_endpoint)

    # Create .env.azure
    cat > "$ENV_FILE" << EOF
# Panel Azure Production Environment Configuration
# Generated by deployment script

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY:-"change-this-in-key-vault"}
DEBUG=false
TESTING=false

# Database Configuration
DATABASE_URL=postgresql://paneladmin:${DB_PASSWORD:-"change-this-in-key-vault"}@$DB_SERVER:5432/panel

# Redis Configuration
REDIS_URL=rediss://:${REDIS_PASSWORD:-"change-this-in-key-vault"}@$REDIS_HOST:6380

# Azure Storage Configuration
AZURE_STORAGE_ACCOUNT=$STORAGE_ACCOUNT
AZURE_STORAGE_KEY=${STORAGE_KEY:-"change-this-in-key-vault"}
AZURE_STORAGE_CONTAINER=uploads

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=$OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY=${OPENAI_KEY:-"change-this-in-key-vault"}
AZURE_OPENAI_DEPLOYMENT_GPT4=gpt-4
AZURE_OPENAI_DEPLOYMENT_GPT35=gpt-35-turbo

# CDN Configuration
CDN_ENABLED=true
CDN_URL=https://$FRONTDOOR_URL
CDN_PROVIDER=azure-frontdoor

# Microservices Configuration
MICROSERVICES_ENABLED=true
API_GATEWAY_ENABLED=true

# Security Settings
SESSION_TIMEOUT=3600
PASSWORD_MIN_LENGTH=12
MAX_LOGIN_ATTEMPTS=3
LOCKOUT_DURATION=1800

# Feature Flags
FORUM_ENABLED=true
CMS_ENABLED=true
ADMIN_ENABLED=true
API_ENABLED=true
OAUTH_ENABLED=true
GDPR_ENABLED=true
PWA_ENABLED=true
REALTIME_ENABLED=true
AI_ENABLED=true

# Monitoring
PERFORMANCE_MONITORING_ENABLED=true

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_SCHEDULE=daily
BACKUP_RETENTION_DAYS=30
BACKUP_ENCRYPTION=true
BACKUP_STORAGE_PATH=abfs://backups@$STORAGE_ACCOUNT.dfs.core.windows.net/

# Logging
LOG_LEVEL=INFO

# Azure-specific settings
AZURE_KEY_VAULT_NAME=$KEY_VAULT
AZURE_LOCATION=eastus
EOF

    log_success "Azure environment file created: $ENV_FILE"
}

# Main deployment function
deploy_full() {
    log_info "Starting full Azure deployment..."

    check_prerequisites
    setup_terraform_backend
    init_infrastructure
    plan_infrastructure

    echo
    log_warn "About to apply infrastructure changes. This will create Azure resources and may incur costs."
    read -p "Do you want to continue? (yes/no): " -r
    echo

    if [[ ! $REPLY =~ ^yes$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi

    apply_infrastructure
    create_env_file
    build_and_push_image
    deploy_application
    setup_monitoring
    run_health_checks

    log_success "Full deployment completed!"
    log_info "Your application should be available at: https://$(cd "$INFRA_DIR" && terraform output -raw frontdoor_endpoint)"
}

# Update deployment function
deploy_update() {
    log_info "Starting application update deployment..."

    check_prerequisites
    build_and_push_image
    deploy_application
    run_health_checks

    log_success "Application update completed!"
}

# Destroy infrastructure
destroy_infrastructure() {
    log_warn "About to destroy all infrastructure. This will delete all Azure resources!"
    read -p "Are you sure? Type 'destroy' to confirm: " -r
    echo

    if [[ $REPLY != "destroy" ]]; then
        log_info "Destruction cancelled"
        exit 0
    fi

    log_info "Destroying infrastructure..."

    cd "$INFRA_DIR"
    terraform destroy -var-file=production.tfvars

    log_success "Infrastructure destroyed"
}

# Show status
show_status() {
    log_info "Checking deployment status..."

    cd "$INFRA_DIR"

    if [ -d ".terraform" ]; then
        log_info "Terraform state:"
        terraform state list 2>/dev/null || log_warn "No Terraform state found"

        log_info "Infrastructure outputs:"
        terraform output 2>/dev/null || log_warn "No outputs available"
    else
        log_warn "Infrastructure not initialized"
    fi

    # Check Container App status
    az containerapp show \
        --name panel-app \
        --resource-group panel-rg \
        --query '{name:name, status:properties.configuration.ingress.fqdn}' \
        2>/dev/null || log_warn "Container App not found"
}

# Main function
main() {
    case "$1" in
        "full")
            deploy_full
            ;;
        "update")
            deploy_update
            ;;
        "plan")
            check_prerequisites
            init_infrastructure
            plan_infrastructure
            ;;
        "apply")
            check_prerequisites
            apply_infrastructure
            ;;
        "build")
            check_prerequisites
            build_and_push_image
            ;;
        "deploy")
            check_prerequisites
            deploy_application
            ;;
        "destroy")
            destroy_infrastructure
            ;;
        "status")
            show_status
            ;;
        "health")
            run_health_checks
            ;;
        *)
            echo "Azure Deployment Script for Panel Application"
            echo ""
            echo "Usage: $0 <command>"
            echo ""
            echo "Commands:"
            echo "  full     - Complete infrastructure and application deployment"
            echo "  update   - Update application (existing infrastructure)"
            echo "  plan     - Plan infrastructure changes"
            echo "  apply    - Apply infrastructure changes"
            echo "  build    - Build and push Docker image"
            echo "  deploy   - Deploy application to Container Apps"
            echo "  destroy  - Destroy all infrastructure"
            echo "  status   - Show deployment status"
            echo "  health   - Run health checks"
            echo ""
            echo "Examples:"
            echo "  $0 full          # Complete deployment"
            echo "  $0 update        # Application update"
            echo "  $0 status        # Check status"
            exit 1
            ;;
    esac
}

main "$@"