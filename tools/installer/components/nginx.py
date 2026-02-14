"""Nginx installer helpers (Linux-focused PoC).

Provides:
 - is_installed()
 - install(dry_run=False)
"""
import os
import platform
import shutil
import subprocess
import logging
from ..deps import get_package_manager

log = logging.getLogger(__name__)


def is_installed():
    return shutil.which("nginx") is not None


def _write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _nginx_config_paths() -> tuple[str, str | None]:
    """Return (config_path, enable_path).

    - On Debian/Ubuntu: write to /etc/nginx/sites-available and symlink into sites-enabled
    - On most other distros: write to /etc/nginx/conf.d and no enable step
    """
    if os.path.isdir("/etc/nginx/sites-available") and os.path.isdir("/etc/nginx/sites-enabled"):
        cfg = "/etc/nginx/sites-available/panel.conf"
        enable = "/etc/nginx/sites-enabled/panel.conf"
        return cfg, enable
    return "/etc/nginx/conf.d/panel.conf", None


def configure_panel_reverse_proxy(
    *,
    domain: str,
    upstream_host: str = "127.0.0.1",
    upstream_port: int = 8080,
    listen_port: int = 80,
    dry_run: bool = False,
    elevate: bool = True,
) -> dict:
    """Best-effort write an Nginx vhost that proxies :80 -> Panel :8080.

    Includes WebSocket upgrade headers for Flask-SocketIO.
    """
    if platform.system() not in ("Linux", "Darwin"):
        return {"ok": False, "error": "nginx config automation not supported on this OS"}

    if not elevate:
        return {
            "ok": False,
            "error": "elevation required to write nginx config",
            "hint": "Re-run with elevation or configure nginx manually",
        }

    if not domain:
        domain = "localhost"

    cfg_path, enable_path = _nginx_config_paths()

    upstream = f"{upstream_host}:{int(upstream_port)}"
    content = f"""# Managed by Panel installer
server {{
    listen {int(listen_port)};
    server_name {domain};

    location / {{
        proxy_pass http://{upstream};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (Flask-SocketIO)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
}}
"""

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "config": cfg_path,
            "enable": enable_path,
            "upstream": upstream,
            "domain": domain,
        }

    try:
        _write_text(cfg_path, content)
        enabled = False
        if enable_path:
            try:
                if os.path.islink(enable_path) or os.path.exists(enable_path):
                    os.remove(enable_path)
                os.symlink(cfg_path, enable_path)
                enabled = True
            except Exception as e:
                return {"ok": False, "error": f"failed to enable nginx site: {e}", "config": cfg_path, "enable": enable_path}

        # Validate config before reloading.
        try:
            subprocess.check_call(["nginx", "-t"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            return {"ok": False, "error": f"nginx config test failed: {e}", "config": cfg_path, "enable": enable_path}

        reloaded = False
        try:
            subprocess.check_call(["systemctl", "reload", "nginx"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            reloaded = True
        except Exception:
            # Fallback to reload via nginx signal
            try:
                subprocess.check_call(["nginx", "-s", "reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                reloaded = True
            except Exception:
                reloaded = False

        return {
            "ok": True,
            "config": cfg_path,
            "enabled": enabled,
            "reloaded": reloaded,
            "upstream": upstream,
            "domain": domain,
            "listen_port": int(listen_port),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "config": cfg_path, "enable": enable_path}


def install(dry_run=False, target=None, elevate=True, **kwargs):
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
