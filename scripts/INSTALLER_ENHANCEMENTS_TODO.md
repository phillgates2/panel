# Installer Enhancement Implementation Plan

## Status: Iteration 5 - IN PROGRESS

This document tracks the implementation of 10 advanced features for the install-interactive.sh script.

## Completed Features ✓

### 1. Documentation & Offline Cache Script ✓
- **Status**: COMPLETE (commit 011d179)
- **Files**: 
  - `scripts/create-offline-cache.sh` - Created
  - `scripts/README.md` - Updated with all new options
- **Features**:
  - Offline package cache creator
  - Comprehensive documentation for all new flags
  - Usage examples and workflows

## Features To Implement

### 2. Configuration Wizard Mode (`--wizard`)
- **Status**: NOT STARTED
- **Implementation**:
  - Add `WIZARD_MODE` flag parsing (DONE in concept)
  - Enhance interactive prompts section (line ~460)
  - Add advanced configuration options:
    - Deployment type (dev/prod/HA/container)
    - Database configuration (SQLite/PostgreSQL/External)
    - Redis setup (local/external/cluster)
    - Performance tuning (worker processes, connections)
    - Security options (firewall, fail2ban, hardening)
    - Monitoring setup (Prometheus/Grafana)
    - Backup configuration (retention, directory)
    - SSL/TLS configuration
- **Code Location**: Lines 461-650 in install-interactive.sh
- **Complexity**: HIGH (requires restructuring interactive prompts)

### 3. Rollback Capability
- **Status**: NOT STARTED
- **Implementation**:
  - Add `ROLLBACK_STEPS` array initialization
  - Create `add_rollback_step(command)` function
  - Create `rollback_installation()` function
  - Add `trap 'rollback_installation' ERR`
  - Register rollback actions for:
    - Directory creation (`rm -rf`)
    - Service installation (`systemctl disable && stop`)
    - Database creation (`dropdb`, `DROP USER`)
    - Virtual environment
- **Code Location**: Beginning of script (after variable initialization)
- **Complexity**: MEDIUM

### 4. Progress Tracking & Timer
- **Status**: PARTIALLY COMPLETE (functions created, need integration)
- **Implementation**:
  - Add `INSTALL_START_TIME` tracking
  - Create `show_progress(current, total, message)` function (DONE)
  - Create `show_elapsed_time()` function (DONE)
  - Integrate progress calls at 10 key points:
    1. After preflight checks
    2. After repository clone
    3. After venv creation
    4. After venv activation
    5. After pip upgrade
    6. After dependency installation
    7. After database setup
    8. After Redis setup
    9. After configuration
    10. Installation complete
- **Code Location**: Throughout installer
- **Complexity**: LOW (functions exist, just need to add calls)

### 5. Multi-Version Python Support
- **Status**: CONCEPTUALLY COMPLETE (need to reapply)
- **Implementation**:
  - Detect Python 3.8, 3.9, 3.10, 3.11, 3.12
  - Auto-search for alternative installations
  - Interactive selection if current version < 3.8
  - Set `PYTHON_CMD` variable
  - Version-specific optimizations (PYTHONOPTIMIZE=2 for 3.11+)
  - Python 3.12 compatibility (install build-essential)
- **Code Location**: Lines 340-390 (Python detection section)
- **Complexity**: MEDIUM

### 6. Cloud Provider Presets
- **Status**: CONCEPTUALLY COMPLETE (need to reapply)
- **Implementation**:
  - Parse `--cloud=PROVIDER` argument
  - Support: aws, gcp, azure, digitalocean
  - Auto-set for each preset:
    - `ENV_CHOICE=2` (production)
    - `DB_CHOICE=2` (PostgreSQL)
    - `INSTALL_REDIS="y"`
    - Cloud-specific env vars (`AWS_CLOUD`, `GCP_CLOUD`, etc.)
- **Code Location**: Lines 185-230 (after argument parsing)
- **Complexity**: LOW

### 7. Migration Mode
- **Status**: FRAMEWORK READY (need specific implementations)
- **Implementation**:
  - Parse `--migrate` flag
  - Interactive source panel selection:
    1. Pterodactyl Panel
    2. ApisCP
    3. cPanel/WHM
    4. Plesk
    5. Custom
  - Extract database credentials from each source
  - Import configuration
- **Code Location**: Lines 230-275 (after cloud presets)
- **Complexity**: HIGH (panel-specific logic needed)

### 8. Offline Installation Support
- **Status**: CONCEPTUALLY COMPLETE (need to reapply)
- **Implementation**:
  - Parse `--offline` flag
  - Check for offline package cache (`offline-packages/`)
  - Use `pip install --no-index --find-links` for all installations
  - Skip online-only operations (git clone from cache, preflight network checks)
- **Code Location**: 
  - Lines 168-182 (preflight checks - skip network)
  - Lines 748-770 (pip installation logic)
- **Complexity**: MEDIUM

### 9. Integration Testing
- **Status**: CONCEPTUALLY COMPLETE (need to reapply)
- **Implementation**:
  - Parse `--test` flag
  - After installation complete:
    - Run `scripts/post-install-test.sh` if available
    - Run `pytest tests/` if pytest available
    - Test application startup (timeout 10s)
- **Code Location**: Lines 1299-1332 (after installation summary)
- **Complexity**: LOW

### 10. Dependency Conflict Resolution
- **Status**: CONCEPTUALLY COMPLETE (need to reapply)
- **Implementation**:
  - Install `pip-tools` (pip-compile)
  - Run `pip-compile` on requirements/production.txt
  - Detect conflicts with grep
  - Auto-upgrade and regenerate if conflicts found
  - Only run if not in offline mode
- **Code Location**: Lines 790-800 (before pip install)
- **Complexity**: LOW

## Implementation Strategy

### Phase 1: Core Functions (Low Risk)
1. Rollback functions and trap
2. Progress bar integration
3. Timer tracking
4. Dependency conflict detection

### Phase 2: Mode Enhancements (Medium Risk)
5. Multi-version Python support
6. Cloud provider presets
7. Offline installation mode
8. Integration testing

### Phase 3: Advanced Features (High Risk)
9. Configuration wizard mode
10. Migration mode (panel-specific)

## Testing Checklist

- [ ] Syntax check: `bash -n scripts/install-interactive.sh`
- [ ] Dry run: `./scripts/install-interactive.sh --dry-run`
- [ ] Non-interactive: `./scripts/install-interactive.sh --non-interactive`
- [ ] Wizard mode: `./scripts/install-interactive.sh --wizard`
- [ ] Cloud presets: Test each cloud option
- [ ] Offline mode: Create cache and test offline install
- [ ] Integration tests: `./scripts/install-interactive.sh --test`
- [ ] Rollback: Test error conditions trigger rollback
- [ ] Python versions: Test with different Python versions
- [ ] Migration: Test at least one panel migration

## Notes

- The original install-interactive.sh was restored to clean state (git checkout)
- All conceptual work is documented here for clean re-implementation
- Create-offline-cache.sh and documentation are complete and committed
- Previous iteration (16 enterprise features) was completed in commit 87bb571

## Next Steps

1. Implement Phase 1 features (rollback, progress, timer, conflicts)
2. Test Phase 1 thoroughly
3. Implement Phase 2 features (Python, cloud, offline, testing)
4. Test Phase 2 thoroughly
5. Implement Phase 3 features (wizard, migration) 
6. Final comprehensive testing
7. Commit all changes with detailed message
8. Update CHANGELOG.md

## File Status

- `scripts/install-interactive.sh` - RESTORED TO CLEAN STATE, needs re-implementation
- `scripts/create-offline-cache.sh` - ✓ COMPLETE AND COMMITTED
- `scripts/README.md` - ✓ COMPLETE AND COMMITTED
- `scripts/INSTALLER_ENHANCEMENTS_TODO.md` - THIS FILE
