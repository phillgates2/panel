"""Installer package for Panel

Provides both GUI and CLI entry points with supporting modules.
"""

__version__ = "0.1.0"

# Import supporting modules
from . import core, deps, os_utils, service_manager

# Expose gui and cli
from . import gui  # type: ignore
from . import cli  # type: ignore
from . import ssh  # type: ignore
__all__ = ["core", "gui", "cli", "ssh", "deps", "os_utils", "service_manager"]
