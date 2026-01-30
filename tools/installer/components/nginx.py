"""Nginx installer helpers (Linux-focused PoC).

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
    return shutil.which("nginx") is not None


def install(dry_run=False, target=None, elevate=True):
    if is_installed():
        return {"installed": True, "skipped": True, "msg": "nginx already available"}

    if not elevate:
        cmd_preview = "apt-get update && apt-get install -y nginx"
        if get_package_manager() and get_package_manager() != "apt":
            # Rough preview string for other managers
            cmd_preview = f"install nginx via {get_package_manager()}"
        return {
            "installed": False,
            "skipped": False,
            "error": "elevation required to install system package 'nginx'",
            "hint": "Re-run with elevation or install nginx manually",
            "cmd": cmd_preview,
        }

    pm = get_package_manager()
    if pm in ("apt", None):
        cmd = ["apt-get", "update", "&&", "apt-get", "install", "-y", "nginx"]
        shell = True
    elif pm == "dnf":
        cmd = ["dnf", "install", "-y", "nginx"]
        shell = False
    elif pm == "yum":
        cmd = ["yum", "install", "-y", "nginx"]
        shell = False
    elif pm == "pacman":
        cmd = ["pacman", "-Sy", "--noconfirm", "nginx"]
        shell = False
    elif pm == "apk":
        cmd = ["apk", "add", "nginx"]
        shell = False
    elif pm == "brew":
        cmd = ["brew", "install", "nginx"]
        shell = False
    elif pm in ("choco", "winget"):
        if pm == "choco":
            cmd = ["choco", "install", "nginx", "-y"]
        else:
            cmd = ["winget", "install", "--id", "nginx", "-e"]
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
            subprocess.check_call(["systemctl", "enable", "nginx"])
            subprocess.check_call(["systemctl", "start", "nginx"])
        except Exception:
            log.debug("systemctl not available or enabling service failed; continuing")

        return {"installed": True, "skipped": False, "msg": "nginx installed"}
    except subprocess.CalledProcessError as e:
        return {"installed": False, "error": str(e), "cmd": cmd_str}


def uninstall(preserve_data=True, dry_run=False):
    if dry_run:
        return {"uninstalled": False, "cmd": "(dry-run) stop/disable nginx; optionally remove packages"}

    out = {"stopped": False, "disabled": False, "packages_removed": False}
    try:
        subprocess.check_call(["systemctl", "stop", "nginx"])  # may fail
        out["stopped"] = True
    except Exception:
        pass

    try:
        subprocess.check_call(["systemctl", "disable", "nginx"])  # may fail
        out["disabled"] = True
    except Exception:
        pass

    if not preserve_data:
        pm = get_package_manager()
        try:
            if pm in ("apt", None):
                subprocess.check_call(["apt-get", "remove", "-y", "nginx"])
            elif pm in ("dnf", "yum"):
                subprocess.check_call([pm, "remove", "-y", "nginx"])
            elif pm == "pacman":
                subprocess.check_call(["pacman", "-Rns", "--noconfirm", "nginx"])
            out["packages_removed"] = True
        except Exception as e:
            out["packages_error"] = str(e)

    return out
