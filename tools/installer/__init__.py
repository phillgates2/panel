"""Installer package for Panel

Provides GUI, CLI, and SSH entry points. GUI is imported lazily
to avoid hard dependency on PySide6 during non-GUI usage.
"""

__version__ = "0.1.0"

# Import supporting modules (safe, no GUI deps)
from . import core, deps, os_utils, service_manager

# Do not import GUI/CLI/SSH here to keep imports lazy and avoid
# PySide6 requirements in non-GUI environments.
__all__ = ["core", "deps", "os_utils", "service_manager"]
