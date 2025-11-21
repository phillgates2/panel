#!/bin/bash
# Docker Setup Validation Script
# Validates Docker configuration and security settings

set -e

echo "🔍 Validating Docker setup for Panel application..."
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Validation functions
validate_docker() {
    echo -n "Checking Docker installation... "
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Docker not found${NC}"
        return 1
    fi
}

validate_docker_compose() {
    echo -n "Checking Docker Compose... "
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Docker Compose not found${NC}"
        return 1
    fi
}

validate_dockerfile() {
    echo -n "Checking Dockerfile... "
    if [ -f "Dockerfile" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Dockerfile not found${NC}"
        return 1
    fi
}

validate_docker_compose_files() {
    echo -n "Checking docker-compose files... "
    if [ -f "docker-compose.yml" ] && [ -f "docker-compose.override.yml" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ Some docker-compose files missing${NC}"
    fi
}

validate_env_file() {
    echo -n "Checking environment configuration... "
    if [ -f ".env.prod.example" ]; then
        if [ -f ".env" ] || [ -f ".env.prod" ]; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${YELLOW}⚠ Environment file not found (copy from .env.prod.example)${NC}"
        fi
    else
        echo -e "${RED}✗ Environment template not found${NC}"
        return 1
    fi
}

validate_nginx_config() {
    echo -n "Checking Nginx configuration... "
    if [ -f "nginx/nginx.conf" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Nginx configuration not found${NC}"
        return 1
    fi
}

validate_ssl_setup() {
    echo -n "Checking SSL certificate setup... "
    if [ -d "nginx/ssl" ]; then
        if [ -f "nginx/ssl/cert.pem" ] && [ -f "nginx/ssl/key.pem" ]; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${YELLOW}⚠ SSL certificates not found${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ SSL directory not found${NC}"
    fi
}

validate_monitoring_config() {
    echo -n "Checking monitoring configuration... "
    local missing_configs=0

    [ ! -f "monitoring/prometheus.yml" ] && ((missing_configs++))
    [ ! -f "monitoring/loki-config.yml" ] && ((missing_configs++))
    [ ! -f "monitoring/promtail-config.yml" ] && ((missing_configs++))
    [ ! -d "monitoring/grafana/dashboards" ] && ((missing_configs++))
    [ ! -d "monitoring/grafana/provisioning" ] && ((missing_configs++))

    if [ $missing_configs -eq 0 ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ $missing_configs monitoring configs missing${NC}"
    fi
}

validate_security() {
    echo -n "Checking security configurations... "
    local issues=0

    # Check if Dockerfile has security features
    if ! grep -q "no-new-privileges" Dockerfile 2>/dev/null; then
        ((issues++))
    fi

    if ! grep -q "USER panel" Dockerfile 2>/dev/null; then
        ((issues++))
    fi

    if [ $issues -eq 0 ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ $issues security issues found${NC}"
    fi
}

test_docker_build() {
    echo -n "Testing Docker build (production)... "
    if docker-compose build --quiet panel 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Build failed${NC}"
        return 1
    fi
}

check_image_size() {
    echo -n "Checking Docker image size... "
    local size
    size=$(docker images panel:latest --format "{{.Size}}" 2>/dev/null | head -1)

    if [ -n "$size" ]; then
        # Convert to MB for comparison
        local size_mb
        size_mb=$(echo "$size" | sed 's/B//g' | numfmt --from=iec --to-unit=1M 2>/dev/null || echo "100")

        if [ "${size_mb%.*}" -lt 500 ]; then
            echo -e "${GREEN}✓ (~${size_mb}MB)${NC}"
        else
            echo -e "${YELLOW}⚠ Large image (~${size_mb}MB)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Could not determine size${NC}"
    fi
}

validate_dependencies() {
    echo -n "Checking Python dependencies... "
    if [ -f "requirements-prod.txt" ] && [ -f "requirements-dev.txt" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Requirements files missing${NC}"
        return 1
    fi
}

# Main validation
main() {
    local failed_checks=0

    echo "Performing pre-flight checks..."
    echo

    # Run all validations
    validate_docker || ((failed_checks++))
    validate_docker_compose || ((failed_checks++))
    validate_dockerfile || ((failed_checks++))
    validate_docker_compose_files
    validate_env_file || ((failed_checks++))
    validate_nginx_config || ((failed_checks++))
    validate_ssl_setup
    validate_monitoring_config
    validate_security
    validate_dependencies || ((failed_checks++))

    echo
    echo "Testing Docker functionality..."
    echo

    test_docker_build || ((failed_checks++))
    check_image_size

    echo
    echo "=================================================="

    if [ $failed_checks -eq 0 ]; then
        echo -e "${GREEN}🎉 All critical checks passed!${NC}"
        echo
        echo "Next steps:"
        echo "1. Copy .env.prod.example to .env and configure your values"
        echo "2. Set up SSL certificates in nginx/ssl/"
        echo "3. Run: docker-compose up -d"
        echo "4. Access your application at https://localhost"
        echo
        exit 0
    else
        echo -e "${RED}❌ $failed_checks critical checks failed${NC}"
        echo
        echo "Please fix the issues above before deploying."
        echo
        exit 1
    fi
}

# Run main function
main "$@"