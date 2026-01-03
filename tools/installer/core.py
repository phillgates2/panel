import logging
from .deps import check_system_deps
from .os_utils import is_admin, ensure_elevated
import platform

log = logging.getLogger(__name__)

# Default service names per OS for components
SERVICE_MAP = {
    "postgres": {
        "Linux": "postgresql",
        "Darwin": "postgresql",
        "Windows": "postgresql-x64-16",  # best-effort default; may vary by version
    },
    "redis": {
        "Linux": "redis-server",
        "Darwin": "redis",
        "Windows": "Redis",
    },
    "nginx": {
        "Linux": "nginx",
        "Darwin": "nginx",
        "Windows": "nginx",
    },
}


def _service_name(component):
    osname = platform.system()
    mapping = SERVICE_MAP.get(component, {})
    return mapping.get(osname, mapping.get("Linux"))


def install_all(domain, components, elevate=True, dry_run=False, venv_path="/opt/panel/venv"):
    """High level install orchestrator (stub/PoC).

    - domain: domain name string
    - components: list of component keys to install (postgres, redis, nginx, python)
    - elevate: whether to ensure admin rights
    - dry_run: only check / report actions
    - venv_path: target path for python venv component
    """
    if elevate and not is_admin():
        # Skip elevation when dry_run to allow simulation without prompts.
        if not dry_run:
            try:
                ensure_elevated()
            except Exception as e:
                raise RuntimeError(f"Elevation failed: {e}")

    missing = check_system_deps()
    if missing:
        log.warning("Missing system dependencies: %s", missing)
        if dry_run:
            return {"status": "dry-run", "missing": missing}

    log.info("Starting install for domain %s with components %s", domain, components)

    # Execute installers for requested components
    from .components import postgres as pg, redis as rd
    actions = []

    for c in components:
        try:
            if c == "postgres":
                res = pg.install(dry_run=dry_run)
                actions.append({"component": "postgres", "result": res})
                if not dry_run and res.get("installed"):
                    try:
                        # enable/start service
                        from .service_manager import enable_service, start_service
                        svc = _service_name("postgres")
                        enable_service(svc)
                        start_service(svc)
                    except Exception:
                        log.debug("Failed to enable/start postgresql service via service_manager")
                    # record successful install to state
                    try:
                        from .state import add_action
                        add_action({"component": "postgres", "meta": res})
                    except Exception:
                        log.debug("Failed to write install state for postgres")

            elif c == "redis":
                res = rd.install(dry_run=dry_run)
                actions.append({"component": "redis", "result": res})
                if not dry_run and res.get("installed"):
                    try:
                        from .service_manager import enable_service, start_service
                        svc = _service_name("redis")
                        enable_service(svc)
                        start_service(svc)
                    except Exception:
                        log.debug("Failed to enable/start redis service via service_manager")
                    try:
                        from .state import add_action
                        add_action({"component": "redis", "meta": res})
                    except Exception:
                        log.debug("Failed to write install state for redis")

            elif c == "nginx":
                from .components import nginx as ng
                res = ng.install(dry_run=dry_run)
                actions.append({"component": "nginx", "result": res})
                if not dry_run and res.get("installed"):
                    try:
                        from .service_manager import enable_service, start_service
                        svc = _service_name("nginx")
                        enable_service(svc)
                        start_service(svc)
                    except Exception:
                        log.debug("Failed to enable/start nginx service via service_manager")
                    try:
                        from .state import add_action
                        add_action({"component": "nginx", "meta": res})
                    except Exception:
                        log.debug("Failed to write install state for nginx")

            elif c == "python":
                from .components import pythonenv as pyenv
                # configurable target path
                res = pyenv.install(dry_run=dry_run, target=venv_path)
                actions.append({"component": "python", "result": res})
                if not dry_run and res.get("installed"):
                    try:
                        from .state import add_action
                        add_action({"component": "python", "meta": res})
                    except Exception:
                        log.debug("Failed to write install state for pythonenv")

            else:
                log.info("No installer implemented for component: %s", c)
                actions.append({"component": c, "result": "not-implemented"})
        except Exception as e:
            actions.append({"component": c, "result": "error", "error": str(e)})

    return {"status": "ok", "actions": actions}


def uninstall_all(preserve_data=True, dry_run=False, elevate=True):
    # Allow dry-run without elevation/admin to enable safe simulation
    if elevate and not dry_run:
        if not is_admin():
            raise RuntimeError("Admin rights are required to uninstall")

    # Use state-based rollback if available
    from .state import rollback, read_state
    state = read_state()
    actions = state.get("actions", [])

    if not actions:
        log.info("No recorded install actions found; nothing to uninstall via state. Returning ok.")
        return {"status": "no-actions"}

    log.info("Starting rollback of %d actions (preserve_data=%s, dry_run=%s)", len(actions), preserve_data, dry_run)
    return rollback(preserve_data=preserve_data, dry_run=dry_run)
