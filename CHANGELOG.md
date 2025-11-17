# Changelog

All notable changes to this project will be documented in this file.

## [3.0.5] - 2025-11-17

### ✨ **New Features**

#### Installer Enhancements
- **Enhanced `--help` Output** - Display all available installer functions
  - Lists 25+ functions organized by category (Core, System, Validation, Installation, Utility)
  - Helpful for debugging and understanding installer capabilities
  - Shows function names and brief descriptions
  - Integrated into help menu for easier discovery

- **`--verify-only` Flag** - Verify existing installation without reinstalling
  - Checks `.env` file existence and configuration
  - Validates virtual environment and Flask installation
  - Tests database connection (PostgreSQL or SQLite)
  - Useful for troubleshooting existing installations

- **`--update` Flag** - Safe upgrade mechanism for existing installations
  - Creates timestamped backup before updating
  - Pulls latest code from git repository
  - Upgrades Python dependencies via pip
  - Runs database migrations if available
  - Preserves existing `.env` configuration

#### Documentation Updates
- **README** - Added installer flags reference section
  - Documents `--functions`, `--verify-only`, `--update` flags
  - Updated installation examples with new options

## [3.0.4] - 2025-11-17

### 🐛 **Bug Fixes**

#### Auto-Start Process Detection
- **Fixed Flask Debug Mode Process Detection** - Auto-start now correctly detects running Panel
  - Flask's debug mode spawns child processes via reloader
  - Original PID check was unreliable (parent process exits immediately)
  - Now uses `pgrep -f "python.*app.py"` to find actual running processes
  - Displays all running PIDs (Panel and Worker may have multiple processes)
  - Updated stop instructions to recommend `pkill -f` over individual PID termination

#### Directory Creation
- **Enhanced Directory Setup** - Creates all required directories before starting services
  - Now creates: `logs/`, `instance/logs/`, `instance/audit_logs/`, `instance/backups/`
  - Prevents file write errors during startup
  - Increased startup wait time from 2s to 3s for proper initialization
  - Shows last 20 lines of log on failure for debugging

## [3.0.3] - 2025-11-17

### ✨ **New Features**

#### Redis Installation & Service Management
- **Automatic Redis Installation** - Installer now includes Redis in system dependencies
  - Supports all package managers: apt, dnf/yum, apk, pacman, brew
  - Checks if Redis is running before starting Panel services
  - Automatically starts Redis if not running (systemd, service, or daemonize)
  - Provides clear warnings and instructions if Redis fails to start

#### Domain/Hostname Configuration
- **Domain Prompt** - Interactive installer now asks for domain/hostname
  - Supports domains (panel.example.com), IPs (192.168.1.100), or localhost
  - Stores domain in `.env` file for configuration reference
  - Updates all completion messages to show configured domain

#### Comprehensive Documentation
- **Troubleshooting Section** - Added detailed troubleshooting guide to README
  - Redis connection errors (port 6379 refused)
  - Panel startup issues and port conflicts
  - Database connection problems (PostgreSQL & SQLite)
  - Worker not processing jobs
  - Step-by-step solutions with commands

### 🐛 **Bug Fixes**

#### Background Worker Redis Dependency
- **Fixed Redis Connection Error** - Worker now starts successfully
  - Error: `ConnectionError: Error 111 connecting to 127.0.0.1:6379. Connection refused.`
  - Cause: Redis was not installed or running
  - Solution: Installer now ensures Redis is installed and running before starting worker

## [3.0.2] - 2025-11-17

### ✨ **New Features**

#### Installer Auto-Start Option
- **Interactive Auto-Start** - Installer now prompts to automatically start the Panel after installation
  - Starts both web server and background worker in one step
  - Provides immediate access to the Panel without manual commands
  - Shows PIDs for easy process management
  - Displays log file locations for troubleshooting
  - Falls back to manual instructions if user declines

### 🐛 **Bug Fixes**

#### Installer UX Improvements
- **Fixed Post-Installation Confusion** - Panel now starts automatically when user confirms
  - Previously only showed manual start instructions
  - Users reported being "unable to connect" because services weren't running
  - Now provides clear choice: start now (automatic) or manual start later

## [3.0.1] - 2025-11-17

### 🐛 **Bug Fixes**

#### Installer Improvements
- **Fixed Terminal Text Selection** - Removed `-n` flag from echo commands to allow normal text selection in terminal
- **Fixed Prompt Capture Issue** - Redirected all prompts to stderr (`>&2`) to prevent prompt text from being captured in variables
  - Fixes error: "Refusing to create a venv... because it contains the PATH separator `:'"
- **Fixed Database Initialization** - Wrapped `db.create_all()` in `app.app_context()` to prevent RuntimeError
  - Fixes error: "RuntimeError: Working outside of application context"

#### Logging Improvements  
- **Fixed Logging Outside App Context** - Added try/except in `record_factory` to gracefully handle missing Flask application context
  - Returns `None` for `correlation_id` when no request context is available
  - Prevents crashes during database initialization and CLI commands

#### Uninstaller Clarification
- **Separated Uninstaller** - `uninstall.sh` is now completely standalone
  - Fixed issue where `--uninstall` flag in install.sh wasn't working with curl piping
  - Use `curl -fsSL .../uninstall.sh | bash` for uninstallation
  - Updated README and help documentation to reflect proper usage

### 📚 **Documentation**
- Updated README.md with correct uninstallation commands
- Updated install.sh --help to point to separate uninstall.sh
- Clarified that uninstaller removes files, folders, AND system dependencies by default

## [3.0.0] - 2025-01-16

### 🎉 **Major Refactoring - PostgreSQL Migration & Codebase Cleanup**

This release represents a complete modernization of Panel with a focus on simplicity, PostgreSQL, and removing legacy code.

### 🗄️ **Database Migration**
- **PostgreSQL as Primary Database** - Migrated from MariaDB/MySQL to PostgreSQL
  - Production database now uses `psycopg2-binary==2.9.9` driver
  - Maintained SQLite support for development (`PANEL_USE_SQLITE=1`)
  - Removed all MariaDB/MySQL dependencies and configurations
  - Updated all database connection strings and queries for PostgreSQL compatibility

### 🧹 **Massive Code Cleanup** - Removed **7,916 lines** across **8 legacy files**
- **Removed Legacy Installer** - Deleted bloated `getpanel.sh` (2,947 lines)
- **Removed Backup Files** - Deleted `getpanel.sh.mariadb.backup`
- **Removed Migration Docs** - Deleted temporary `POSTGRES_MIGRATION.md`
- **Removed Migration Scripts** - Deleted `scripts/migrate_to_postgres.sh` and `scripts/postgres_functions.sh`
- **Removed Deprecated Wrappers** - Deleted `scripts/install.sh`, `scripts/update.sh`, `scripts/uninstall.sh`
- **86% Size Reduction** - New installer is only **416 lines** vs old 2,947-line installer

### ✨ **New Streamlined Installer**
- **Created `install.sh`** (416 lines) - Complete rewrite from scratch
  - Environment variable driven configuration
  - Interactive and non-interactive modes
  - PostgreSQL and SQLite support
  - Cross-platform package manager support (apt, dnf, apk, pacman, brew)
  - Clean color scheme: RED, GREEN, YELLOW, MAGENTA (removed BLUE, CYAN)
  - Comprehensive error handling and validation
  - Non-interactive installation via environment variables:
    - `PANEL_NON_INTERACTIVE=true`
    - `PANEL_DB_TYPE=postgresql|sqlite`
    - `PANEL_DB_HOST`, `PANEL_DB_PORT`, `PANEL_DB_NAME`, etc.

### 🔄 **Database Admin UI Refactoring**
- **Renamed `phpmyadmin_integration.py` → `database_admin.py`**
  - `PhpMyAdminIntegration` class → `DatabaseAdmin` class
  - `PHPMYADMIN_BASE_TEMPLATE` → `DATABASE_ADMIN_BASE_TEMPLATE`
  - `PHPMYADMIN_HOME_TEMPLATE` → `DATABASE_ADMIN_HOME_TEMPLATE`
  - `PHPMYADMIN_TABLE_TEMPLATE` → `DATABASE_ADMIN_TABLE_TEMPLATE`
  - `PHPMYADMIN_QUERY_TEMPLATE` → `DATABASE_ADMIN_QUERY_TEMPLATE`
  - Updated all imports in `app.py` and `tests/test_database_integration.py`
  - Removed misleading phpMyAdmin references (Python-based UI, not PHP)
  - Supports both PostgreSQL and SQLite via built-in Python drivers

### 🎨 **Installer UI Improvements**
- **Simplified Color Scheme** - Reduced from 6 colors to 4 colors
  - Removed: `BLUE`, `CYAN`
  - Kept: `RED`, `GREEN`, `YELLOW`, `MAGENTA`
  - Updated all banners, prompts, labels, and error messages
  - Cleaner, more professional terminal output

### 📚 **Documentation Overhaul**
- **Completely Rewrote README.md**
  - Removed all MariaDB/MySQL references
  - Removed phpMyAdmin references (now "Database Admin UI")
  - Highlighted PostgreSQL-first architecture
  - Documented new 416-line installer
  - Removed deprecated installer options
  - Added clear PostgreSQL vs SQLite usage examples
  - Updated architecture diagram with `database_admin.py`
  - Simplified quick start with single curl command

### 🔧 **Breaking Changes**
- **Removed MariaDB/MySQL Support** - PostgreSQL or SQLite only
- **Removed Legacy Installers** - Only `install.sh` remains
- **Removed Deprecated Scripts** - Old wrapper scripts no longer available
- **Renamed Database Admin** - Update any custom integrations using `PhpMyAdminIntegration`

### 📦 **Dependencies**
- **Added**: `psycopg2-binary==2.9.9` - PostgreSQL driver
- **Removed**: All MariaDB/MySQL Python drivers
- **Updated**: Flask, SQLAlchemy maintained at current versions

### ✅ **Validation & Testing**
- All Python files validated with `py_compile`
- Bash installer validated with `bash -n`
- Tests updated for PostgreSQL compatibility
- Database admin UI tests updated for new class names

### 🚀 **Migration Guide**
For users upgrading from v2.x with MariaDB/MySQL:
1. **Backup your database** - Use `make db-backup` or `mysqldump`
2. **Export data to PostgreSQL format**
3. **Run new installer** - `curl -fsSL .../install.sh | bash`
4. **Import data into PostgreSQL** - Use `psql` or `pg_restore`
5. **Update environment variables** - Switch to PostgreSQL connection strings

## [2.1.0] - 2025-01-16

### 🚀 **Installation Flow Reorganization**
- **Production Mode Early Database Setup** - MariaDB and phpMyAdmin now installed immediately after selecting production mode
- **Validation Checkers** - Added comprehensive validation functions for each configuration section
  - `check_mariadb_ready()` - Verifies MariaDB service is running and accessible (10 retry attempts)
  - `check_phpmyadmin_ready()` - Confirms phpMyAdmin installation and HTTP accessibility
  - `check_database_connection()` - Tests database connectivity and creates database with UTF8MB4
  - `check_section_complete()` - Visual completion markers between configuration sections
- **Early Failure Detection** - Database issues caught early before app configuration begins
- **Better Error Handling** - Option to abort or continue when database setup fails
- **Improved UX** - Clear visual separators and progress indicators throughout installation
- **Section Markers** - Each configuration section now has a completion marker for better visibility

### ✨ **Enhanced Production Deployment**
- **Immediate Database Verification** - Database infrastructure verified before continuing with configuration
- **phpMyAdmin Instant Access** - Database management UI available immediately at http://localhost:8081
- **Better Flow** - Database setup → Verify → Admin config → App settings → Services
- **Configuration Summary** - Enhanced summary with bold section headers and clear structure

## [2.0.0] - 2025-01-16

### 🎨 **Installer UX Improvements**
- **Colorful Terminal Output** - Added magenta, yellow, white colors for better readability
- **Redesigned --help** - Professional layout with categorized options and examples
- **Fixed Color Display** - Switched from heredoc to printf for proper ANSI rendering
- **Visual Hierarchy** - Grouped options by function (Installation, Components, Automation)

### 🗑️ **Enhanced Uninstall**
- **Complete Cleanup** - Now removes logs, audit logs, and database backups
- **Clear User Messaging** - Shows exactly what will be removed
- **Safe Operation** - Confirmation required before deletion

### 🗄️ **Database & phpMyAdmin**
- **Replaced Apache with Nginx** - phpMyAdmin now served via Nginx on port 8081
- **No Port Conflicts** - Panel (80/443) and phpMyAdmin (8081) coexist peacefully
- **Enhanced Database Setup** - Uses Flask-Migrate when available, UTF8MB4 charset
- **Better Logging** - Detailed step-by-step database creation logs
- **Verification** - Tests database creation with USE/SELECT validation

### 🔧 **Bug Fixes**
- **PHP-FPM Service Detection** - Auto-detects correct service name (php8.4-fpm, etc.)
- **Syntax Errors** - Fixed orphaned if/fi blocks in installer
- **Wildcard Commands** - Replaced invalid systemctl wildcards with proper detection

### 📚 **Documentation**
- **Streamlined README** - Easier to scan with clear sections and quick start
- **Better Examples** - One-line commands for common scenarios
- **Architecture Diagram** - Visual project structure
- **Updated Links** - All documentation properly cross-referenced

## [Unreleased]

### 🧰 **Installer, Logging & Tooling** - 2025-11-16

- **Unified Panel Entrypoints**
  - Deprecated legacy helper scripts (`scripts/install.sh`, `scripts/update.sh`, `scripts/uninstall.sh`, `start-dev.sh`) in favor of the consolidated `panel.sh` CLI
  - Updated `README.md` and `README_DEV.md` to steer users toward `panel.sh` as the primary interface
- **Self-Healing & Diagnostics**
  - Added `panel-doctor.sh` to run health checks on services, sockets, ports, migrations, and directories with optional auto-fix mode
  - Improved MariaDB readiness detection in `getpanel.sh` with broader systemd unit scanning (including templated units) and richer diagnostics
- **Secrets & Environment Management**
  - Introduced `scripts/env_generator.sh` for validated `.env` generation with support for `LOG_FORMAT` configuration
- **Structured Logging Enhancements**
  - Extended `logging_config.py` with optional JSON log output and per-request correlation IDs controlled via environment variables

### 🔧 **System Health & Configuration Management** - 2025-11-15

- **Health Check Endpoints** 💓
  - Added `/health` endpoint for basic system health monitoring
  - Added `/health/detailed` endpoint for comprehensive admin health checks
  - Integrated database, Redis, and uptime monitoring
  - JSON response format for easy integration with monitoring tools
  - Authentication protection for sensitive health information

- **Configuration Validation System** ✅
  - Implemented comprehensive `ConfigValidator` with intelligent dev/production detection  
  - Enhanced error handling with proper development vs production mode differentiation
  - Added detailed validation for SECRET_KEY, database, Redis, and ET:Legacy configurations
  - Improved dependency checking with required vs optional package classifications
  - **Fixed dependency detection for PIL/Pillow imports**
  - **Enhanced dev/production mode detection for contextual warnings**
  - **Added intelligent directory validation with optional paths**
  - **Refined service connection warnings to be development-appropriate**
  - **Removed duplicate validation checks and improved error messages**
  - Smart fallback configuration reading from config.py when environment variables missing

- **Admin Configuration Interface** 🎛️
  - Created `/admin/config/validate` endpoint with full validation reporting
  - Added beautiful admin interface (`admin_config_validate.html`) with real-time validation
  - Integrated configuration validation into admin tools menu
  - Color-coded error, warning, and info sections for easy issue identification
  - Added comprehensive configuration tips and best practices documentation
  - Real-time re-validation functionality with loading states

- **Enhanced Development Experience** 🛠️
  - Automatic detection of development mode (SQLite, FLASK_ENV, missing configs)
  - Graceful handling of missing optional dependencies in development
  - Improved error messages with context-aware suggestions
  - Better separation of critical production issues vs development warnings

### ✅ **Testing & Validation** - 2025-11-15

- **Captcha System Validation** 🔍
  - Extensively tested captcha generation with multiple size configurations (50x25 to 700x280 pixels)
  - Validated optimal readability with 80px font in 350x140 pixel canvas
  - Tested ultra-compact 50x25 pixel implementation for mobile compatibility
  - Confirmed enhanced contrast with light gray background and dark blue text
  - Verified exclusion of confusing characters (0, O, I, 1, L) for better usability

- **Code Quality & Cleanup** 🧹
  - Added comprehensive `.gitignore` for Python, Flask, IDE, and temporary files
  - Cleaned up test captcha files and development artifacts
  - Resolved all configuration validation warnings with appropriate dev/production context
  - Improved dependency detection accuracy for proper virtual environment validation
  - Enhanced error messages and validation reporting for better developer experience

- **Installer Testing & Verification** 🧪
  - Validated getpanel.sh installer functionality in clean environments
  - Tested interactive and non-interactive installation modes
  - Confirmed proper dependency management and Python version checking
  - Verified repository cloning and virtual environment setup
  - Validated uninstaller safety checks and complete cleanup

- **Dependency Compatibility Verification** ✅
  - Confirmed Flask 3.0.0 compatibility with existing codebase
  - Tested Pillow 10.1.0 image processing improvements
  - Validated Redis 5.0.1 connection handling
  - Verified all updated dependencies work correctly in production environment
  - Tested pip 25.3 upgrade process and build tool compatibility

### 📦 **Dependency Updates & Optimization** - 2025-11-15

- **Latest Package Versions** 🔄
  - Updated Flask to 3.0.0 (latest stable release)
  - Updated Flask-SQLAlchemy to 3.1.1 with improved performance
  - Updated Pillow to 10.1.0 for enhanced image processing
  - Updated Redis client to 5.0.1 for better async support
  - Updated cryptography to 41.0.8 for latest security patches
  - Updated all development and testing dependencies

- **Enhanced Dependency Management** 🛠️
  - Automatic pip and build tools upgrade during installation
  - Build essentials installation (python3-dev, build-essential)
  - Optional ML dependencies with version pinning for stability
  - Dependency verification after installation
  - Better error handling for missing or incompatible packages
  - Python version compatibility warnings and recommendations

- **Optimized Requirements Structure** 📋
  - Separated core dependencies from optional enterprise features
  - Removed duplicate psutil entries and version conflicts
  - Added proper version constraints for security and compatibility
  - Documented optional dependencies with installation flags
  - Cleaner requirements.txt with categorized sections

### 🚀 **Interactive Installation System** - 2025-11-15

- **One-Command Installer & Uninstaller** 📦
  - Created `getpanel.sh` - curl-installable script for instant deployment and removal
  - Interactive configuration wizard with step-by-step setup guidance
  - Complete uninstaller with safety checks and graceful service cleanup
  - Support for development, production, and custom installation modes
  - Non-interactive mode for automation and CI/CD pipelines
  - Automatic system requirements validation (Python 3.8+, Git, Curl)

- **Advanced Configuration Options** ⚙️
  - **Database Setup**: Interactive choice between SQLite and MariaDB with connection configuration
  - **Admin User Creation**: Secure password input with email configuration
  - **Application Settings**: Host, port, debug mode, and CAPTCHA preferences
  - **Production Services**: Nginx reverse proxy, SSL certificates, systemd services
  - **Optional Features**: Redis task queue, Discord webhook notifications

- **Smart Installation & Removal Features** ✨
  - Automatic system dependency detection and installation (apt/yum/apk)
  - Latest dependency versions with automated upgrade handling
  - Build essentials and development tools installation
  - Python version compatibility checking (3.8+ required, 3.11+ recommended)
  - Pip and build tools upgrade to latest versions
  - Optional ML/Analytics dependencies (numpy, scikit-learn, boto3)
  - Dependency verification with error handling
  - Secure environment file generation with random secret keys
  - MariaDB database and user creation with proper permissions
  - Nginx configuration with domain setup and SSL certificate provisioning
  - Systemd service configuration for production deployments
  - Complete uninstaller with service cleanup and safety confirmations
  - Graceful service shutdown and configuration removal
  - Comprehensive installation summary with next steps guidance

- **Enhanced Documentation** 📚
  - Complete README rewrite with modern structure and clear installation paths
  - Interactive installer documentation with configuration examples
  - Production deployment guide with automated service setup
  - Environment variable reference and customization options

### 🔐 **Captcha System Optimization** - 2025-11-15

- **Ultra-Compact Captcha Design** 📏
  - Reduced captcha image size to ultra-compact 50x25 pixels for better UI integration
  - Optimized font size to 16px for maximum clarity in small format
  - Implemented quality enhancement filters (SMOOTH + SHARPEN) for improved readability
  - Added comprehensive fallback calculations for character width optimization
  - Generated multiple test variations to validate optimization approaches

- **Enhanced Visual Quality** ✨
  - Applied dual image filters for crisp text rendering in compact format
  - Improved contrast and readability despite reduced dimensions
  - Maintained security standards while prioritizing user experience
  - Tested progressive zoom levels (100%, 300%, 900%) before settling on optimal size

- **Development Stability** 🛠️
  - Temporarily disabled enterprise monitoring systems for stable development
  - Resolved SQLAlchemy context management issues
  - Improved Flask application startup reliability
  - Created comprehensive test suite for captcha size variations

### 🚀 **Major Enterprise Features Added**

- **Real-Time Monitoring System** 📊
  - Live server metrics tracking (CPU, memory, disk, network usage)
  - Automated alerting with configurable thresholds
  - Player session monitoring and analytics
  - Interactive monitoring dashboard with Chart.js visualizations
  - Background monitoring threads with 30-second intervals
  - Performance trends and historical data analysis

- **Advanced Log Analytics Platform** 🔍
  - Machine learning-based anomaly detection using statistical analysis
  - Automated pattern recognition and baseline establishment
  - Security event detection and automated alerting
  - Log deduplication and intelligent parsing
  - Real-time log processing with queue management
  - Comprehensive log search and filtering capabilities

- **Multi-Server Management System** 🖥️
  - Cluster orchestration with automated scaling
  - SSH-based remote server management and deployment
  - Centralized configuration management across multiple servers
  - Load balancing and health monitoring
  - Automated deployment pipelines with rollback capabilities
  - Multi-server performance coordination

### 🎨 **User Interface Enhancements**

- **Theme Editor**: Admin can customize site CSS via `/admin/theme`
- **Server Logo Support**: Upload/manage logos with Theme Editor at `/theme_asset/<filename>`
- **Enhanced Navigation**: Hide `Dashboard` and `RCON` links unless user is logged in
- **Professional Dashboards**: Modern enterprise-grade monitoring interfaces
- **Responsive Design**: Mobile-friendly monitoring and management interfaces

### 🔒 **Security & Authentication Improvements**

- **Captcha Hardening** across all authentication flows:
  - Captcha required for Forgot Password (except testing environments)
  - Enhanced Login and Reset Password captcha with audio support via espeak
  - 3-minute captcha expiry with per-IP rate limiting
  - Testing mode bypasses for automated testing compatibility
  - Pillow 10+ compatibility fixes using `textbbox` with fallbacks

### 🛠️ **Technical Infrastructure**

- **Enterprise Database Models**: Comprehensive schema for monitoring, analytics, and cluster management
- **Background Processing**: Robust threading system for real-time data processing
- **Flask App Context**: Proper context management for background services
- **Modular Architecture**: Blueprint-based system for easy feature extension
- **SQLAlchemy Modernization**: Resolved deprecations, replaced `Query.get()` with `db.session.get()`

### 📦 **Installation & Deployment**

- **Enhanced Installation System**:
  - **Unified Management**: `panel.sh` - Single command for all operations
  - **Enterprise Install**: `scripts/install.sh` - Automated enterprise feature setup
  - **Smart Updates**: `scripts/update.sh` - Handles enterprise dependencies and migrations
  - **Clean Removal**: `scripts/uninstall.sh` - Removes all enterprise components
  - Cross-platform support (Linux, macOS, Alpine)
  - Automatic enterprise dependency management
  - Virtual environment setup with ML libraries
  - Enterprise database table initialization
  - Systemd service creation and management

- **Management Commands**:
  - `./panel.sh install` - Full enterprise installation
  - `./panel.sh start` - Development mode with minimal monitoring
  - `./panel.sh start-prod` - Production mode with full enterprise features
  - `./panel.sh monitoring` - Direct access to monitoring dashboard
  - `./panel.sh status` - Service health checks
  - `./panel.sh logs` - Centralized log viewing

- **Enhanced Dependencies**:
  - Enterprise monitoring: `psutil`, `paramiko`, `PyYAML`
  - Analytics capabilities: `numpy`, `scikit-learn` (optional)
  - Graceful fallback for systems without ML support
  - Updated requirements.txt with comprehensive dependency list

### 🐛 **Bug Fixes & Stability**

- Fixed Flask application context issues in background threads
- Resolved SQLAlchemy instance registration warnings
- Improved error handling and graceful degradation
- Enhanced startup reliability and service monitoring

## [scaffold-initial-2025-11-14] - 2025-11-14

- Initial scaffold merge: Flask backend, admin UI templates, deploy/systemd examples.
- Authentication flows (register/login/forgot), local captcha generation, and password rules.
- Server model, role-based access, admin server CRUD, and audit logging with streaming CSV export.
- Confirmation modal with accessibility improvements and keyboard handling.
- Tests: unit tests for auth/models/server UI and a Playwright E2E test scaffold for modal behavior.
- CI workflow and example `requirements.txt` including Playwright.
- Utility scripts and systemd units for RQ workers, memwatch, and autodeploy.

*(This file follows Keep a Changelog format in a minimal form.)*
