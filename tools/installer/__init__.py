"""Installer package for Panel

GUI-only entry with supporting modules.
"""

__version__ = "0.1.0"

# Import supporting modules
from . import core, deps, os_utils, service_manager

# Expose gui
from . import gui  # type: ignore
__all__ = ["core", "gui", "deps", "os_utils", "service_manager"]
