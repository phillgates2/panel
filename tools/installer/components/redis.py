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
    # Important: redis-cli can be installed standalone via redis-tools; we
    # consider Redis "installed" only when the server is present.
    return shutil.which("redis-server") is not None


def _try_systemctl(*args: str) -> bool:
    if not shutil.which("systemctl"):
        return False
    try:
        subprocess.check_call(["systemctl", *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _redis_service_candidates() -> list[str]:
    # Debian/Ubuntu typically: redis-server
    # Some distros: redis
    return ["redis-server", "redis"]


def _start_enable_redis_service() -> dict:
    """Best-effort enable+start Redis service.

    Returns dict with ok/service used.
    """
    if not shutil.which("systemctl"):
        return {"ok": False, "error": "systemctl not available"}

    # Prefer an existing unit name if any.
    existing = None
    for name in _redis_service_candidates():
        if _try_systemctl("cat", name):
            existing = name
            break

    # If we can't find an existing unit, still try the common one.
    to_try = [existing] if existing else []
    to_try += [n for n in _redis_service_candidates() if n not in to_try]

    last_error = None
    for svc in to_try:
        if not svc:
            continue
        if _try_systemctl("enable", svc) and _try_systemctl("start", svc):
            return {"ok": True, "service": svc}
        last_error = f"failed to enable/start {svc}"
    return {"ok": False, "error": last_error or "unable to enable/start redis service"}


def install(dry_run=False, target=None, elevate=True):
    if is_installed():
        svc_res = _start_enable_redis_service()
        # Even if service start fails, the server binary exists; report installed.
        out = {"installed": True, "skipped": True, "msg": "redis-server already available"}
        if svc_res.get("ok"):
            out["service"] = svc_res.get("service")
        else:
            out["service_error"] = svc_res.get("error")
        return out

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

        svc_res = _start_enable_redis_service()
        out = {"installed": True, "skipped": False, "msg": "redis installed"}
        if svc_res.get("ok"):
            out["service"] = svc_res.get("service")
        else:
            out["service_error"] = svc_res.get("error")
        return out
    except subprocess.CalledProcessError as e:
        return {"installed": False, "error": str(e), "cmd": cmd_str}


def uninstall(preserve_data=True, dry_run=False):
    if dry_run:
        return {"uninstalled": False, "cmd": "(dry-run) stop/disable redis; optionally remove packages"}

    out = {"stopped": False, "disabled": False, "packages_removed": False}
    try:
        for svc in _redis_service_candidates():
            try:
                subprocess.check_call(["systemctl", "stop", svc])
                out["stopped"] = True
            except Exception:
                pass
        for svc in _redis_service_candidates():
            try:
                subprocess.check_call(["systemctl", "disable", svc])
                out["disabled"] = True
            except Exception:
                pass
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
