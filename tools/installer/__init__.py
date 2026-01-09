"""Installer package for Panel

Light-weight scaffolding for a cross-platform installer (CLI + GUI PoC)
"""

__version__ = "0.1.0"

# Import non-GUI modules eagerly; GUI is optional and should not block tests/environments without PySide6.
from . import core, cli, deps, os_utils, service_manager

# Expose gui only if available
try:
    from . import gui  # type: ignore
    __all__ = ["core", "cli", "gui", "deps", "os_utils", "service_manager"]
except Exception:
    __all__ = ["core", "cli", "deps", "os_utils", "service_manager"]
