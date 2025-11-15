# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

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
  - **Database Setup**: Interactive choice between SQLite and MySQL with connection configuration
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
  - MySQL database and user creation with proper permissions
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
