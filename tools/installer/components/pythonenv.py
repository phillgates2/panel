"""Python environment installer helpers (PoC).

Provides:
 - is_installed()  # check for venv support
 - install(dry_run=False, target='/opt/panel/venv')  # create venv
"""
import shutil
import subprocess
import logging
import os
import sys

log = logging.getLogger(__name__)


def is_installed():
    # On Debian/Ubuntu, `python3 -m venv` requires `python3-venv` (ensurepip).
    if shutil.which("python3") is None:
        return False
    try:
        p = subprocess.run(["python3", "-c", "import venv, ensurepip"], capture_output=True, text=True)
        return p.returncode == 0
    except Exception:
        return False


def _python_major_minor() -> str | None:
    try:
        out = subprocess.check_output(
            ["python3", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
            text=True,
        ).strip()
        return out or None
    except Exception:
        return None


def _ensure_venv_support(*, elevate: bool) -> dict:
    """Ensure `python3 -m venv` will work (best-effort).

    Primary target: Debian/Ubuntu where ensurepip lives in python3-venv.
    Returns a dict describing what was done.
    """
    try:
        probe = subprocess.run(["python3", "-c", "import venv, ensurepip"], capture_output=True, text=True)
        if probe.returncode == 0:
            return {"ok": True, "action": "probe", "changed": False}
    except Exception as e:
        return {"ok": False, "action": "probe", "error": str(e), "changed": False}

    if not elevate:
        ver = _python_major_minor()
        hint = "apt install python3-venv"
        if ver:
            hint = f"apt install python{ver}-venv (or python3-venv)"
        return {
            "ok": False,
            "action": "install_os_package",
            "changed": False,
            "error": "ensurepip/venv support missing",
            "hint": hint,
        }

    # Try to install the needed OS package(s)
    try:
        from tools.installer.deps import get_package_manager
    except Exception:
        get_package_manager = None

    pm = get_package_manager() if get_package_manager else None
    ver = _python_major_minor()

    if pm == "apt":
        pkgs = ["python3-venv"]
        if ver:
            # Debian 13 often suggests python3.13-venv explicitly.
            pkgs.append(f"python{ver}-venv")

        last_err = ""
        try:
            subprocess.run(["apt-get", "update"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        for pkg in pkgs:
            try:
                p = subprocess.run(["apt-get", "install", "-y", pkg], capture_output=True, text=True)
                if p.returncode == 0:
                    # Re-probe
                    probe2 = subprocess.run(["python3", "-c", "import venv, ensurepip"], capture_output=True, text=True)
                    return {
                        "ok": probe2.returncode == 0,
                        "action": "install_os_package",
                        "changed": True,
                        "package": pkg,
                        "stderr": (probe2.stderr or "")[-2000:],
                    }
                last_err = (p.stderr or p.stdout or "")[-2000:]
            except Exception as e:
                last_err = str(e)

        return {
            "ok": False,
            "action": "install_os_package",
            "changed": False,
            "error": "failed to install python venv support",
            "hint": "apt install python3-venv",
            "details": last_err,
        }

    return {
        "ok": False,
        "action": "install_os_package",
        "changed": False,
        "error": "ensurepip/venv support missing",
        "hint": "Install your OS 'python3-venv' package (Debian/Ubuntu) then retry",
        "package_manager": pm,
    }


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

        # Ensure OS has venv/ensurepip support (Debian/Ubuntu: python3-venv)
        support = _ensure_venv_support(elevate=elevate)
        if not support.get("ok"):
            return {
                "installed": False,
                "error": support.get("error") or "python venv support missing",
                "cmd": cmd,
                "path": target,
                "hint": support.get("hint"),
                "details": support,
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
