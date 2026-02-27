# Panel Scripts Directory

This directory contains utility scripts for managing the Panel application.

> Note: The Panel application/runtime is PostgreSQL-only. Some older scripts and documentation in this directory still mention SQLite; treat those references as legacy/historical.

## Installation & Setup

### 📦 install-interactive.sh
**Interactive installer for Panel application**

```bash
# Interactive installation
bash scripts/install-interactive.sh

# Non-interactive (CI/CD)
bash scripts/install-interactive.sh --non-interactive

# Development mode
bash scripts/install-interactive.sh --dev

# Docker installation
bash scripts/install-interactive.sh --docker

# Configuration wizard
bash scripts/install-interactive.sh --wizard

# Cloud provider presets
bash scripts/install-interactive.sh --cloud=aws
bash scripts/install-interactive.sh --cloud=gcp
bash scripts/install-interactive.sh --cloud=azure
bash scripts/install-interactive.sh --cloud=digitalocean

# Offline installation
bash scripts/install-interactive.sh --offline

# With integration tests
bash scripts/install-interactive.sh --test

# Migrate from another panel
bash scripts/install-interactive.sh --migrate

# Dry run (preview)
bash scripts/install-interactive.sh --dry-run

# Get help
bash scripts/install-interactive.sh --help
```

**Features:**
- Interactive prompts for configuration
- System requirements validation (integrated preflight checks)
- Multi-version Python support (3.8-3.12)
- Database setup (PostgreSQL or external PostgreSQL)
- Redis installation and configuration (local, external, or cluster)
- Virtual environment creation
- Admin user creation
- Production service setup (systemd, nginx, SSL)
- Comprehensive health checks
- Development mode with hot reload
- Docker Compose installation
- **Automatic rollback on failure**
- **Progress tracking with visual progress bars**
- **Installation timer and elapsed time display**
- **Cloud provider optimization**
- **Offline installation support**
- **Integration testing**
- **Migration from other panels**
- **Dependency conflict resolution**
- **Configuration wizard mode**

**Options:**
- `--dry-run` - Show what would be installed
- `--non-interactive` - Use defaults for automation
- `--dev` - Setup development environment with debugging tools
- `--docker` - Install using Docker Compose
- `--wizard` - Advanced configuration wizard with performance tuning, security, monitoring, backups
- `--cloud=PROVIDER` - Optimize for cloud provider (aws, gcp, azure, digitalocean)
- `--offline` - Install from offline package cache (requires create-offline-cache.sh)
- `--test` - Run integration tests after installation
- `--migrate` - Import configuration from another panel (Pterodactyl, cPanel, Plesk, etc.)
- `--help` - Display usage information

**Rollback Capability:**
- Automatic rollback on any error
- Tracks all changes (directories, services, database)
- Restores previous state on failure
- Manual cleanup if needed

**Multi-Version Python:**
- Automatically detects Python 3.8-3.12
- Searches for alternative installations
- Interactive selection if current version incompatible
- Version-specific optimizations (PYTHONOPTIMIZE=2 for 3.11+)
- Python 3.12 compatibility handling

**Cloud Presets:**
Each preset automatically configures:
- Environment: Production
- Database: PostgreSQL
- Redis: Local installation
- Cloud-specific environment variables
- Optimized settings for the platform

**Migration Sources:**
1. Pterodactyl Panel
2. ApisCP
3. cPanel/WHM
4. Plesk
5. Custom (manual configuration)

---

### 🗄️ create-offline-cache.sh
**Create offline package cache for air-gapped installations**

```bash
# Create offline cache in default location
bash scripts/create-offline-cache.sh

# Custom cache directory
bash scripts/create-offline-cache.sh -d /path/to/cache

# Specify Python version
bash scripts/create-offline-cache.sh -p 3.11

# All options
bash scripts/create-offline-cache.sh -d offline-packages -r /path/to/repo -p 3.10
```

**Features:**
- Downloads all Python dependencies
- Includes development and production packages
- Creates README with usage instructions
- Reports cache size and file count
- Supports custom Python version

**Options:**
- `-d, --dir DIR` - Output directory (default: offline-packages)
- `-r, --repo DIR` - Repository directory (default: current)
- `-p, --python VER` - Python version (default: 3.10)
- `-h, --help` - Show help

**Usage Workflow:**
1. On connected machine: `./scripts/create-offline-cache.sh`
2. Copy `offline-packages/` to target machine
3. On target machine: `./scripts/install-interactive.sh --offline`

---

## Testing & Validation

### ✅ preflight-check.sh
**Validate system requirements before installation**

```bash
# Run preflight checks
bash scripts/preflight-check.sh

# Check with custom directory
bash scripts/preflight-check.sh /custom/path
```

**Checks:**
- Operating system compatibility
- System architecture
- Python version (>= 3.8)
- Git availability
- Disk space (>= 2GB)
- Memory (>= 1GB)
- Network connectivity
- Port availability (5000, 80, 443, etc.)
- Optional dependencies (PostgreSQL, Redis, nginx, Docker)
- Write permissions

---

### 🧪 post-install-test.sh
**Automated test suite after installation**

```bash
# Run post-installation tests
bash scripts/post-install-test.sh

# Test specific directory
bash scripts/post-install-test.sh /path/to/panel
```

**Tests:**
- Virtual environment setup
- Python dependencies
- Configuration files
- Database connectivity
- Redis connection
- Application startup
- CLI commands
- Static files
- Templates
- Helper scripts
- Systemd service
- Nginx configuration
- Application endpoints

---

### 🔍 validate-config.sh
**Validate configuration against best practices**

```bash
# Validate default config
bash scripts/validate-config.sh

# Validate specific file
bash scripts/validate-config.sh /path/to/config.py
```

**Validations:**
- Python syntax
- Required settings (SECRET_KEY, DATABASE_URI, REDIS_URL)
- SECRET_KEY strength
- Database configuration
- Redis setup
- Debug mode (should be off in production)
- Security headers
- Email configuration
- Logging setup
- Performance settings
- Environment configuration
- Hardcoded credentials check

---

## Status & Monitoring

### 📊 status.sh
**Check Panel application status and health**

```bash
# Check default installation
bash scripts/status.sh

# Check specific directory
bash scripts/status.sh /path/to/panel
```

**Checks:**
- Virtual environment
- Configuration files
- Database status
- Redis connectivity
- Application running status
- Systemd service status
- Nginx configuration
- Disk usage
- Log files

---

## Maintenance

### 🗑️ uninstall.sh
**Safely remove Panel application**

```bash
bash scripts/uninstall.sh
```

**Features:**
- Optional backup before removal
- PostgreSQL database cleanup
- Systemd service removal
- Nginx configuration cleanup
- Redis data flush option
- Safe removal with confirmation

---

## Deployment

### ☁️ deploy-aws.sh
**Deploy to AWS (ECS, RDS, ElastiCache)**

```bash
bash scripts/deploy-aws.sh
```

### ☁️ deploy-azure.sh
**Deploy to Azure (App Service, PostgreSQL, Redis)**

```bash
bash scripts/deploy-azure.sh
```

### ☁️ deploy-gcp.sh
**Deploy to Google Cloud Platform**

```bash
bash scripts/deploy-gcp.sh
```

---

## Backup & Recovery

### 💾 manage-backups.sh
**Backup and restore Panel data**

```bash
# Create backup
bash scripts/manage-backups.sh backup

# List backups
bash scripts/manage-backups.sh list

# Restore from backup
bash scripts/manage-backups.sh restore backup_20231202_120000

# Cleanup old backups
bash scripts/manage-backups.sh cleanup --days 30
```

---

## Configuration

### ⚙️ manage-config.sh
**Manage Panel configuration**

```bash
# Show current configuration
bash scripts/manage-config.sh show

# Update configuration
bash scripts/manage-config.sh update

# Validate configuration
bash scripts/manage-config.sh validate

# Reset to defaults
bash scripts/manage-config.sh reset
```

---

## CI/CD

### 🔄 ci-cd-pipeline.sh
**Automated CI/CD pipeline**

```bash
bash scripts/ci-cd-pipeline.sh
```

**Features:**
- Code quality checks
- Automated testing
- Build process
- Deployment automation
- Rollback capabilities

---

## Dependencies

### 📦 update-dependencies.sh
**Update Python dependencies safely**

```bash
# Check for updates
bash scripts/update-dependencies.sh check

# Update all dependencies
bash scripts/update-dependencies.sh update

# Update specific package
bash scripts/update-dependencies.sh update flask

# Security audit
bash scripts/update-dependencies.sh audit
```

---

## Helper Scripts (Created During Installation)

These scripts are created in the installation directory during setup:

### ▶️ start.sh
**Start the application**
```bash
./start.sh
```
- Activates virtual environment
- Loads environment variables
- Checks port availability
- Starts Flask application

### 🧪 test.sh
**Run application tests**
```bash
./test.sh
```
- Runs pytest test suite
- Shows test coverage
- Identifies failing tests

### 📊 status.sh (copy)
**Quick status check**
```bash
./status.sh
```
- Local copy of status script
- Checks application health
- Shows service status

### 🗑️ uninstall.sh (copy)
**Uninstall Panel**
```bash
./uninstall.sh
```
- Local copy of uninstall script
- Safe removal process
- Optional backup creation

---

## Database Management

### 🔄 migrate-db.sh
**Migrate between SQLite and PostgreSQL**

> Note: Panel is PostgreSQL-only. SQLite migrations are legacy and are not part of the supported runtime configuration.

```bash
# Interactive migration
bash scripts/migrate-db.sh

# Migrate to PostgreSQL
bash scripts/migrate-db.sh --to-postgresql localhost 5432 panel panel password

# (Legacy) Migrate to SQLite
# bash scripts/migrate-db.sh --to-sqlite ./panel.db

# Backup only
bash scripts/migrate-db.sh --backup
```

**Features:**
- Export/import data between databases
- Automatic backups before migration
- Config file updates
- Schema migration with Flask-Migrate

---

## Backup & Recovery

### 💾 backup.sh
**Automated backup of Panel application**

```bash
# Create backup
bash scripts/backup.sh

# List backups
bash scripts/backup.sh --list

# Restore from backup
bash scripts/backup.sh --restore /var/backups/panel/panel_backup_20250101.tar.gz

# Cleanup old backups
bash scripts/backup.sh --cleanup
```

**Backup includes:**
- Configuration files (config.py, .env)
- Database (PostgreSQL dump)
- Uploaded files
- Custom static files
- Logs
- Systemd service
- Nginx configuration

**Environment variables:**
- `PANEL_BACKUP_DIR` - Backup directory (default: /var/backups/panel)
- `PANEL_BACKUP_RETENTION` - Days to keep backups (default: 30)
- `PANEL_BACKUP_COMPRESS` - Compress backups (default: true)

---

## Security

### 🔒 security-harden.sh
**Apply security best practices**

```bash
bash scripts/security-harden.sh [/path/to/panel]
```

**Security measures:**
- Secure file permissions (640/750)
- Disable debug mode
- Generate strong SECRET_KEY
- Configure secure cookies
- Enable CSRF protection
- Setup rate limiting
- Database SSL enforcement
- Security headers (nginx)
- Audit logging
- Redis password protection
- Remove test accounts
- Dependency vulnerability scan

**Creates:** `SECURITY_CHECKLIST.md` for manual review

---

### 🔥 setup-firewall.sh
**Configure firewall rules**

```bash
bash scripts/setup-firewall.sh
```

**Features:**
- UFW or iptables configuration
- SSH port protection with rate limiting
- HTTP/HTTPS access
- Database/Redis access control
- fail2ban integration
- Attack protection (SYN flood, ping flood)

---

### 🔐 setup-ssl-renewal.sh
**Configure SSL certificate auto-renewal**

```bash
bash scripts/setup-ssl-renewal.sh
```

**Features:**
- Install certbot
- Obtain Let's Encrypt certificates
- Automatic renewal timer (systemd)
- Renewal hooks (pre/post/deploy)
- Nginx SSL configuration
- Expiration monitoring
- Email notifications

---

## Monitoring & Observability

### 📈 setup-monitoring.sh
**Setup Prometheus and Grafana**

```bash
bash scripts/setup-monitoring.sh
```

**Installs:**
- Prometheus (metrics collection)
- Grafana (visualization)
- Node Exporter (system metrics)
- Redis Exporter
- Flask metrics endpoint

**Includes:**
- Alert rules for Panel
- Pre-built Grafana dashboard
- Health checks
- Performance monitoring

**Access:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

---

## Updates

### 🔄 check-updates.sh
**Check for Panel updates**

```bash
# Check for updates
bash scripts/check-updates.sh

# Update to latest version
bash scripts/check-updates.sh --update

# Update to specific version
bash scripts/check-updates.sh --update v1.2.3

# View changelog
bash scripts/check-updates.sh --changelog

# Setup auto-check (cron)
bash scripts/check-updates.sh --setup-auto
```

**Features:**
- Check GitHub releases
- Compare current vs latest version
- View release notes
- Automatic updates
- Backup before update
- Post-update testing

---

## Multi-Server Deployment

### 🌐 setup-distributed.sh
**Configure distributed architecture**

```bash
# Interactive setup
bash scripts/setup-distributed.sh

# Setup application server
bash scripts/setup-distributed.sh --app-server DB_HOST REDIS_HOST

# Setup database server
bash scripts/setup-distributed.sh --db-server

# Setup Redis server
bash scripts/setup-distributed.sh --redis-server

# Generate config template
bash scripts/setup-distributed.sh --generate-config
```

**Supports:**
- Separate app/database/Redis servers
- Load balancer configuration
- Celery workers
- Monitoring servers

---

### ⚖️ generate-lb-config.sh
**Generate load balancer configuration**

```bash
# Interactive
bash scripts/generate-lb-config.sh

# Nginx config
bash scripts/generate-lb-config.sh --nginx panel.example.com 10.0.1.20:5000 10.0.1.21:5000

# HAProxy config
bash scripts/generate-lb-config.sh --haproxy 10.0.1.20:5000 10.0.1.21:5000
```

**Features:**
- Nginx or HAProxy configs
- Round-robin/least-conn/ip-hash balancing
- Health checks
- SSL termination
- Rate limiting
- WebSocket support
- Static file caching

---

### 🔗 setup-cluster.sh
**Setup multi-instance cluster**

```bash
# Interactive cluster setup
bash scripts/setup-cluster.sh

# Add cluster node
bash scripts/setup-cluster.sh --add-node 4

# Remove cluster node
bash scripts/setup-cluster.sh --remove-node 3

# Check cluster health
bash scripts/setup-cluster.sh --health
```

**Features:**
- Multiple Panel instances
- Shared database and Redis
- Session sharing across instances
- Load balancer auto-configuration
- Health monitoring
- Easy scaling (add/remove nodes)

---

## Helper Scripts (Created by Installer)

These scripts are created in the Panel installation directory:

### 🚀 start.sh
**Start Panel application**
```bash
./start.sh
```
- Checks port availability
- Starts Flask application

### 🧪 test.sh
**Run application tests**
```bash
./test.sh
```
- Runs pytest test suite
- Shows test coverage
- Identifies failing tests

### 📊 status.sh (copy)
**Quick status check**
```bash
./status.sh
```
- Local copy of status script
- Checks application health
- Shows service status

### 🗑️ uninstall.sh (copy)
**Uninstall Panel**
```bash
./uninstall.sh
```
- Local copy of uninstall script
- Safe removal process
- Optional backup creation

### 🛠️ dev.sh (development mode only)
**Development helper script**
```bash
# Run dev server with hot reload
./dev.sh run

# Run tests
./dev.sh test

# Run linters
./dev.sh lint

# Format code
./dev.sh format

# Open Flask shell
./dev.sh shell
```

---

## Common Workflows

### Fresh Installation
```bash
# 1. Run preflight check
bash scripts/preflight-check.sh

# 2. Install Panel
bash scripts/install-interactive.sh

# 3. Validate installation
bash scripts/post-install-test.sh

# 4. Harden security
bash scripts/security-harden.sh

# 5. Setup firewall
bash scripts/setup-firewall.sh

# 6. Setup SSL
bash scripts/setup-ssl-renewal.sh

# 7. Setup monitoring
bash scripts/setup-monitoring.sh
```

### Production Deployment
```bash
# 1. Install with production settings
bash scripts/install-interactive.sh

# 2. Harden security
bash scripts/security-harden.sh

# 3. Setup firewall and SSL
bash scripts/setup-firewall.sh
bash scripts/setup-ssl-renewal.sh

# 4. Setup monitoring
bash scripts/setup-monitoring.sh

# 5. Configure backups
bash scripts/backup.sh
```

### Development Setup
```bash
# Install in development mode
bash scripts/install-interactive.sh --dev

# Use development helper
./dev.sh run
```

### Docker Deployment
```bash
# Install via Docker
bash scripts/install-interactive.sh --docker
```

### Distributed Deployment
```bash
# 1. Setup database server
bash scripts/setup-distributed.sh --db-server

# 2. Setup Redis server  
bash scripts/setup-distributed.sh --redis-server

# 3. Setup application servers
bash scripts/setup-distributed.sh --app-server DB_IP REDIS_IP

# 4. Generate load balancer config
bash scripts/generate-lb-config.sh

# 5. Setup monitoring
bash scripts/setup-monitoring.sh
```

### Cluster Deployment
```bash
# Setup 3-node cluster
bash scripts/setup-cluster.sh

# Add more nodes as needed
bash scripts/setup-cluster.sh --add-node 4
```

### Update & Maintenance
```bash
# Check for updates
bash scripts/check-updates.sh

# Create backup
bash scripts/backup.sh

# Update Panel
bash scripts/check-updates.sh --update

# Verify installation
bash scripts/post-install-test.sh
```

### Troubleshooting
```bash
# Check status
bash scripts/status.sh

# Validate configuration
bash scripts/validate-config.sh

# View logs
journalctl -u panel -f

# Run health checks
bash scripts/post-install-test.sh
```

---

## Environment Variables

Scripts respect these environment variables:

```bash
# Installation
INSTALL_DIR=~/panel          # Installation directory
DB_CHOICE=1                  # 1=SQLite, 2=PostgreSQL
INSTALL_REDIS=y              # Install Redis locally
ENV_CHOICE=1                 # 1=Development, 2=Production
DOMAIN=example.com           # Domain for production
SSL_EMAIL=admin@example.com  # Email for SSL certificates

# Backup
PANEL_INSTALL_DIR=/opt/panel              # Panel directory
PANEL_BACKUP_DIR=/var/backups/panel       # Backup location
PANEL_BACKUP_RETENTION=30                 # Days to keep
PANEL_BACKUP_COMPRESS=true                # Compress backups

# Monitoring
PROMETHEUS_PORT=9090         # Prometheus port
GRAFANA_PORT=3000            # Grafana port
```

---

## Script Dependencies

Most scripts require:
- Bash 4.0+
- Python 3.8+
- Git 2.0+
- sudo access (for system packages)

Optional dependencies:
- PostgreSQL (for PostgreSQL database)
- Redis (for caching)
- nginx (for production)
- certbot (for SSL)
- docker (for containerized deployments)

---

## Common Workflows

### Fresh Installation
```bash
# 1. Install Panel
bash scripts/install-interactive.sh

# 2. Check status
cd ~/panel
./status.sh

# 3. Start application
./start.sh
```

### Update Existing Installation
```bash
# 1. Backup current installation
bash scripts/manage-backups.sh backup

# 2. Update with installer
bash scripts/install-interactive.sh
# Choose option [1] Update existing

# 3. Verify status
./status.sh
```

### Production Deployment
```bash
# 1. Deploy to cloud provider
bash scripts/deploy-aws.sh  # or azure/gcp

# 2. Configure monitoring
# Setup Prometheus, Grafana, etc.

# 3. Setup CI/CD
bash scripts/ci-cd-pipeline.sh
```

### Troubleshooting
```bash
# 1. Check status
./status.sh

# 2. View logs
tail -f logs/app.log

# 3. Test configuration
bash scripts/manage-config.sh validate

# 4. Run tests
./test.sh
```

---

## Contributing

When adding new scripts:

1. Follow the existing naming convention
2. Add proper error handling
3. Include logging functions
4. Add help/usage information
5. Update this README
6. Make scripts executable: `chmod +x script.sh`

---

## Support

For issues or questions:
- 📖 [Documentation](https://github.com/phillgates2/panel/blob/main/README.md)
- 🐛 [Report Issues](https://github.com/phillgates2/panel/issues)
- 💬 [Discussions](https://github.com/phillgates2/panel/discussions)

---

**Last Updated:** December 2, 2025
