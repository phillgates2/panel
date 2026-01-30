"""PostgreSQL installer helpers (Linux-focused PoC).

Provides:
 - is_installed()
 - install(dry_run=False)
 - setup_database(db_name='panel', db_user='panel', db_pass=None)

This module uses `tools.installer.deps.get_package_manager()` to pick an install command.
"""
import shutil
import subprocess
import logging
from ..deps import get_package_manager

log = logging.getLogger(__name__)


def is_installed():
    return shutil.which("psql") is not None


def install(dry_run=False, target=None, elevate=True):
    """Install PostgreSQL using the detected package manager.

    Returns a dict with details and, when dry_run=True, includes the command to run.
    """
    if is_installed():
        return {"installed": True, "skipped": True, "msg": "psql already available"}

    if not elevate:
        cmd_preview = "apt-get update && apt-get install -y postgresql postgresql-contrib"
        if get_package_manager() and get_package_manager() != "apt":
            cmd_preview = f"install postgresql via {get_package_manager()}"
        return {
            "installed": False,
            "skipped": False,
            "error": "elevation required to install system package 'postgresql'",
            "hint": "Re-run with elevation or install PostgreSQL manually",
            "cmd": cmd_preview,
        }

    pm = get_package_manager()
    if pm in ("apt", None):
        cmd = ["apt-get", "update", "&&", "apt-get", "install", "-y", "postgresql", "postgresql-contrib"]
        shell = True
    elif pm == "dnf":
        cmd = ["dnf", "install", "-y", "postgresql-server", "postgresql-contrib"]
        shell = False
    elif pm == "yum":
        cmd = ["yum", "install", "-y", "postgresql-server", "postgresql-contrib"]
        shell = False
    elif pm == "pacman":
        cmd = ["pacman", "-Sy", "--noconfirm", "postgresql"]
        shell = False
    elif pm == "apk":
        cmd = ["apk", "add", "postgresql", "postgresql-contrib"]
        shell = False
    elif pm == "brew":
        cmd = ["brew", "install", "postgresql"]
        shell = False
    elif pm in ("choco", "winget"):
        if pm == "choco":
            cmd = ["choco", "install", "postgresql", "-y"]
        else:
            cmd = ["winget", "install", "--id", "PostgreSQL", "-e"]
        shell = False
    else:
        # Unknown or non-Linux package manager, provide an informative message
        return {"installed": False, "skipped": False, "msg": f"No installer configured for package manager: {pm}"}

    cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
    if dry_run:
        return {"installed": False, "cmd": cmd_str}

    try:
        log.info("Running: %s", cmd_str)
        if shell:
            subprocess.check_call(cmd_str, shell=True)
        else:
            subprocess.check_call(cmd)

        # Try starting/enabling service using systemctl if present
        try:
            subprocess.check_call(["systemctl", "enable", "postgresql"])
            subprocess.check_call(["systemctl", "start", "postgresql"])
        except Exception:
            log.debug("systemctl not available or enabling service failed; continuing")

        return {"installed": True, "skipped": False, "msg": "postgresql installed"}
    except subprocess.CalledProcessError as e:
        return {"installed": False, "error": str(e), "cmd": cmd_str}


def setup_database(db_name='panel', db_user='panel', db_pass=None):
    """Create a database and user for the Panel app. Requires postgres superuser access."""
    # Use sudo -u postgres psql -c statements on Linux
    try:
        import shlex
        create_user = f"CREATE USER {db_user} WITH PASSWORD '{db_pass}'" if db_pass else f"CREATE USER {db_user};"
        grant = f"CREATE DATABASE {db_name} OWNER {db_user};"
        subprocess.check_call(["sudo", "-u", "postgres", "psql", "-c", create_user])
        subprocess.check_call(["sudo", "-u", "postgres", "psql", "-c", grant])
        return {"created": True}
    except Exception as e:
        return {"created": False, "error": str(e)}


def uninstall(preserve_data=True, dry_run=False):
    """Uninstall PostgreSQL (best-effort). If preserve_data=True, only stops services and disables autostart; otherwise remove packages."""
    if dry_run:
        return {"uninstalled": False, "cmd": "(dry-run) stop/disable postgresql; optionally remove packages"}

    out = {"stopped": False, "disabled": False, "packages_removed": False}
    try:
        subprocess.check_call(["systemctl", "stop", "postgresql"])  # may fail on some systems
        out["stopped"] = True
    except Exception:
        pass

    try:
        subprocess.check_call(["systemctl", "disable", "postgresql"])  # may fail
        out["disabled"] = True
    except Exception:
        pass

    if not preserve_data:
        pm = get_package_manager()
        try:
            if pm in ("apt", None):
                subprocess.check_call(["apt-get", "remove", "-y", "postgresql", "postgresql-contrib"])
            elif pm == "dnf":
                subprocess.check_call(["dnf", "remove", "-y", "postgresql-server"])
            elif pm == "yum":
                subprocess.check_call(["yum", "remove", "-y", "postgresql-server"])
            elif pm == "pacman":
                subprocess.check_call(["pacman", "-Rns", "--noconfirm", "postgresql"])            
            out["packages_removed"] = True
        except Exception as e:
            out["packages_error"] = str(e)

    return out
