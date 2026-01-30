"""Python environment installer helpers (PoC).

Provides:
 - is_installed()  # check for venv support
 - install(dry_run=False, target='/opt/panel/venv')  # create venv
"""
import shutil
import subprocess
import logging
import os

log = logging.getLogger(__name__)


def is_installed():
    # venv is part of stdlib; check python3 exists
    return shutil.which("python3") is not None


def install(dry_run=False, target=None, elevate=True):
    """Create a venv in the given target directory.

    When elevate=False, the target directory must be user-writable. If it's not,
    we return a clear error advising a user path (e.g. ~/panel/venv) or to re-run
    with elevation.
    """
    target = target or '/opt/panel/venv'
    cmd = f"python3 -m venv {target}"
    if dry_run:
        return {"installed": False, "cmd": cmd, "path": target}

    # Validate writability when not elevated
    try:
        parent = os.path.dirname(target) or "."
        if not elevate:
            # Check if parent exists and is writable; try to create if missing
            if not os.path.exists(parent):
                try:
                    os.makedirs(parent, exist_ok=True)
                except Exception as e:
                    return {
                        "installed": False,
                        "error": f"cannot create parent directory '{parent}': {e}",
                        "cmd": cmd,
                        "path": target,
                        "hint": "Use a user-writable path (e.g., ~/panel/venv) or enable elevation",
                    }
            if not os.access(parent, os.W_OK):
                return {
                    "installed": False,
                    "error": f"permission denied: parent directory '{parent}' not writable",
                    "cmd": cmd,
                    "path": target,
                    "hint": "Choose a user path (e.g., ~/panel/venv) or re-run with elevation",
                }

        # Create venv
        os.makedirs(parent, exist_ok=True)
        subprocess.check_call(["python3", "-m", "venv", target])
        return {"installed": True, "path": target}
    except Exception as e:
        return {"installed": False, "error": str(e), "cmd": cmd, "path": target}


def uninstall(preserve_data=True, dry_run=False, target='/opt/panel/venv'):
    """Remove the venv directory unless preserve_data=True."""
    if dry_run:
        return {"uninstalled": False, "cmd": f"(dry-run) rm -rf {target}", "path": target}

    if preserve_data:
        return {"uninstalled": False, "msg": "preserve_data=True; skipping venv removal", "path": target}

    try:
        import shutil as _sh
        _sh.rmtree(target)
        return {"uninstalled": True, "path": target}
    except Exception as e:
        return {"uninstalled": False, "error": str(e), "path": target}
