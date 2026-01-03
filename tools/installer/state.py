"""Installer state tracking and rollback helpers."""
import json
import os
import logging
from typing import Optional

log = logging.getLogger(__name__)

# Default state file location; if running as root use /var/lib/panel_installer, else cwd
try:
    _is_root = hasattr(os, "geteuid") and os.geteuid() == 0
except Exception:
    _is_root = False
DEFAULT_STATE_PATH = "/var/lib/panel_installer/state.json" if _is_root else os.path.abspath("installer_state.json")


def _ensure_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def read_state(path: Optional[str] = None):
    path = path or DEFAULT_STATE_PATH
    if not os.path.exists(path):
        return {"actions": [], "meta": {}}
    with open(path, "r") as f:
        return json.load(f)


def write_state(data, path: Optional[str] = None):
    path = path or DEFAULT_STATE_PATH
    _ensure_dir(path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def add_action(action: dict, path: Optional[str] = None):
    # enrich with timestamp and host info
    import time, platform
    state = read_state(path)
    action = {
        **action,
        "timestamp": int(time.time()),
        "host": {
            "os": platform.system(),
            "arch": platform.machine(),
        },
    }
    state.setdefault("actions", []).append(action)
    # update meta
    state.setdefault("meta", {})
    state["meta"]["last_action_ts"] = action["timestamp"]
    write_state(state, path)
    log.info("Recorded action to state: %s", action)


def clear_state(path: Optional[str] = None):
    write_state({"actions": [], "meta": {}}, path)


def rollback(preserve_data=True, dry_run=False, path: Optional[str] = None):
    """Attempt rollback by undoing recorded actions in reverse order.

    Behavior:
      - Actions are attempted in reverse-install order.
      - On success the action is removed from the state file.
      - On failure the action is left in the state file so an operator can retry or inspect.
      - In dry-run mode actions are reported but not executed; state remains unchanged and remaining reflects current actions.

    Returns a dict with per-action results and the remaining actions in state.
    """
    state = read_state(path)
    actions = state.get("actions", [])
    results = []
    remaining = list(actions)

    # Process in reverse order (last installed first)
    for a in list(actions)[::-1]:
        comp = a.get("component")
        res = {"component": comp, "action": a, "result": None}
        if dry_run:
            res["result"] = "dry-run"
            results.append(res)
            continue

        try:
            # Import component uninstall handler dynamically
            try:
                from .components import postgres, redis, nginx, pythonenv  # type: ignore
                mapping = {"postgres": postgres, "redis": redis, "nginx": nginx, "python": pythonenv}
                mod = mapping.get(comp)
            except Exception:
                mod = None

            if mod and hasattr(mod, "uninstall"):
                # pass through venv path for python component if present
                kwargs = {"preserve_data": preserve_data}
                if comp == "python":
                    target = a.get("meta", {}).get("path") or "/opt/panel/venv"
                    kwargs["target"] = target
                r = mod.uninstall(**kwargs)
                res["result"] = r
                # success => remove the corresponding original action from remaining
                if isinstance(r, dict) and (r.get("uninstalled") or r.get("stopped") or r.get("packages_removed") or r.get("ok")):
                    # find and remove matching action (by identity)
                    for i in range(len(remaining)-1, -1, -1):
                        if remaining[i] == a:
                            del remaining[i]
                            break
            else:
                res["result"] = {"error": "no_uninstall_handler"}
        except Exception as e:
            res["result"] = {"error": str(e)}

        results.append(res)

    # Persist state mutations only when not dry-run
    if not dry_run:
        write_state({"actions": remaining, "meta": state.get("meta", {})}, path)
        remaining_count = len(remaining)
    else:
        remaining_count = len(actions)

    return {"status": "ok", "results": results, "remaining": remaining_count, "meta": state.get("meta", {})}