# Panel Unified Installer (PoC)

This document describes the early PoC for a unified cross-platform installer.

Goals for first release:

- Support Linux, macOS, and Windows
- GUI in first release (PySide6 PoC)
- Require admin/elevated rights for system changes
- Allow domain customization during install
- Install all components: PostgreSQL, Redis, Nginx, Python env, services

PoC status:

- CLI and GUI scaffolds added in `tools/installer/`
- `scripts/panel-installer` launcher added
- Core functions and stubs exist for dependency checks and service management
- **PostgreSQL installer implemented (Linux PoC)**
- **Redis installer implemented (Linux PoC)**
- **Nginx and Python env installers implemented (Linux PoC)**
- **Unit tests added and CI workflow implemented to validate installers across OSes**
- **Uninstall & state-based rollback support implemented (PoC)**

Next steps:

- Implement the admin elevation flow per OS and validate behavior on macOS/Windows
- Implement more robust dependency installer / package manager wrappers and package mappings
- Implement packaging workflows (AppImage/DMG/EXE) and release pipelines
- Wire advanced GUI flows (progress indicators, logs, rollback UI)
