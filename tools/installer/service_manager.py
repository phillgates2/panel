"""Service manager abstractions (stubs for PoC).

Implementations should cover systemd (Linux), launchd (macOS), and Windows Service.
"""
import platform
import logging
import shutil
import subprocess

log = logging.getLogger(__name__)


def _run(cmd, shell=False):
    try:
        if shell:
            subprocess.check_call(cmd, shell=True)
        else:
            subprocess.check_call(cmd)
        return {"ok": True}
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
        # Otherwise we don't have a generic way to enable; return helpful message
        return {"ok": False, "error": "no known enable method on macOS for service"}

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
        return {"ok": False, "error": "no known start method on macOS for service"}

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
        return {"ok": False, "error": "no known stop method on macOS for service"}

    if osname == "Windows":
        if shutil.which("sc"):
            return _run(["sc", "stop", name])
        return {"ok": False, "error": "sc not available"}

    return {"ok": False, "error": f"unsupported OS: {osname}"}
