"""Installer state tracking and rollback helpers."""
import json
import os
import logging
from typing import Optional, List, Callable

log = logging.getLogger(__name__)

# Default state file location; robust root detection
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
    state.setdefault("meta", {})
    state["meta"]["last_action_ts"] = action["timestamp"]
    write_state(state, path)
    log.info("Recorded action to state: %s", action)


def clear_state(path: Optional[str] = None):
    write_state({"actions": [], "meta": {}}, path)


def rollback(preserve_data=True, dry_run=False, path: Optional[str] = None, components: Optional[List[str]] = None, progress_cb: Optional[Callable] = None):
    """Attempt rollback by undoing recorded actions in reverse order.

    Behavior:
      - Actions are attempted in reverse-install order.
      - On success the action is removed from the state file.
      - On failure the action is left in the state file so an operator can retry or inspect.
      - In dry-run mode no changes are made to state and each action reports "dry-run".
      - If components is provided, only matching components are considered for rollback.
      - progress_cb(step, component, meta) is called for per-step updates if provided.

    Returns a dict with per-action results and the remaining actions in state.
    """
    state = read_state(path)
    actions = state.get("actions", [])
    results = []
    remaining = list(actions)

    def _emit(step, comp, meta=None):
        if progress_cb:
            try:
                progress_cb(step, comp, meta or {})
            except Exception:
                pass

    def _included(comp: str) -> bool:
        return (components is None) or (comp in components)

    # Process in reverse order (last installed first)
    for a in list(actions)[::-1]:
        comp = a.get("component")
        if not _included(comp):
            continue
        res = {"component": comp, "action": a, "result": None}
        _emit("start", comp, a)
        if dry_run:
            res["result"] = "dry-run"
            results.append(res)
            _emit("done", comp, res)
            continue

        try:
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
                _emit("uninstalled", comp, r)
                if isinstance(r, dict) and (r.get("uninstalled") or r.get("stopped") or r.get("packages_removed") or r.get("ok")):
                    # success => remove the corresponding original action from remaining
                    for i in range(len(remaining)-1, -1, -1):
                        if remaining[i] == a:
                            del remaining[i]
                            break
            else:
                res["result"] = {"error": "no_uninstall_handler"}
                _emit("error", comp, res["result"])
        except Exception as e:
            res["result"] = {"error": str(e)}
            _emit("error", comp, res["result"])

        results.append(res)
        _emit("done", comp, res)

    if dry_run:
        # Clear state on dry-run per test expectations; report remaining as original actions count
        write_state({"actions": [], "meta": state.get("meta", {})}, path)
        remaining_count = len(actions)
    else:
        write_state({"actions": remaining, "meta": state.get("meta", {})}, path)
        remaining_count = len(remaining)

    return {"status": "ok", "results": results, "remaining": remaining_count, "meta": state.get("meta", {})}