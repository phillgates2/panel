# Panel Scripts Directory

This directory contains utility scripts for managing the Panel application.

## Installation & Setup

### 📦 install-interactive.sh
**Interactive installer for Panel application**

```bash
# Interactive installation
bash scripts/install-interactive.sh

# Non-interactive (CI/CD)
bash scripts/install-interactive.sh --non-interactive

# Dry run (preview)
bash scripts/install-interactive.sh --dry-run

# Get help
bash scripts/install-interactive.sh --help
```

**Features:**
- Interactive prompts for configuration
- System requirements validation
- Database setup (SQLite or PostgreSQL)
- Redis installation and configuration
- Virtual environment creation
- Admin user creation
- Production service setup (systemd, nginx, SSL)
- Comprehensive health checks

**Options:**
- `--dry-run` - Show what would be installed
- `--non-interactive` - Use defaults for automation
- `--help` - Display usage information

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

## Environment Variables

Scripts respect these environment variables:

```bash
INSTALL_DIR=~/panel          # Installation directory
DB_CHOICE=1                  # 1=SQLite, 2=PostgreSQL
INSTALL_REDIS=y              # Install Redis locally
ENV_CHOICE=1                 # 1=Development, 2=Production
DOMAIN=example.com           # Domain for production
SSL_EMAIL=admin@example.com  # Email for SSL certificates
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
