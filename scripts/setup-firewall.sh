#!/bin/bash

#############################################################################
# Panel Firewall Setup Script
# Configure UFW/iptables for Panel application
#############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Panel Firewall Setup${NC}"
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

# Setup UFW
setup_ufw() {
    info "Setting up UFW firewall..."
    
    if ! command -v ufw &> /dev/null; then
        info "Installing UFW..."
        sudo apt-get update
        sudo apt-get install -y ufw
    fi
    
    # Default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    success "Default policies set"
    
    # SSH (critical - do this first!)
    read -p "SSH port [22]: " SSH_PORT
    SSH_PORT=${SSH_PORT:-22}
    sudo ufw allow ${SSH_PORT}/tcp comment 'SSH'
    success "SSH allowed on port $SSH_PORT"
    
    # HTTP/HTTPS
    sudo ufw allow 80/tcp comment 'HTTP'
    sudo ufw allow 443/tcp comment 'HTTPS'
    success "HTTP/HTTPS allowed"
    
    # Panel application (if not behind nginx)
    read -p "Allow direct access to Panel port 5000? (yes/no) [no]: " ALLOW_DIRECT
    if [[ "$ALLOW_DIRECT" == "yes" ]]; then
        sudo ufw allow 5000/tcp comment 'Panel'
        success "Panel port 5000 allowed"
    fi
    
    # Database ports (only if external access needed)
    read -p "Allow external PostgreSQL access? (yes/no) [no]: " ALLOW_PG
    if [[ "$ALLOW_PG" == "yes" ]]; then
        read -p "PostgreSQL IP range [10.0.0.0/8]: " PG_RANGE
        PG_RANGE=${PG_RANGE:-10.0.0.0/8}
        sudo ufw allow from ${PG_RANGE} to any port 5432 proto tcp comment 'PostgreSQL'
        success "PostgreSQL allowed from $PG_RANGE"
    fi
    
    read -p "Allow external Redis access? (yes/no) [no]: " ALLOW_REDIS
    if [[ "$ALLOW_REDIS" == "yes" ]]; then
        read -p "Redis IP range [10.0.0.0/8]: " REDIS_RANGE
        REDIS_RANGE=${REDIS_RANGE:-10.0.0.0/8}
        sudo ufw allow from ${REDIS_RANGE} to any port 6379 proto tcp comment 'Redis'
        success "Redis allowed from $REDIS_RANGE"
    fi
    
    # Monitoring ports (if enabled)
    read -p "Allow monitoring access (Prometheus/Grafana)? (yes/no) [no]: " ALLOW_MON
    if [[ "$ALLOW_MON" == "yes" ]]; then
        sudo ufw allow 9090/tcp comment 'Prometheus'
        sudo ufw allow 3000/tcp comment 'Grafana'
        success "Monitoring ports allowed"
    fi
    
    # Rate limiting for SSH
    info "Setting up rate limiting for SSH..."
    sudo ufw limit ${SSH_PORT}/tcp comment 'Rate limit SSH'
    success "SSH rate limiting enabled"
    
    # Enable UFW
    sudo ufw --force enable
    
    success "UFW firewall enabled"
}

# Setup iptables
setup_iptables() {
    info "Setting up iptables firewall..."
    
    # Flush existing rules
    sudo iptables -F
    sudo iptables -X
    sudo iptables -t nat -F
    sudo iptables -t nat -X
    sudo iptables -t mangle -F
    sudo iptables -t mangle -X
    
    # Default policies
    sudo iptables -P INPUT DROP
    sudo iptables -P FORWARD DROP
    sudo iptables -P OUTPUT ACCEPT
    
    # Allow loopback
    sudo iptables -A INPUT -i lo -j ACCEPT
    sudo iptables -A OUTPUT -o lo -j ACCEPT
    
    # Allow established connections
    sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    
    # SSH
    read -p "SSH port [22]: " SSH_PORT
    SSH_PORT=${SSH_PORT:-22}
    sudo iptables -A INPUT -p tcp --dport ${SSH_PORT} -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
    
    # SSH rate limiting
    sudo iptables -A INPUT -p tcp --dport ${SSH_PORT} -m conntrack --ctstate NEW -m recent --set
    sudo iptables -A INPUT -p tcp --dport ${SSH_PORT} -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 4 -j DROP
    
    # HTTP/HTTPS
    sudo iptables -A INPUT -p tcp --dport 80 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
    sudo iptables -A INPUT -p tcp --dport 443 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
    
    # Panel application (optional)
    read -p "Allow direct access to Panel port 5000? (yes/no) [no]: " ALLOW_DIRECT
    if [[ "$ALLOW_DIRECT" == "yes" ]]; then
        sudo iptables -A INPUT -p tcp --dport 5000 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
    fi
    
    # Drop invalid packets
    sudo iptables -A INPUT -m conntrack --ctstate INVALID -j DROP
    
    # Protection against common attacks
    # SYN flood protection
    sudo iptables -N syn_flood
    sudo iptables -A INPUT -p tcp --syn -j syn_flood
    sudo iptables -A syn_flood -m limit --limit 1/s --limit-burst 3 -j RETURN
    sudo iptables -A syn_flood -j DROP
    
    # Ping flood protection
    sudo iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s --limit-burst 2 -j ACCEPT
    sudo iptables -A INPUT -p icmp --icmp-type echo-request -j DROP
    
    # Save rules
    if command -v netfilter-persistent &> /dev/null; then
        sudo netfilter-persistent save
    elif command -v iptables-save &> /dev/null; then
        sudo iptables-save > /etc/iptables/rules.v4
    fi
    
    success "iptables firewall configured"
}

# Setup fail2ban
setup_fail2ban() {
    info "Setting up fail2ban..."
    
    if ! command -v fail2ban-client &> /dev/null; then
        info "Installing fail2ban..."
        if [[ -f /etc/debian_version ]]; then
            sudo apt-get update
            sudo apt-get install -y fail2ban
        elif [[ -f /etc/redhat-release ]]; then
            sudo yum install -y epel-release
            sudo yum install -y fail2ban
        fi
    fi
    
    # Panel jail configuration
    sudo tee /etc/fail2ban/jail.d/panel.conf > /dev/null << EOF
[panel]
enabled = true
port = 80,443,5000
filter = panel
logpath = /opt/panel/logs/*.log
maxretry = 5
bantime = 3600
findtime = 600

[panel-auth]
enabled = true
port = 80,443,5000
filter = panel-auth
logpath = /opt/panel/logs/*.log
maxretry = 3
bantime = 86400
findtime = 600
EOF
    
    # Panel filter for failed logins
    sudo tee /etc/fail2ban/filter.d/panel.conf > /dev/null << EOF
[Definition]
failregex = ^.*Failed login attempt.*from <HOST>.*$
            ^.*Authentication failed.*<HOST>.*$
            ^.*Invalid credentials.*<HOST>.*$
ignoreregex =
EOF
    
    # Panel authentication filter
    sudo tee /etc/fail2ban/filter.d/panel-auth.conf > /dev/null << EOF
[Definition]
failregex = ^.*POST /login.*401.*<HOST>.*$
            ^.*POST /api/auth.*401.*<HOST>.*$
ignoreregex =
EOF
    
    sudo systemctl enable fail2ban
    sudo systemctl restart fail2ban
    
    success "fail2ban configured and started"
}

# Show firewall status
show_status() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Firewall Status${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
    
    if command -v ufw &> /dev/null; then
        echo -e "${BLUE}UFW Status:${NC}"
        sudo ufw status verbose
    fi
    
    if command -v iptables &> /dev/null; then
        echo
        echo -e "${BLUE}iptables Rules:${NC}"
        sudo iptables -L -n -v
    fi
    
    if command -v fail2ban-client &> /dev/null; then
        echo
        echo -e "${BLUE}fail2ban Status:${NC}"
        sudo fail2ban-client status
    fi
}

# Main
main() {
    print_header
    
    # Detect firewall preference
    if command -v ufw &> /dev/null || [[ -f /etc/debian_version ]]; then
        FIREWALL="ufw"
    else
        FIREWALL="iptables"
    fi
    
    read -p "Use $FIREWALL for firewall? (yes/no) [yes]: " USE_DEFAULT
    USE_DEFAULT=${USE_DEFAULT:-yes}
    
    if [[ "$USE_DEFAULT" != "yes" ]]; then
        read -p "Enter firewall type (ufw/iptables): " FIREWALL
    fi
    
    case "$FIREWALL" in
        ufw)
            setup_ufw
            ;;
        iptables)
            setup_iptables
            ;;
        *)
            error "Unknown firewall type: $FIREWALL"
            ;;
    esac
    
    # Setup fail2ban
    read -p "Setup fail2ban? (yes/no) [yes]: " SETUP_F2B
    SETUP_F2B=${SETUP_F2B:-yes}
    
    if [[ "$SETUP_F2B" == "yes" ]]; then
        setup_fail2ban
    fi
    
    show_status
    
    echo
    success "Firewall setup complete!"
    warn "Make sure you can still access the server via SSH!"
}

main "$@"
