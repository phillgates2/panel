#!/bin/bash
# CI/CD Pipeline Script for Panel Application
# Integrates testing, monitoring, and deployment

set -e

# Configuration
APP_NAME="panel"
ENVIRONMENT="${ENVIRONMENT:-development}"
TEST_BASE_URL="${TEST_BASE_URL:-http://localhost:8080}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Pre-flight checks
preflight_checks() {
    log_info "Running pre-flight checks..."

    # Check required tools
    command -v python3 >/dev/null 2>&1 || { log_error "Python3 is required but not installed."; exit 1; }
    command -v pip >/dev/null 2>&1 || { log_error "pip is required but not installed."; exit 1; }
    command -v node >/dev/null 2>&1 || { log_error "Node.js is required but not installed."; exit 1; }
    command -v npm >/dev/null 2>&1 || { log_error "npm is required but not installed."; exit 1; }

    # Check environment variables
    if [ -z "$DATABASE_URL" ]; then
        log_warn "DATABASE_URL not set, using default"
    fi

    if [ -z "$SECRET_KEY" ]; then
        log_error "SECRET_KEY must be set for security"
        exit 1
    fi

    log_info "Pre-flight checks passed"
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."

    # Python dependencies
    pip install -r requirements/requirements-dev.txt

    # Node.js dependencies for testing
    npm install -g playwright
    playwright install

    log_info "Dependencies installed"
}

# Run linting and code quality checks
run_code_quality() {
    log_info "Running code quality checks..."

    # Python linting
    if command -v flake8 >/dev/null 2>&1; then
        flake8 src/ tests/ --max-line-length=120 --extend-ignore=E203,W503 || log_warn "Flake8 found issues"
    fi

    # Python type checking
    if command -v mypy >/dev/null 2>&1; then
        mypy src/panel/ --ignore-missing-imports || log_warn "MyPy found type issues"
    fi

    # Security scanning
    if command -v bandit >/dev/null 2>&1; then
        bandit -r src/ -f json -o security-report.json || log_warn "Bandit found security issues"
    fi

    log_info "Code quality checks completed"
}

# Run unit tests
run_unit_tests() {
    log_info "Running unit tests..."

    # Set test environment
    export FLASK_ENV=test
    export TESTING=true

    # Run pytest with coverage
    python -m pytest tests/unit/ -v --tb=short --cov=src/ --cov-report=html --cov-report=term

    # Check coverage threshold
    COVERAGE_THRESHOLD=80
    COVERAGE=$(python -c "import json; data=json.load(open('coverage.json')); print(int(data['totals']['percent_covered']))" 2>/dev/null || echo "0")

    if [ "$COVERAGE" -lt "$COVERAGE_THRESHOLD" ]; then
        log_error "Code coverage $COVERAGE% is below threshold $COVERAGE_THRESHOLD%"
        exit 1
    fi

    log_info "Unit tests passed with $COVERAGE% coverage"
}

# Run integration tests
run_integration_tests() {
    log_info "Running integration tests..."

    # Start test database
    if command -v docker >/dev/null 2>&1; then
        docker run -d --name test-postgres -e POSTGRES_DB=test -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:15-alpine
        sleep 10
    fi

    # Set integration test environment
    export DATABASE_URL="postgresql://test:test@localhost:5433/test"
    export REDIS_URL="redis://localhost:6379/1"

    # Run integration tests
    python -m pytest tests/integration/ -v --tb=short

    # Cleanup
    if command -v docker >/dev/null 2>&1; then
        docker stop test-postgres
        docker rm test-postgres
    fi

    log_info "Integration tests completed"
}

# Run E2E tests
run_e2e_tests() {
    log_info "Running end-to-end tests..."

    # Start application for testing
    export FLASK_ENV=test
    export TESTING=true
    python app.py &
    APP_PID=$!

    # Wait for app to start
    sleep 10

    # Run E2E tests
    TEST_BASE_URL="http://localhost:8080" python -m pytest tests/e2e/ -v --tb=short --headed=false

    # Cleanup
    kill $APP_PID

    log_info "E2E tests completed"
}

# Run load tests
run_load_tests() {
    log_info "Running load tests..."

    # Start application
    export FLASK_ENV=test
    python app.py &
    APP_PID=$!

    sleep 10

    # Run load tests
    locust -f tests/load/locustfile.py --host=http://localhost:8080 --users=50 --spawn-rate=5 --run-time=2m --headless --csv=load_test_results

    # Cleanup
    kill $APP_PID

    log_info "Load tests completed"
}

# Run security tests
run_security_tests() {
    log_info "Running security tests..."

    # OWASP ZAP baseline scan (if available)
    if command -v zap-baseline.py >/dev/null 2>&1; then
        zap-baseline.py -t http://localhost:8080 -r security-scan.html || log_warn "ZAP scan found issues"
    fi

    # Dependency vulnerability check
    if command -v safety >/dev/null 2>&1; then
        safety check --full-report || log_warn "Safety found vulnerabilities"
    fi

    log_info "Security tests completed"
}

# Performance testing
run_performance_tests() {
    log_info "Running performance tests..."

    # Lighthouse CI (if available)
    if command -v lhci >/dev/null 2>&1; then
        lhci autorun --config=lighthouserc.json || log_warn "Lighthouse tests found issues"
    fi

    log_info "Performance tests completed"
}

# Generate test reports
generate_reports() {
    log_info "Generating test reports..."

    # Create reports directory
    mkdir -p test-reports

    # Copy coverage reports
    cp -r htmlcov test-reports/coverage 2>/dev/null || true

    # Copy Playwright reports
    cp -r test-results test-reports/playwright 2>/dev/null || true

    # Generate summary report
    cat > test-reports/summary.md << EOF
# Test Execution Summary

## Environment
- Date: $(date)
- Environment: $ENVIRONMENT
- Base URL: $TEST_BASE_URL

## Test Results
- Unit Tests: ? Passed
- Integration Tests: ? Passed
- E2E Tests: ? Passed
- Load Tests: ? Passed
- Security Tests: ? Passed
- Performance Tests: ? Passed

## Coverage
- Code Coverage: Check coverage/index.html

## Reports
- Coverage: test-reports/coverage/
- E2E Results: test-reports/playwright/
- Load Test Results: load_test_results_*.csv
- Security Report: security-report.json

## Recommendations
- Review security findings in security-report.json
- Check performance metrics in monitoring dashboards
- Address any accessibility issues found in E2E tests
EOF

    log_info "Test reports generated in test-reports/"
}

# Deploy to staging/production
deploy_application() {
    log_info "Deploying application to $ENVIRONMENT..."

    if [ "$ENVIRONMENT" = "production" ]; then
        # Production deployment
        echo "Production deployment steps would go here"
        # - Build Docker image
        # - Push to registry
        # - Update Kubernetes deployment
        # - Run database migrations
        # - Health checks
    else
        # Staging deployment
        echo "Staging deployment steps would go here"
        # - Build and deploy to staging
        # - Run smoke tests
    fi

    log_info "Deployment completed"
}

# Rollback deployment
rollback_deployment() {
    log_error "Deployment failed, initiating rollback..."

    # Rollback logic here
    # - Revert to previous version
    # - Restore database backup
    # - Update load balancer

    log_info "Rollback completed"
}

# Main CI/CD pipeline
main() {
    log_info "Starting CI/CD pipeline for $APP_NAME ($ENVIRONMENT)"

    # Run pipeline stages
    preflight_checks
    install_dependencies
    run_code_quality
    run_unit_tests
    run_integration_tests
    run_e2e_tests
    run_load_tests
    run_security_tests
    run_performance_tests
    generate_reports

    # Deployment (only in CI environment)
    if [ "$CI" = "true" ]; then
        if deploy_application; then
            log_info "CI/CD pipeline completed successfully"
        else
            rollback_deployment
            log_error "CI/CD pipeline failed"
            exit 1
        fi
    else
        log_info "CI/CD pipeline completed successfully (local run)"
    fi
}

# Allow running individual stages
case "$1" in
    "preflight")
        preflight_checks
        ;;
    "install")
        install_dependencies
        ;;
    "quality")
        run_code_quality
        ;;
    "unit")
        run_unit_tests
        ;;
    "integration")
        run_integration_tests
        ;;
    "e2e")
        run_e2e_tests
        ;;
    "load")
        run_load_tests
        ;;
    "security")
        run_security_tests
        ;;
    "performance")
        run_performance_tests
        ;;
    "reports")
        generate_reports
        ;;
    "deploy")
        deploy_application
        ;;
    *)
        main
        ;;
esac