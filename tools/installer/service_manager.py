"""Service manager abstractions (stubs for PoC).

Implementations should cover systemd (Linux), launchd (macOS), and Windows Service.
"""
import platform
import logging
import shutil
import subprocess

log = logging.getLogger(__name__)


def _run(cmd, shell=False):
    """Run a command and capture output to avoid noisy stderr in terminal.

    Returns a dict with ok, stdout, stderr, and optional error.
    """
    try:
        if shell:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:
            res = subprocess.run(cmd, capture_output=True, text=True)
        return {
            "ok": res.returncode == 0,
            "stdout": (res.stdout or "").strip(),
            "stderr": (res.stderr or "").strip(),
        }
    except Exception as e:
        log.debug("Command failed: %s (%s)", cmd, e)
        return {"ok": False, "error": str(e)}


def enable_service(name):
    """Enable a service to start at boot (best-effort). Returns a dict with result."""
    osname = platform.system()
    log.info("Enabling service %s on %s", name, osname)

    if osname == "Linux":
        if shutil.which("systemctl"):
            return _run(["systemctl", "enable", name])
        else:
            return {"ok": False, "error": "systemctl not available"}

    if osname == "Darwin":
        # Try brew services if available
        if shutil.which("brew"):
            return _run(["brew", "services", "start", name])
        # Otherwise we don't have a generic way to enable; return generic message
        return {"ok": False, "error": "no known enable method for service"}

    if osname == "Windows":
        # Use sc to configure start= auto
        if shutil.which("sc"):
            return _run(["sc", "config", name, "start=", "auto"])
        return {"ok": False, "error": "sc not available"}

    return {"ok": False, "error": f"unsupported OS: {osname}"}


def start_service(name):
    """Start the named service (best-effort)."""
    osname = platform.system()
    log.info("Starting service %s on %s", name, osname)

    if osname == "Linux":
        if shutil.which("systemctl"):
            return _run(["systemctl", "start", name])
        return {"ok": False, "error": "systemctl not available"}

    if osname == "Darwin":
        if shutil.which("brew"):
            return _run(["brew", "services", "start", name])
        return {"ok": False, "error": "no known start method for service"}

    if osname == "Windows":
        if shutil.which("sc"):
            return _run(["sc", "start", name])
        return {"ok": False, "error": "sc not available"}

    return {"ok": False, "error": f"unsupported OS: {osname}"}


def stop_service(name):
    """Stop the named service (best-effort)."""
    osname = platform.system()
    log.info("Stopping service %s on %s", name, osname)

    if osname == "Linux":
        if shutil.which("systemctl"):
            return _run(["systemctl", "stop", name])
        return {"ok": False, "error": "systemctl not available"}

    if osname == "Darwin":
        if shutil.which("brew"):
            return _run(["brew", "services", "stop", name])
        return {"ok": False, "error": "no known stop method for service"}

    if osname == "Windows":
        if shutil.which("sc"):
            return _run(["sc", "stop", name])
        return {"ok": False, "error": "sc not available"}

    return {"ok": False, "error": f"unsupported OS: {osname}"}


def service_status(name):
    """Get service status details. Returns dict with keys:
    - ok: bool
    - status: str (e.g., 'active', 'inactive', 'running', 'stopped', 'unknown')
    - enabled: Optional[str] ('enabled'|'disabled'|'unknown')
    - raw: Optional[str] (raw output for debugging)
    - error: Optional[str]
    """
    osname = platform.system()
    log.info("Checking service status %s on %s", name, osname)

    try:
        if osname == "Linux":
            if shutil.which("systemctl"):
                try:
                    out_active = subprocess.check_output(["systemctl", "is-active", name], text=True).strip()
                except subprocess.CalledProcessError as e:
                    out_active = e.output.strip() if hasattr(e, "output") and e.output else "unknown"
                try:
                    out_enabled = subprocess.check_output(["systemctl", "is-enabled", name], text=True).strip()
                except subprocess.CalledProcessError as e:
                    out_enabled = e.output.strip() if hasattr(e, "output") and e.output else "unknown"
                return {
                    "ok": True,
                    "status": out_active or "unknown",
                    "enabled": out_enabled or "unknown",
                }
            return {"ok": False, "status": "unknown", "enabled": "unknown", "error": "systemctl not available"}

        if osname == "Darwin":
            if shutil.which("brew"):
                try:
                    out = subprocess.check_output(["brew", "services", "list"], text=True)
                    status = "unknown"
                    enabled = "unknown"
                    for line in out.splitlines():
                        # Format example: name  state  user  file
                        parts = [p for p in line.split() if p]
                        if not parts:
                            continue
                        if parts[0] == name:
                            # state can be 'started', 'stopped', 'none'
                            state = parts[1] if len(parts) > 1 else "unknown"
                            status = {
                                "started": "running",
                                "stopped": "stopped",
                            }.get(state, state)
                            enabled = "enabled" if state == "started" else "disabled"
                            break
                    return {"ok": True, "status": status, "enabled": enabled}
                except Exception as e:
                    return {"ok": False, "status": "unknown", "enabled": "unknown", "error": str(e)}
            return {"ok": False, "status": "unknown", "enabled": "unknown", "error": "brew not available"}

        if osname == "Windows":
            if shutil.which("sc"):
                try:
                    out = subprocess.check_output(["sc", "query", name], text=True)
                    state_map = {
                        "1": "stopped",
                        "2": "start_pending",
                        "3": "stop_pending",
                        "4": "running",
                        "5": "continue_pending",
                        "6": "pause_pending",
                        "7": "paused",
                    }
                    status = "unknown"
                    for line in out.splitlines():
                        line = line.strip()
                        if line.startswith("STATE"):
                            parts = [p for p in line.split() if p]
                            # e.g., ['STATE', ':', '4', 'RUNNING']
                            if len(parts) >= 3:
                                code = parts[2]
                                status = state_map.get(code, parts[-1].lower())
                            break
                    return {"ok": True, "status": status, "enabled": "unknown", "raw": out}
                except Exception as e:
                    return {"ok": False, "status": "unknown", "enabled": "unknown", "error": str(e)}
            return {"ok": False, "status": "unknown", "enabled": "unknown", "error": "sc not available"}

        return {"ok": False, "status": "unknown", "enabled": "unknown", "error": f"unsupported OS: {osname}"}
    except Exception as e:
        log.debug("service_status failure: %s", e)
        return {"ok": False, "status": "unknown", "enabled": "unknown", "error": str(e)}


def service_exists(name):
    """Return True if the service unit exists on the current platform.

    Best-effort per OS:
      - Linux: systemd -> `systemctl cat <name>`; True if exit code 0
      - macOS: brew services list contains the name
      - Windows: `sc query <name>` returns ok
    """
    osname = platform.system()
    try:
        if osname == "Linux":
            if shutil.which("systemctl"):
                res = _run(["systemctl", "cat", name])
                return bool(res.get("ok"))
            return False
        if osname == "Darwin":
            if shutil.which("brew"):
                try:
                    out = subprocess.check_output(["brew", "services", "list"], text=True)
                    for line in out.splitlines():
                        parts = [p for p in line.split() if p]
                        if parts and parts[0] == name:
                            return True
                    return False
                except Exception:
                    return False
            return False
        if osname == "Windows":
            if shutil.which("sc"):
                res = _run(["sc", "query", name])
                return bool(res.get("ok"))
            return False
        return False
    except Exception:
        return False
