import logging
import os
from .deps import check_system_deps
from .os_utils import is_admin, ensure_elevated
import platform
import secrets
import string
from datetime import date

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
    "panel": {
        "Linux": "panel-gunicorn",
        "Darwin": "panel",
        "Windows": "Panel",
    },
}


def _ensure_panel_systemd_unit(venv_path: str, workdir: str, port: int = 8080) -> bool:
    """Best-effort creation of a systemd unit for the Panel gunicorn service.

    This installer currently does not lay down application code into a fixed
    install directory; in SSH mode the most reliable assumption is that the
    current working directory is the repo root containing `app.py`.

    Returns True if the unit file was written successfully.
    """
    if platform.system() != "Linux":
        return False
    import shutil
    import subprocess

    if not shutil.which("systemctl"):
        return False

    unit_name = "panel-gunicorn.service"
    unit_path = os.path.join("/etc/systemd/system", unit_name)
    gunicorn = os.path.join(venv_path, "bin", "gunicorn")

    python = os.path.join(venv_path, "bin", "python")
    app_py = os.path.join(workdir, "app.py")

    use_gunicorn = os.path.exists(gunicorn)
    if not use_gunicorn:
        # Fall back to the built-in Flask dev server via `python app.py`.
        # This is not ideal for production but keeps the installer PoC usable
        # without requiring extra packages.
        if not (os.path.exists(python) and os.path.exists(app_py)):
            return False

    if use_gunicorn:
        exec_start = f"{gunicorn} --bind 0.0.0.0:{port} --workers 4 app:app"
        extra_env = ""
    else:
        exec_start = f"{python} {app_py}"
        extra_env = f"Environment=HOST=0.0.0.0\nEnvironment=PORT={port}\nEnvironment=FLASK_DEBUG=0\n"

    content = f"""[Unit]
Description=Panel
After=network.target

[Service]
Type=simple
WorkingDirectory={workdir}
Environment=PATH={venv_path}/bin
{extra_env}ExecStart={exec_start}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

    try:
        os.makedirs(os.path.dirname(unit_path), exist_ok=True)
        with open(unit_path, "w", encoding="utf-8") as f:
            f.write(content)
        # Reload systemd so it sees the new unit.
        subprocess.check_call(["systemctl", "daemon-reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _service_name(component):
    osname = platform.system()
    mapping = SERVICE_MAP.get(component, {})
    return mapping.get(osname, mapping.get("Linux"))


def start_component_service(component: str):
    name = _service_name(component)
    if not name:
        return False
    try:
        from .service_manager import enable_service, start_service, service_exists
        if not service_exists(name):
            # Service unit not present; skip attempts
            return False
        en = enable_service(name)
        st = start_service(name)
        return bool(en.get("ok") and st.get("ok"))
    except Exception as e:
        log.debug("Failed to start service for %s: %s", component, e)
        return False


def stop_component_service(component: str):
    name = _service_name(component)
    if not name:
        return False
    try:
        from .service_manager import stop_service, disable_service
        stop_service(name)
        try:
            disable_service(name)
        except Exception:
            pass
        return True
    except Exception as e:
        log.debug("Failed to stop service for %s: %s", component, e)
        return False


def get_component_service_status(component: str):
    """Return service status dict for a component using platform-specific manager."""
    name = _service_name(component)
    if not name:
        return {"ok": False, "status": "unknown", "enabled": "unknown", "error": "no service name"}
    try:
        from .service_manager import service_status
        res = service_status(name)
        # Attach resolved service name for context
        res["service"] = name
        return res
    except Exception as e:
        log.debug("Failed to get service status for %s: %s", component, e)
        return {"ok": False, "status": "unknown", "enabled": "unknown", "error": str(e), "service": name}


def _generate_strong_password(length: int = 20) -> str:
    """Generate a password that satisfies Panel's complexity rules.

    Requirements (per src/panel/models.py):
    - >= 12 chars
    - at least one uppercase, lowercase, digit, special
    """
    length = max(int(length or 0), 12)
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    special = '!@#$%^&*(),.?":{}|<>'
    # Ensure at least one of each category.
    chars = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(special),
    ]
    all_chars = upper + lower + digits + special
    while len(chars) < length:
        chars.append(secrets.choice(all_chars))
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def ensure_default_admin_user(
    *,
    admin_email: str | None = None,
    admin_password: str | None = None,
    db_uri: str | None = None,
    progress_cb=None,
) -> dict:
    """Create a default system admin user if none exists.

    This is intentionally best-effort: it will not crash installation if Panel
    app dependencies aren't installed.
    """
    email = (admin_email or os.environ.get("PANEL_ADMIN_EMAIL") or "admin@panel.local").strip().lower()
    password = (admin_password or os.environ.get("PANEL_ADMIN_PASS") or os.environ.get("PANEL_ADMIN_PASSWORD") or "").strip()
    generated = False
    if not password:
        password = _generate_strong_password()
        generated = True

    # Default to Panel's dev sqlite database if db_uri isn't provided.
    # Note: this is relative to the current working directory.
    uri = db_uri or os.environ.get("PANEL_SQLITE_URI") or "sqlite:///panel_dev.db"

    if progress_cb:
        progress_cb("bootstrap", "panel", {"action": "ensure_default_admin_user", "email": email, "db_uri": uri})

    try:
        # Import lazily so the installer can still run in minimal environments.
        from flask import Flask
        from app.db import db
        from src.panel.models import User

        app = Flask("panel-installer-bootstrap")
        app.config.update(
            SECRET_KEY=os.environ.get("PANEL_SECRET_KEY", "installer-bootstrap"),
            SQLALCHEMY_DATABASE_URI=uri,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            TESTING=False,
        )
        db.init_app(app)

        with app.app_context():
            # Ensure schema exists for the User model at least.
            try:
                db.create_all()
            except Exception as e:
                if progress_cb:
                    progress_cb("bootstrap", "panel", {"action": "create_all_failed", "error": str(e)})

            existing_admin = User.query.filter_by(role="system_admin").first()
            if existing_admin:
                return {
                    "ok": True,
                    "created": False,
                    "reason": "system_admin_exists",
                    "email": getattr(existing_admin, "email", None),
                    "password_generated": False,
                }

            # Prefer upgrading an existing account with matching email.
            user = User.query.filter_by(email=email).first()
            if user:
                user.role = "system_admin"
            else:
                user = User(
                    first_name="Admin",
                    last_name="User",
                    email=email,
                    dob=date(1990, 1, 1),
                    role="system_admin",
                )
                db.session.add(user)

            user.set_password(password)
            db.session.commit()

            result = {
                "ok": True,
                "created": True,
                "email": email,
                "password_generated": generated,
            }
            if generated:
                # Only return the password when generated by the installer.
                result["generated_password"] = password
            return result
    except Exception as e:
        if progress_cb:
            progress_cb("bootstrap", "panel", {"action": "ensure_default_admin_user_failed", "error": str(e)})
        return {"ok": False, "created": False, "error": str(e), "email": email, "password_generated": generated}


def install_all(
    domain,
    components,
    elevate=True,
    dry_run=False,
    progress_cb=None,
    venv_path="/opt/panel/venv",
    auto_start=True,
    *,
    create_default_user: bool = True,
    admin_email: str | None = None,
    admin_password: str | None = None,
    db_uri: str | None = None,
):
    """High level install orchestrator (stub/PoC).

    - domain: domain name string
    - components: list of component keys to install (postgres, redis, nginx, python)
    - elevate: whether to ensure admin rights
    - dry_run: only check / report actions
    - progress_cb: optional callable(step:str, component:str, meta:dict)
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
            if progress_cb:
                progress_cb("deps", "system", {"missing": missing})
            return {"status": "dry-run", "missing": missing}

    log.info("Starting install for domain %s with components %s", domain, components)

    from .components import postgres as pg, redis as rd
    actions = []
    errors = []

    for c in components:
        try:
            if progress_cb:
                progress_cb("start", c, {})
            if c == "postgres":
                res = pg.install(dry_run=dry_run, elevate=elevate)
                actions.append({"component": "postgres", "result": res})
                if progress_cb:
                    progress_cb("installed", c, res)
                if not dry_run and res.get("installed"):
                    from .service_manager import manager_available
                    if not manager_available():
                        if progress_cb:
                            progress_cb("skipped", c, {"service": _service_name("postgres"), "reason": "service manager not available"})
                    else:
                        started = start_component_service("postgres")
                        if progress_cb:
                            progress_cb("service", c, {"service": _service_name("postgres"), "started": started})
                    try:
                        from .state import add_action
                        add_action({"component": "postgres", "meta": res})
                    except Exception:
                        log.debug("Failed to write install state for postgres")

            elif c == "redis":
                res = rd.install(dry_run=dry_run, elevate=elevate)
                actions.append({"component": "redis", "result": res})
                if progress_cb:
                    progress_cb("installed", c, res)
                if not dry_run and res.get("installed"):
                    from .service_manager import manager_available
                    if not manager_available():
                        if progress_cb:
                            progress_cb("skipped", c, {"service": _service_name("redis"), "reason": "service manager not available"})
                    else:
                        started = start_component_service("redis")
                        if progress_cb:
                            progress_cb("service", c, {"service": _service_name("redis"), "started": started})
                    try:
                        from .state import add_action
                        add_action({"component": "redis", "meta": res})
                    except Exception:
                        log.debug("Failed to write install state for redis")

            elif c == "nginx":
                from .components import nginx as ng
                res = ng.install(dry_run=dry_run, elevate=elevate)
                actions.append({"component": "nginx", "result": res})
                if progress_cb:
                    progress_cb("installed", c, res)
                if not dry_run and res.get("installed"):
                    from .service_manager import manager_available
                    if not manager_available():
                        if progress_cb:
                            progress_cb("skipped", c, {"service": _service_name("nginx"), "reason": "service manager not available"})
                    else:
                        started = start_component_service("nginx")
                        if progress_cb:
                            progress_cb("service", c, {"service": _service_name("nginx"), "started": started})
                    try:
                        from .state import add_action
                        add_action({"component": "nginx", "meta": res})
                    except Exception:
                        log.debug("Failed to write install state for nginx")

            elif c == "python":
                from .components import pythonenv as pyenv
                res = pyenv.install(dry_run=dry_run, target=venv_path, elevate=elevate)
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

    # Best-effort: ensure a default admin user exists so the UI is accessible.
    if (not dry_run) and create_default_user:
        try:
            user_res = ensure_default_admin_user(
                admin_email=admin_email,
                admin_password=admin_password,
                db_uri=db_uri,
                progress_cb=progress_cb,
            )
            actions.append({"component": "panel", "result": {"default_user": user_res}})
            if progress_cb:
                progress_cb("bootstrap", "panel", user_res)
            if isinstance(user_res, dict) and not user_res.get("ok", False):
                errors.append({"component": "panel", "error": user_res.get("error") or "default user creation failed"})
        except Exception as e:
            if progress_cb:
                progress_cb("bootstrap", "panel", {"ok": False, "error": str(e)})
            errors.append({"component": "panel", "error": str(e)})

    # Attempt to start the Panel app service after install
    if not dry_run and auto_start:
        try:
            name = _service_name("panel")
            from .service_manager import service_exists, manager_available
            if not manager_available():
                if progress_cb:
                    progress_cb("skipped", "panel", {"service": name, "reason": "service manager not available"})
            elif not service_exists(name):
                # Best-effort: create a systemd unit on Linux so auto-start can work.
                created = False
                try:
                    created = _ensure_panel_systemd_unit(venv_path=venv_path, workdir=os.getcwd(), port=8080)
                except Exception:
                    created = False
                if progress_cb:
                    progress_cb(
                        "info",
                        "panel",
                        {"service": name, "action": "create_unit", "created": created, "workdir": os.getcwd(), "port": 8080},
                    )
                if not created:
                    if progress_cb:
                        progress_cb("skipped", "panel", {"service": name, "reason": "service unit not found"})
                else:
                    started = start_component_service("panel")
                    if progress_cb:
                        progress_cb("service", "panel", {"service": name, "started": started})
                    try:
                        from .state import add_action
                        add_action({"component": "panel", "meta": {"auto_start": True, "created_unit": True, "started": started}})
                    except Exception:
                        log.debug("Failed to write install state for panel auto-start")
            else:
                started = start_component_service("panel")
                if progress_cb:
                    progress_cb("service", "panel", {"service": name, "started": started})
                try:
                    from .state import add_action
                    add_action({"component": "panel", "meta": {"auto_start": True, "started": started}})
                except Exception:
                    log.debug("Failed to write install state for panel auto-start")
        except Exception as e:
            if progress_cb:
                progress_cb("error", "panel", {"error": str(e)})

    status = "ok" if not errors else "error"
    return {"status": status, "actions": actions, "errors": errors}


def uninstall_all(preserve_data=True, dry_run=False, components=None, progress_cb=None, elevate=True):
    # Allow dry-run without elevation/admin to enable safe simulation
    if elevate and not dry_run:
        if not is_admin():
            raise RuntimeError("Admin rights are required to uninstall")

    # Stop services for selected components before rollback
    if components:
        for c in components:
            stopped = stop_component_service(c)
            if progress_cb:
                progress_cb("service_stop", c, {"service": _service_name(c), "stopped": stopped})

    # Use state-based rollback if available
    from .state import rollback, read_state
    state = read_state()
    actions = state.get("actions", [])

    if not actions:
        log.info("No recorded install actions found; nothing to uninstall via state. Returning ok.")
        return {"status": "no-actions"}

    log.info("Starting rollback of %d actions (preserve_data=%s, dry_run=%s, components=%s)", len(actions), preserve_data, dry_run, components)
    return rollback(preserve_data=preserve_data, dry_run=dry_run, components=components, progress_cb=progress_cb)
