"""Installer state tracking and rollback helpers."""
import json
import os
import logging
from typing import Optional

log = logging.getLogger(__name__)

# Default state file location; if running as root use /var/lib/panel_installer, else cwd
DEFAULT_STATE_PATH = "/var/lib/panel_installer/state.json" if os.geteuid() == 0 else os.path.abspath("installer_state.json")


def _ensure_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def read_state(path: Optional[str] = None):
    path = path or DEFAULT_STATE_PATH
    if not os.path.exists(path):
        return {"actions": []}
    with open(path, "r") as f:
        return json.load(f)


def write_state(data, path: Optional[str] = None):
    path = path or DEFAULT_STATE_PATH
    _ensure_dir(path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def add_action(action: dict, path: Optional[str] = None):
    state = read_state(path)
    state.setdefault("actions", []).append(action)
    write_state(state, path)
    log.info("Recorded action to state: %s", action)


def clear_state(path: Optional[str] = None):
    write_state({"actions": []}, path)


def rollback(preserve_data=True, dry_run=False, path: Optional[str] = None):
    """Attempt rollback by undoing recorded actions in reverse order.

    For each recorded action we try to call a component-specific uninstall handler.
    This is best-effort and will continue on errors, collecting results.
    """
    state = read_state(path)
    actions = state.get("actions", [])[::-1]
    results = []

    for a in actions:
        comp = a.get("component")
        res = {"component": comp, "action": a, "result": None}
        if dry_run:
            res["result"] = "dry-run"
            results.append(res)
            continue

        try:
            # Import component uninstall handler dynamically
            mod = None
            try:
                from .components import postgres, redis, nginx, pythonenv  # type: ignore
                mapping = {"postgres": postgres, "redis": redis, "nginx": nginx, "python": pythonenv}
                mod = mapping.get(comp)
            except Exception:
                mod = None

            if mod and hasattr(mod, "uninstall"):
                r = mod.uninstall(preserve_data=preserve_data)
                res["result"] = r
            else:
                res["result"] = {"error": "no_uninstall_handler"}
        except Exception as e:
            res["result"] = {"error": str(e)}

        results.append(res)

    # After attempted rollback, clear state (we could preserve on errors but clear for now)
    clear_state(path)
    return {"status": "ok", "results": results}