#!/bin/bash

#############################################################################
# Panel Monitoring Setup Script
# Configure Prometheus and Grafana integration
#############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="${1:-/opt/panel}"
PROMETHEUS_PORT="${PROMETHEUS_PORT:-9090}"
GRAFANA_PORT="${GRAFANA_PORT:-3000}"

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Panel Monitoring Setup${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

error() {
    echo -e "${RED}Error: $1${NC}"
    exit 1
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

warn() {
    echo -e "${YELLOW}! $1${NC}"
}

# Install Prometheus
install_prometheus() {
    info "Installing Prometheus..."
    
    if command -v prometheus &> /dev/null; then
        success "Prometheus already installed"
        return
    fi
    
    PROMETHEUS_VERSION="2.45.0"
    
    cd /tmp
    wget "https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz"
    tar xzf "prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz"
    
    sudo mv prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus /usr/local/bin/
    sudo mv prometheus-${PROMETHEUS_VERSION}.linux-amd64/promtool /usr/local/bin/
    sudo mkdir -p /etc/prometheus /var/lib/prometheus
    
    rm -rf prometheus-${PROMETHEUS_VERSION}*
    
    success "Prometheus installed"
}

# Configure Prometheus
configure_prometheus() {
    info "Configuring Prometheus..."
    
    sudo tee /etc/prometheus/prometheus.yml > /dev/null << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'panel'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']
      
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
      
  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']

rule_files:
  - '/etc/prometheus/rules/*.yml'
EOF
    
    sudo mkdir -p /etc/prometheus/rules
    
    success "Prometheus configured"
}

# Create Prometheus systemd service
create_prometheus_service() {
    info "Creating Prometheus service..."
    
    sudo tee /etc/systemd/system/prometheus.service > /dev/null << EOF
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \\
    --config.file=/etc/prometheus/prometheus.yml \\
    --storage.tsdb.path=/var/lib/prometheus/ \\
    --web.console.templates=/etc/prometheus/consoles \\
    --web.console.libraries=/etc/prometheus/console_libraries \\
    --web.listen-address=0.0.0.0:${PROMETHEUS_PORT}

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    sudo useradd --no-create-home --shell /bin/false prometheus 2>/dev/null || true
    sudo chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus
    
    sudo systemctl daemon-reload
    sudo systemctl enable prometheus
    sudo systemctl start prometheus
    
    success "Prometheus service created and started"
}

# Install Grafana
install_grafana() {
    info "Installing Grafana..."
    
    if command -v grafana-server &> /dev/null; then
        success "Grafana already installed"
        return
    fi
    
    # Add Grafana repository
    if [[ -f /etc/debian_version ]]; then
        sudo apt-get install -y apt-transport-https software-properties-common
        sudo wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key
        echo "deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
        sudo apt-get update
        sudo apt-get install -y grafana
    elif [[ -f /etc/redhat-release ]]; then
        sudo tee /etc/yum.repos.d/grafana.repo > /dev/null << EOF
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
        sudo yum install -y grafana
    fi
    
    sudo systemctl daemon-reload
    sudo systemctl enable grafana-server
    sudo systemctl start grafana-server
    
    success "Grafana installed and started"
}

# Install Node Exporter
install_node_exporter() {
    info "Installing Node Exporter..."
    
    if command -v node_exporter &> /dev/null; then
        success "Node Exporter already installed"
        return
    fi
    
    NODE_EXPORTER_VERSION="1.6.1"
    
    cd /tmp
    wget "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
    tar xzf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
    
    sudo mv node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter /usr/local/bin/
    
    rm -rf node_exporter-${NODE_EXPORTER_VERSION}*
    
    # Create systemd service
    sudo tee /etc/systemd/system/node_exporter.service > /dev/null << EOF
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    sudo useradd --no-create-home --shell /bin/false node_exporter 2>/dev/null || true
    
    sudo systemctl daemon-reload
    sudo systemctl enable node_exporter
    sudo systemctl start node_exporter
    
    success "Node Exporter installed and started"
}

# Install Redis Exporter
install_redis_exporter() {
    info "Installing Redis Exporter..."
    
    REDIS_EXPORTER_VERSION="1.55.0"
    
    cd /tmp
    wget "https://github.com/oliver006/redis_exporter/releases/download/v${REDIS_EXPORTER_VERSION}/redis_exporter-v${REDIS_EXPORTER_VERSION}.linux-amd64.tar.gz"
    tar xzf "redis_exporter-v${REDIS_EXPORTER_VERSION}.linux-amd64.tar.gz"
    
    sudo mv redis_exporter-v${REDIS_EXPORTER_VERSION}.linux-amd64/redis_exporter /usr/local/bin/
    
    rm -rf redis_exporter-v${REDIS_EXPORTER_VERSION}*
    
    # Create systemd service
    sudo tee /etc/systemd/system/redis_exporter.service > /dev/null << EOF
[Unit]
Description=Redis Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=redis_exporter
Group=redis_exporter
Type=simple
ExecStart=/usr/local/bin/redis_exporter

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    sudo useradd --no-create-home --shell /bin/false redis_exporter 2>/dev/null || true
    
    sudo systemctl daemon-reload
    sudo systemctl enable redis_exporter
    sudo systemctl start redis_exporter
    
    success "Redis Exporter installed and started"
}

# Add Flask metrics endpoint
add_flask_metrics() {
    info "Adding metrics endpoint to Panel..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Install prometheus-flask-exporter
    pip install prometheus-flask-exporter
    
    success "Flask metrics configured"
    warn "Add 'from prometheus_flask_exporter import PrometheusMetrics' to app/__init__.py"
    warn "Add 'metrics = PrometheusMetrics(app)' after app creation"
}

# Create alert rules
create_alert_rules() {
    info "Creating Prometheus alert rules..."
    
    sudo tee /etc/prometheus/rules/panel.yml > /dev/null << 'EOF'
groups:
  - name: panel
    interval: 30s
    rules:
      - alert: PanelDown
        expr: up{job="panel"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Panel is down"
          description: "Panel application has been down for more than 2 minutes"
          
      - alert: HighResponseTime
        expr: flask_http_request_duration_seconds_sum / flask_http_request_duration_seconds_count > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time"
          description: "Average response time is {{ $value }}s"
          
      - alert: HighErrorRate
        expr: rate(flask_http_request_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate"
          description: "Error rate is {{ $value }} errors/sec"
          
      - alert: DatabaseConnectionFailure
        expr: increase(flask_http_request_total{endpoint="/health"}[5m]) == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection issues"
          
      - alert: HighMemoryUsage
        expr: (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Available memory is {{ $value }}%"
          
      - alert: HighDiskUsage
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High disk usage"
          description: "Available disk space is {{ $value }}%"
EOF
    
    sudo chown prometheus:prometheus /etc/prometheus/rules/panel.yml
    sudo systemctl reload prometheus
    
    success "Alert rules created"
}

# Create Grafana dashboard
create_grafana_dashboard() {
    info "Creating Grafana dashboard..."
    
    cat > /tmp/panel-dashboard.json << 'EOF'
{
  "dashboard": {
    "title": "Panel Application Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{"expr": "rate(flask_http_request_total[5m])"}]
      },
      {
        "title": "Response Time",
        "targets": [{"expr": "flask_http_request_duration_seconds_sum / flask_http_request_duration_seconds_count"}]
      },
      {
        "title": "Error Rate",
        "targets": [{"expr": "rate(flask_http_request_total{status=~\"5..\"}[5m])"}]
      },
      {
        "title": "CPU Usage",
        "targets": [{"expr": "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)"}]
      },
      {
        "title": "Memory Usage",
        "targets": [{"expr": "100 - ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100)"}]
      },
      {
        "title": "Disk Usage",
        "targets": [{"expr": "100 - ((node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100)"}]
      }
    ]
  }
}
EOF
    
    success "Dashboard template created at /tmp/panel-dashboard.json"
    info "Import this dashboard in Grafana UI"
}

# Print summary
print_summary() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Setup Complete${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
    echo "Prometheus: http://localhost:${PROMETHEUS_PORT}"
    echo "Grafana: http://localhost:${GRAFANA_PORT} (admin/admin)"
    echo
    echo "Next steps:"
    echo "  1. Configure Prometheus data source in Grafana"
    echo "  2. Import dashboard from /tmp/panel-dashboard.json"
    echo "  3. Add metrics to Panel application"
    echo "  4. Configure alert notifications"
}

# Main
main() {
    print_header
    
    install_prometheus
    configure_prometheus
    create_prometheus_service
    install_grafana
    install_node_exporter
    install_redis_exporter
    add_flask_metrics
    create_alert_rules
    create_grafana_dashboard
    
    print_summary
}

main "$@"
