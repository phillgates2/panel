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


def install(dry_run=False, target=None):
    """Create a venv in the given target directory. Requires admin if target is system path."""
    target = target or '/opt/panel/venv'
    cmd = f"python3 -m venv {target}"
    if dry_run:
        return {"installed": False, "cmd": cmd, "path": target}

    # On Windows target may be under Program Files; on macOS/linux respect provided target
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
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
