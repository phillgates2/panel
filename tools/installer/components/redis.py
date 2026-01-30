"""Redis installer helpers (Linux-focused PoC).

Provides:
 - is_installed()
 - install(dry_run=False)
"""
import shutil
import subprocess
import logging
from ..deps import get_package_manager

log = logging.getLogger(__name__)


def is_installed():
    return shutil.which("redis-server") is not None or shutil.which("redis-cli") is not None


def install(dry_run=False, target=None, elevate=True):
    if is_installed():
        return {"installed": True, "skipped": True, "msg": "redis already available"}

    if not elevate:
        cmd_preview = "apt-get update && apt-get install -y redis-server"
        if get_package_manager() and get_package_manager() != "apt":
            cmd_preview = f"install redis via {get_package_manager()}"
        return {
            "installed": False,
            "skipped": False,
            "error": "elevation required to install system package 'redis'",
            "hint": "Re-run with elevation or install Redis manually",
            "cmd": cmd_preview,
        }

    pm = get_package_manager()
    if pm in ("apt", None):
        cmd = ["apt-get", "update", "&&", "apt-get", "install", "-y", "redis-server"]
        shell = True
    elif pm == "dnf":
        cmd = ["dnf", "install", "-y", "redis"]
        shell = False
    elif pm == "yum":
        cmd = ["yum", "install", "-y", "redis"]
        shell = False
    elif pm == "pacman":
        cmd = ["pacman", "-Sy", "--noconfirm", "redis"]
        shell = False
    elif pm == "apk":
        cmd = ["apk", "add", "redis"]
        shell = False
    elif pm == "brew":
        cmd = ["brew", "install", "redis"]
        shell = False
    elif pm in ("choco", "winget"):
        if pm == "choco":
            cmd = ["choco", "install", "redis-64", "-y"]
        else:
            cmd = ["winget", "install", "--id", "Redis.Redis", "-e"]
        shell = False
    else:
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

        try:
            subprocess.check_call(["systemctl", "enable", "redis-server"])
            subprocess.check_call(["systemctl", "start", "redis-server"])
        except Exception:
            log.debug("systemctl not available or enabling service failed; continuing")

        return {"installed": True, "skipped": False, "msg": "redis installed"}
    except subprocess.CalledProcessError as e:
        return {"installed": False, "error": str(e), "cmd": cmd_str}


def uninstall(preserve_data=True, dry_run=False):
    if dry_run:
        return {"uninstalled": False, "cmd": "(dry-run) stop/disable redis; optionally remove packages"}

    out = {"stopped": False, "disabled": False, "packages_removed": False}
    try:
        subprocess.check_call(["systemctl", "stop", "redis-server"])  # may fail
        out["stopped"] = True
    except Exception:
        pass

    try:
        subprocess.check_call(["systemctl", "disable", "redis-server"])  # may fail
        out["disabled"] = True
    except Exception:
        pass

    if not preserve_data:
        pm = get_package_manager()
        try:
            if pm in ("apt", None):
                subprocess.check_call(["apt-get", "remove", "-y", "redis-server"])
            elif pm in ("dnf", "yum"):
                subprocess.check_call([pm, "remove", "-y", "redis"])
            elif pm == "pacman":
                subprocess.check_call(["pacman", "-Rns", "--noconfirm", "redis"])
            out["packages_removed"] = True
        except Exception as e:
            out["packages_error"] = str(e)

    return out
