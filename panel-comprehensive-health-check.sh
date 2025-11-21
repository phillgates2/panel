#!/bin/bash
# Panel Health Check Script
# Comprehensive health validation for deployment and monitoring

set -e

# Configuration
PANEL_URL="${PANEL_URL:-http://localhost:8080}"
TIMEOUT="${TIMEOUT:-30}"
RETRIES="${RETRIES:-3}"
VERBOSE="${VERBOSE:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1"
    fi
}

# Health check functions
check_http_response() {
    local url="$1"
    local expected_code="${2:-200}"
    local description="$3"

    log_verbose "Checking HTTP response for $url"

    local response
    response=$(curl -s -w "HTTPSTATUS:%{http_code};TIME:%{time_total}" \
               --max-time "$TIMEOUT" \
               -o /dev/null \
               "$url" 2>/dev/null || echo "HTTPSTATUS:000;TIME:0")

    local http_code
    http_code=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://' -e 's/;TIME.*//')
    local response_time
    response_time=$(echo "$response" | tr -d '\n' | sed -e 's/.*TIME://')

    if [ "$http_code" = "$expected_code" ]; then
        log_success "$description - HTTP $http_code (${response_time}s)"
        return 0
    else
        log_error "$description - HTTP $http_code (expected $expected_code) (${response_time}s)"
        return 1
    fi
}

check_database_connection() {
    log_verbose "Checking database connection"

    # This would need to be adapted based on your database setup
    # For PostgreSQL example:
    if command -v psql >/dev/null 2>&1; then
        if PGPASSWORD="${DB_PASSWORD:-password}" psql -h "${DB_HOST:-localhost}" \
           -U "${DB_USER:-panel}" -d "${DB_NAME:-panel}" \
           -c "SELECT 1;" >/dev/null 2>&1; then
            log_success "Database connection - OK"
            return 0
        else
            log_error "Database connection - FAILED"
            return 1
        fi
    else
        log_warning "psql not available, skipping database check"
        return 0
    fi
}

check_redis_connection() {
    log_verbose "Checking Redis connection"

    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -h "${REDIS_HOST:-localhost}" -p "${REDIS_PORT:-6379}" \
           ping >/dev/null 2>&1; then
            log_success "Redis connection - OK"
            return 0
        else
            log_error "Redis connection - FAILED"
            return 1
        fi
    else
        log_warning "redis-cli not available, skipping Redis check"
        return 0
    fi
}

check_disk_space() {
    local threshold="${1:-90}"
    log_verbose "Checking disk space (threshold: ${threshold}%)"

    local usage
    usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

    if [ "$usage" -lt "$threshold" ]; then
        log_success "Disk space - ${usage}% used"
        return 0
    else
        log_error "Disk space - ${usage}% used (threshold: ${threshold}%)"
        return 1
    fi
}

check_memory_usage() {
    local threshold="${1:-90}"
    log_verbose "Checking memory usage (threshold: ${threshold}%)"

    local usage
    usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')

    if [ "$usage" -lt "$threshold" ]; then
        log_success "Memory usage - ${usage}% used"
        return 0
    else
        log_error "Memory usage - ${usage}% used (threshold: ${threshold}%)"
        return 1
    fi
}

check_cpu_usage() {
    local threshold="${1:-90}"
    log_verbose "Checking CPU usage (threshold: ${threshold}%)"

    local usage
    usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')

    if (( $(echo "$usage < $threshold" | bc -l) )); then
        log_success "CPU usage - ${usage}% used"
        return 0
    else
        log_error "CPU usage - ${usage}% used (threshold: ${threshold}%)"
        return 1
    fi
}

check_ssl_certificate() {
    local domain="$1"
    log_verbose "Checking SSL certificate for $domain"

    if command -v openssl >/dev/null 2>&1; then
        local expiry
        expiry=$(echo | openssl s_client -servername "$domain" -connect "$domain":443 2>/dev/null \
                | openssl x509 -noout -enddate 2>/dev/null \
                | sed 's/notAfter=//' || echo "FAILED")

        if [ "$expiry" != "FAILED" ]; then
            local days_left
            days_left=$(( ($(date -d "$expiry" +%s) - $(date +%s)) / 86400 ))

            if [ "$days_left" -gt 30 ]; then
                log_success "SSL certificate - expires in ${days_left} days"
                return 0
            elif [ "$days_left" -gt 7 ]; then
                log_warning "SSL certificate - expires in ${days_left} days"
                return 0
            else
                log_error "SSL certificate - expires in ${days_left} days"
                return 1
            fi
        else
            log_error "SSL certificate check failed"
            return 1
        fi
    else
        log_warning "openssl not available, skipping SSL check"
        return 0
    fi
}

check_application_logs() {
    local log_file="${1:-/app/logs/panel.log}"
    local max_age="${2:-3600}"  # 1 hour in seconds

    log_verbose "Checking application logs: $log_file"

    if [ -f "$log_file" ]; then
        local file_age
        file_age=$(( $(date +%s) - $(stat -c %Y "$log_file" 2>/dev/null || stat -f %m "$log_file") ))

        if [ "$file_age" -lt "$max_age" ]; then
            # Check for recent errors
            local error_count
            error_count=$(tail -n 100 "$log_file" | grep -i error | wc -l)

            if [ "$error_count" -eq 0 ]; then
                log_success "Application logs - OK (no recent errors)"
                return 0
            else
                log_warning "Application logs - $error_count recent errors"
                return 0
            fi
        else
            log_warning "Application logs - file is old (${file_age}s)"
            return 0
        fi
    else
        log_warning "Application logs - file not found: $log_file"
        return 0
    fi
}

check_background_jobs() {
    log_verbose "Checking background job queues"

    # Check RQ queue status
    if command -v redis-cli >/dev/null 2>&1; then
        local queue_length
        queue_length=$(redis-cli -h "${REDIS_HOST:-localhost}" -p "${REDIS_PORT:-6379}" \
                      LLEN rq:queue:default 2>/dev/null || echo "0")

        if [ "$queue_length" -lt 100 ]; then  # Arbitrary threshold
            log_success "Background jobs - queue length: $queue_length"
            return 0
        else
            log_warning "Background jobs - high queue length: $queue_length"
            return 0
        fi
    else
        log_warning "redis-cli not available, skipping job queue check"
        return 0
    fi
}

# Main health check function
perform_health_check() {
    local failures=0
    local total_checks=0

    log_info "Starting comprehensive health check for Panel application"
    log_info "Target URL: $PANEL_URL"
    echo

    # HTTP endpoint checks
    ((total_checks++))
    if ! check_http_response "$PANEL_URL/health" 200 "Application Health"; then
        ((failures++))
    fi

    ((total_checks++))
    if ! check_http_response "$PANEL_URL/" 200 "Main Application"; then
        ((failures++))
    fi

    ((total_checks++))
    if ! check_http_response "$PANEL_URL/api/v2/servers" 200 "API v2 Servers"; then
        ((failures++))
    fi

    # Infrastructure checks
    ((total_checks++))
    if ! check_database_connection; then
        ((failures++))
    fi

    ((total_checks++))
    if ! check_redis_connection; then
        ((failures++))
    fi

    # System resource checks
    ((total_checks++))
    if ! check_disk_space 90; then
        ((failures++))
    fi

    ((total_checks++))
    if ! check_memory_usage 90; then
        ((failures++))
    fi

    ((total_checks++))
    if ! check_cpu_usage 90; then
        ((failures++))
    fi

    # SSL check (if HTTPS)
    if [[ $PANEL_URL == https://* ]]; then
        local domain
        domain=$(echo "$PANEL_URL" | sed 's|https://||' | sed 's|/.*||')
        ((total_checks++))
        if ! check_ssl_certificate "$domain"; then
            ((failures++))
        fi
    fi

    # Application-specific checks
    ((total_checks++))
    if ! check_application_logs; then
        ((failures++))
    fi

    ((total_checks++))
    if ! check_background_jobs; then
        ((failures++))
    fi

    echo
    log_info "Health check completed: $((total_checks - failures))/$total_checks checks passed"

    if [ $failures -eq 0 ]; then
        log_success "🎉 All health checks passed!"
        return 0
    else
        log_error "❌ $failures health check(s) failed"
        return 1
    fi
}

# Performance test function
run_performance_test() {
    log_info "Running basic performance test"

    local start_time
    start_time=$(date +%s.%3N)

    # Simple load test - multiple concurrent requests
    local concurrent_requests=10
    local total_requests=50

    log_verbose "Making $total_requests requests with $concurrent_requests concurrency"

    # Use curl with parallel requests
    local success_count=0
    local total_time=0

    for i in $(seq 1 "$total_requests"); do
        local response_time
        response_time=$(curl -s -w "%{time_total}" -o /dev/null "$PANEL_URL/health" 2>/dev/null || echo "0")

        if (( $(echo "$response_time > 0" | bc -l) )); then
            ((success_count++))
            total_time=$(echo "$total_time + $response_time" | bc -l)
        fi
    done

    local end_time
    end_time=$(date +%s.%3N)
    local test_duration
    test_duration=$(echo "$end_time - $start_time" | bc -l)

    if [ "$success_count" -gt 0 ]; then
        local avg_response_time
        avg_response_time=$(echo "scale=3; $total_time / $success_count" | bc -l)
        local rps
        rps=$(echo "scale=2; $success_count / $test_duration" | bc -l)

        log_success "Performance test - $success_count/$total_requests successful"
        log_info "Average response time: ${avg_response_time}s"
        log_info "Requests per second: ${rps}"

        # Performance thresholds
        if (( $(echo "$avg_response_time < 0.5" | bc -l) )); then
            log_success "Performance rating: EXCELLENT"
        elif (( $(echo "$avg_response_time < 1.0" | bc -l) )); then
            log_success "Performance rating: GOOD"
        elif (( $(echo "$avg_response_time < 2.0" | bc -l) )); then
            log_success "Performance rating: FAIR"
        else
            log_warning "Performance rating: POOR"
        fi
    else
        log_error "Performance test failed - no successful requests"
        return 1
    fi
}

# Main script execution
main() {
    local exit_code=0

    case "${1:-health}" in
        "health")
            if ! perform_health_check; then
                exit_code=1
            fi
            ;;
        "perf"|"performance")
            if ! run_performance_test; then
                exit_code=1
            fi
            ;;
        "all")
            if ! perform_health_check; then
                exit_code=1
            fi
            echo
            if ! run_performance_test; then
                exit_code=1
            fi
            ;;
        *)
            echo "Usage: $0 [health|perf|all]"
            echo "  health      - Run comprehensive health checks"
            echo "  perf        - Run basic performance test"
            echo "  all         - Run both health checks and performance test"
            echo ""
            echo "Environment variables:"
            echo "  PANEL_URL   - Application URL (default: http://localhost:8080)"
            echo "  TIMEOUT     - Request timeout in seconds (default: 30)"
            echo "  RETRIES     - Number of retries (default: 3)"
            echo "  VERBOSE     - Enable verbose output (default: false)"
            exit 1
            ;;
    esac

    exit $exit_code
}

# Run main function with all arguments
main "$@"