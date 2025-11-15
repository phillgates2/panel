# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

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
