import logging
from .deps import check_system_deps
from .os_utils import is_admin, ensure_elevated

log = logging.getLogger(__name__)

# Service name mapping per component
_SERVICE_MAP = {
    "postgres": "postgresql",
    "redis": "redis-server",
    "nginx": "nginx",
    # python env typically doesn't have a system service; leave None
    "python": None,
}


def start_component_service(component: str):
    name = _SERVICE_MAP.get(component)
    if not name:
        return False
    try:
        from .service_manager import enable_service, start_service
        enable_service(name)
        start_service(name)
        return True
    except Exception as e:
        log.debug("Failed to start service for %s: %s", component, e)
        return False


def stop_component_service(component: str):
    name = _SERVICE_MAP.get(component)
    if not name:
        return False
    try:
        from .service_manager import stop_service, disable_service
        # stop first, then optionally disable
        stop_service(name)
        try:
            disable_service(name)
        except Exception:
            pass
        return True
    except Exception as e:
        log.debug("Failed to stop service for %s: %s", component, e)
        return False


def install_all(domain, components, elevate=True, dry_run=False, progress_cb=None):
    """High level install orchestrator (stub/PoC).

    - domain: domain name string
    - components: list of component keys to install (postgres, redis, nginx, python)
    - elevate: whether to ensure admin rights
    - dry_run: only check / report actions
    - progress_cb: optional callable(step:str, component:str, meta:dict)
    """
    if elevate and not is_admin():
        # Attempt to re-run elevated; ensure_elevated() will re-exec or raise on failure.
        try:
            ensure_elevated()
        except Exception as e:
            raise RuntimeError(f"Elevation failed: {e}")

    missing = check_system_deps()
    if missing:
        log.warning("Missing system dependencies: %s", missing)
        if dry_run:
            if progress_cb:
                progress_cb("deps", "system", {"missing": missing})
            return {"status": "dry-run", "missing": missing}

    log.info("Starting install for domain %s with components %s", domain, components)

    from .components import postgres as pg, redis as rd
    actions = []

    for c in components:
        try:
            if progress_cb:
                progress_cb("start", c, {})
            if c == "postgres":
                res = pg.install(dry_run=dry_run)
                actions.append({"component": "postgres", "result": res})
                if progress_cb:
                    progress_cb("installed", c, res)
                if not dry_run and res.get("installed"):
                    started = start_component_service("postgres")
                    if progress_cb:
                        progress_cb("service", c, {"service": _SERVICE_MAP.get("postgres"), "started": started})
                    try:
                        from .state import add_action
                        add_action({"component": "postgres", "meta": res})
                    except Exception:
                        log.debug("Failed to write install state for postgres")

            elif c == "redis":
                res = rd.install(dry_run=dry_run)
                actions.append({"component": "redis", "result": res})
                if progress_cb:
                    progress_cb("installed", c, res)
                if not dry_run and res.get("installed"):
                    started = start_component_service("redis")
                    if progress_cb:
                        progress_cb("service", c, {"service": _SERVICE_MAP.get("redis"), "started": started})
                    try:
                        from .state import add_action
                        add_action({"component": "redis", "meta": res})
                    except Exception:
                        log.debug("Failed to write install state for redis")

            elif c == "nginx":
                from .components import nginx as ng
                res = ng.install(dry_run=dry_run)
                actions.append({"component": "nginx", "result": res})
                if progress_cb:
                    progress_cb("installed", c, res)
                if not dry_run and res.get("installed"):
                    started = start_component_service("nginx")
                    if progress_cb:
                        progress_cb("service", c, {"service": _SERVICE_MAP.get("nginx"), "started": started})
                    try:
                        from .state import add_action
                        add_action({"component": "nginx", "meta": res})
                    except Exception:
                        log.debug("Failed to write install state for nginx")

            elif c == "python":
                from .components import pythonenv as pyenv
                res = pyenv.install(dry_run=dry_run, target='/opt/panel/venv')
                actions.append({"component": "python", "result": res})
                if progress_cb:
                    progress_cb("installed", c, res)
                if not dry_run and res.get("installed"):
                    try:
                        from .state import add_action
                        add_action({"component": "python", "meta": res})
                    except Exception:
                        log.debug("Failed to write install state for pythonenv")

            else:
                log.info("No installer implemented for component: %s", c)
                actions.append({"component": c, "result": "not-implemented"})
                if progress_cb:
                    progress_cb("skipped", c, {"reason": "not-implemented"})
        except Exception as e:
            actions.append({"component": c, "result": "error", "error": str(e)})
            if progress_cb:
                progress_cb("error", c, {"error": str(e)})
        finally:
            if progress_cb:
                progress_cb("done", c, {})

    return {"status": "ok", "actions": actions}


def uninstall_all(preserve_data=True, dry_run=False, components=None, progress_cb=None):
    if not is_admin():
        raise RuntimeError("Admin rights are required to uninstall")

    # Stop services for selected components before rollback
    if components:
        for c in components:
            stopped = stop_component_service(c)
            if progress_cb:
                progress_cb("service_stop", c, {"service": _SERVICE_MAP.get(c), "stopped": stopped})

    # Use state-based rollback if available
    from .state import rollback, read_state
    state = read_state()
    actions = state.get("actions", [])

    if not actions:
        log.info("No recorded install actions found; nothing to uninstall via state. Returning ok.")
        return {"status": "no-actions"}

    log.info("Starting rollback of %d actions (preserve_data=%s, dry_run=%s, components=%s)", len(actions), preserve_data, dry_run, components)
    return rollback(preserve_data=preserve_data, dry_run=dry_run, components=components, progress_cb=progress_cb)
