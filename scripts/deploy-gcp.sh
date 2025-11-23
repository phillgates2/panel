#!/bin/bash
# GCP Deployment Script for Panel Application
# Handles infrastructure provisioning and application deployment

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INFRA_DIR="$PROJECT_ROOT/infrastructure/gcp"
ENV_FILE="$PROJECT_ROOT/.env.gcp"

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

    # Check gcloud CLI
    if ! command -v gcloud >/dev/null 2>&1; then
        log_error "Google Cloud SDK (gcloud) is not installed. Please install it first."
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

    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1; then
        log_error "Not authenticated with Google Cloud. Please run 'gcloud auth login'."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Setup Terraform backend
setup_terraform_backend() {
    log_info "Setting up Terraform backend..."

    # Get project ID from config
    PROJECT_ID=$(grep 'project_id' "$INFRA_DIR/production.tfvars" | cut -d'"' -f2)

    # Create GCS bucket for Terraform state (if it doesn't exist)
    if ! gsutil ls -b "gs://panel-terraform-state" >/dev/null 2>&1; then
        log_info "Creating Terraform state bucket..."
        gsutil mb -p "$PROJECT_ID" "gs://panel-terraform-state"
        gsutil versioning set on "gs://panel-terraform-state"
    fi

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

    # Get project ID
    PROJECT_ID=$(grep 'project_id' "$INFRA_DIR/production.tfvars" | cut -d'"' -f2)

    # Build Docker image
    docker build -f Dockerfile.gcp -t panel:latest .

    # Tag for GCR
    docker tag panel:latest "gcr.io/$PROJECT_ID/panel:latest"

    # Configure Docker to use gcloud as a credential helper
    gcloud auth configure-docker --quiet

    # Push image
    docker push "gcr.io/$PROJECT_ID/panel:latest"

    log_success "Docker image built and pushed"
}

# Deploy application
deploy_application() {
    log_info "Deploying application..."

    # Get project ID and region
    PROJECT_ID=$(grep 'project_id' "$INFRA_DIR/production.tfvars" | cut -d'"' -f2)
    REGION=$(grep 'region' "$INFRA_DIR/production.tfvars" | cut -d'"' -f2 | head -1)

    # The Cloud Run service will automatically pick up the new image
    # since we're using the latest tag

    log_info "Updating Cloud Run service..."

    gcloud run deploy panel-app \
        --image "gcr.io/$PROJECT_ID/panel:latest" \
        --platform managed \
        --region "$REGION" \
        --allow-unauthenticated \
        --port 5000 \
        --memory 512Mi \
        --cpu 1 \
        --max-instances 10 \
        --min-instances 1 \
        --project "$PROJECT_ID"

    log_success "Application deployed"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring..."

    # Get project ID
    PROJECT_ID=$(grep 'project_id' "$INFRA_DIR/production.tfvars" | cut -d'"' -f2)

    # Enable required APIs for monitoring
    gcloud services enable monitoring.googleapis.com --project "$PROJECT_ID"
    gcloud services enable logging.googleapis.com --project "$PROJECT_ID"

    log_success "Monitoring setup completed"
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."

    # Get Cloud Run service URL
    PROJECT_ID=$(grep 'project_id' "$INFRA_DIR/production.tfvars" | cut -d'"' -f2)
    REGION=$(grep 'region' "$INFRA_DIR/production.tfvars" | cut -d'"' -f2 | head -1)

    SERVICE_URL=$(gcloud run services describe panel-app \
        --platform managed \
        --region "$REGION" \
        --project "$PROJECT_ID" \
        --format "value(status.url)")

    # Run health checks
    if curl -f -s "$SERVICE_URL/api/health" >/dev/null 2>&1; then
        log_success "Application health check passed"
    else
        log_error "Application health check failed"
        exit 1
    fi
}

# Create GCP environment file
create_env_file() {
    log_info "Creating GCP environment file..."

    # Get infrastructure outputs
    cd "$INFRA_DIR"
    PROJECT_ID=$(grep 'project_id' production.tfvars | cut -d'"' -f2)
    REGION=$(grep 'region' production.tfvars | cut -d'"' -f2 | head -1)

    # Get service details
    SERVICE_URL=$(gcloud run services describe panel-app \
        --platform managed \
        --region "$REGION" \
        --project "$PROJECT_ID" \
        --format "value(status.url)")

    LOAD_BALANCER_IP=$(terraform output -raw load_balancer_ip 2>/dev/null || echo "")
    STORAGE_BUCKET=$(terraform output -raw storage_bucket 2>/dev/null || echo "")

    # Create .env.gcp
    cat > "$ENV_FILE" << EOF
# Panel GCP Production Environment Configuration
# Generated by deployment script

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY:-"change-this-in-secret-manager"}
DEBUG=false
TESTING=false

# Database Configuration (stored in Secret Manager)
DATABASE_URL=postgresql://panel:${DB_PASSWORD:-"change-this-in-secret-manager"}@DB_PRIVATE_IP:5432/panel

# Redis Configuration (stored in Secret Manager)
REDIS_URL=redis://REDIS_HOST:6379

# Google Cloud Storage Configuration
GCS_BUCKET=$STORAGE_BUCKET
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_REGION=$REGION

# AI Configuration
VERTEX_AI_ENABLED=true
VERTEX_AI_PROJECT=$PROJECT_ID
VERTEX_AI_REGION=$REGION

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
BACKUP_STORAGE_PATH=gs://$STORAGE_BUCKET/backups/

# Logging
LOG_LEVEL=INFO

# GCP-specific settings
SERVICE_URL=$SERVICE_URL
LOAD_BALANCER_IP=$LOAD_BALANCER_IP
EOF

    log_success "GCP environment file created: $ENV_FILE"
}

# Main deployment function
deploy_full() {
    log_info "Starting full GCP deployment..."

    check_prerequisites
    setup_terraform_backend
    init_infrastructure
    plan_infrastructure

    echo
    log_warn "About to apply infrastructure changes. This will create GCP resources and may incur costs."
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
    log_info "Your application should be available at: $(cd "$INFRA_DIR" && terraform output -raw load_balancer_ip)"
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
    log_warn "About to destroy all infrastructure. This will delete all GCP resources!"
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

    # Check Cloud Run service status
    PROJECT_ID=$(grep 'project_id' production.tfvars | cut -d'"' -f2)
    REGION=$(grep 'region' production.tfvars | cut -d'"' -f2 | head -1)

    gcloud run services describe panel-app \
        --platform managed \
        --region "$REGION" \
        --project "$PROJECT_ID" \
        --format "table(name,status.url,spec.template.spec.containers[0].image)" \
        2>/dev/null || log_warn "Cloud Run service not found"
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
            echo "GCP Deployment Script for Panel Application"
            echo ""
            echo "Usage: $0 <command>"
            echo ""
            echo "Commands:"
            echo "  full     - Complete infrastructure and application deployment"
            echo "  update   - Update application (existing infrastructure)"
            echo "  plan     - Plan infrastructure changes"
            echo "  apply    - Apply infrastructure changes"
            echo "  build    - Build and push Docker image to GCR"
            echo "  deploy   - Deploy application to Cloud Run"
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