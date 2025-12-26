"""Installer package for Panel

Light-weight scaffolding for a cross-platform installer (CLI + GUI PoC)
"""

__version__ = "0.1.0"

from . import core, cli, gui, deps, os_utils, service_manager

__all__ = ["core", "cli", "gui", "deps", "os_utils", "service_manager"]
