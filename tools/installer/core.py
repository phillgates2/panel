import json
import logging
import os
import re
import subprocess
import sys
import codecs
from pathlib import Path
from urllib.parse import urlparse, unquote, quote_plus
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


def _ensure_panel_systemd_unit(
    venv_path: str,
    workdir: str,
    port: int = 8080,
    *,
    env_file: str | None = None,
) -> bool:
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
        workers = int(os.environ.get("PANEL_GUNICORN_WORKERS", "4"))
        exec_start = (
            f"{gunicorn} --bind 0.0.0.0:{port} --workers {workers} "
            f"--access-logfile - --error-logfile - app:app"
        )
        extra_env = ""
    else:
        exec_start = f"{python} {app_py}"
        extra_env = f"Environment=HOST=0.0.0.0\nEnvironment=PORT={port}\nEnvironment=FLASK_DEBUG=0\n"

    env_file_line = ""
    if env_file:
        # Leading '-' means optional (systemd won't fail if missing).
        env_file_line = f"EnvironmentFile=-{env_file}\n"

    content = f"""[Unit]
Description=Panel
After=network.target

[Service]
Type=simple
WorkingDirectory={workdir}
Environment=PATH={venv_path}/bin
{env_file_line}{extra_env}ExecStart={exec_start}
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


def _best_effort_ensure_systemd_env_file(*, unit_name: str, env_file: str) -> bool:
    """Best-effort patch for existing systemd units to load an EnvironmentFile.

    This avoids a common drift where `/etc/panel/panel.env` is updated by the
    installer but the already-installed `panel-gunicorn.service` doesn't source
    it, causing the running service to use stale DB credentials.
    """
    if platform.system() != "Linux":
        return False
    try:
        import shutil

        if not shutil.which("systemctl"):
            return False

        candidates = [
            os.path.join("/etc/systemd/system", unit_name),
            os.path.join("/lib/systemd/system", unit_name),
            os.path.join("/usr/lib/systemd/system", unit_name),
        ]
        unit_path = next((p for p in candidates if os.path.exists(p)), None)
        if not unit_path:
            return False

        with open(unit_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "EnvironmentFile=" in content:
            return True

        lines = content.splitlines(True)
        for idx, line in enumerate(lines):
            if line.strip() == "[Service]":
                lines.insert(idx + 1, f"EnvironmentFile=-{env_file}\n")
                break
        else:
            return False

        with open(unit_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        subprocess.check_call(
            ["systemctl", "daemon-reload"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _normalize_env_name(env_name: str | None) -> str:
    name = (env_name or "").strip().lower()
    if name in ("prod", "production"):
        return "production"
    if name in ("stage", "staging"):
        return "staging"
    if name in ("test", "testing"):
        return "testing"
    return "development"


def _write_env_file(path: str, env_vars: dict[str, str], *, mode: int = 0o600) -> dict:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        def _escape(value: str) -> str:
            v = str(value)
            v = v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'"{v}"'

        lines: list[str] = []
        for key in sorted(env_vars.keys()):
            if not re.match(r"^[A-Z0-9_]+$", key):
                continue
            lines.append(f"{key}={_escape(env_vars[key])}")
        lines.append("")

        p.write_text("\n".join(lines), encoding="utf-8")
        try:
            os.chmod(str(p), mode)
        except Exception:
            pass
        return {"ok": True, "path": str(p), "keys": sorted(env_vars.keys())}
    except Exception as e:
        return {"ok": False, "path": path, "error": str(e)}


def _read_env_file(path: str | None) -> dict[str, str]:
    """Parse the installer-written env file (KEY="value" lines).

    The installer writes values with a minimal escaping scheme (\\, \", \n).
    This reader is intentionally conservative and ignores malformed lines.
    """
    if not path:
        return {}
    try:
        p = Path(path)
        if not p.exists():
            return {}
        env: dict[str, str] = {}
        for raw_line in p.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not re.match(r"^[A-Z0-9_]+$", key):
                continue

            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
                try:
                    value = codecs.decode(value, "unicode_escape")
                except Exception:
                    # Best-effort: keep raw string if decoding fails.
                    pass
            env[key] = value
        return env
    except Exception:
        return {}


def _start_panel_background(*, venv_path: str, workdir: str, port: int, env_file: str | None) -> dict:
    """Start Panel in the background without a service manager (systemd-less hosts).

    Returns: {ok: bool, pid?: int, log_path?: str, cmd?: str, error?: str}
    """
    try:
        gunicorn = os.path.join(venv_path, "bin", "gunicorn")
        python = os.path.join(venv_path, "bin", "python")
        app_py = os.path.join(workdir, "app.py")

        env = os.environ.copy()
        env.update(_read_env_file(env_file))
        env.setdefault("HOST", "0.0.0.0")
        env.setdefault("PORT", str(port))
        # Prevent Werkzeug reloader multi-process behavior.
        env["FLASK_DEBUG"] = "0"

        if os.path.exists(gunicorn):
            workers = int(env.get("PANEL_GUNICORN_WORKERS", "4"))
            cmd = [
                gunicorn,
                "--bind",
                f"0.0.0.0:{port}",
                "--workers",
                str(workers),
                "--access-logfile",
                "-",
                "--error-logfile",
                "-",
                "app:app",
            ]
        else:
            if not os.path.exists(app_py):
                return {"ok": False, "error": f"app.py not found at {app_py}"}
            if not os.path.exists(python):
                python = "python"
            cmd = [python, app_py]

        log_path = "/var/log/panel/app.out"
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            log_fp = open(log_path, "a", encoding="utf-8")
        except Exception:
            log_path = os.path.join(workdir, "app.out")
            log_fp = open(log_path, "a", encoding="utf-8")

        # Detach from the installer so the process survives after exit.
        proc = subprocess.Popen(
            cmd,
            cwd=workdir,
            env=env,
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        return {"ok": True, "pid": proc.pid, "log_path": log_path, "cmd": " ".join(cmd)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _parse_db_uri(db_uri: str | None) -> dict:
    if not db_uri:
        return {"ok": False, "type": "unknown"}
    uri = (db_uri or "").strip()
    if uri.lower().startswith("sqlite:"):
        return {"ok": False, "type": "sqlite", "error": "SQLite is not supported"}

    parsed = urlparse(uri)
    scheme = (parsed.scheme or "").lower()
    if scheme.startswith("postgres"):
        return {
            "ok": True,
            "type": "postgres",
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "host": parsed.hostname or "127.0.0.1",
            "port": str(parsed.port or 5432),
            "db_name": (parsed.path or "").lstrip("/"),
        }

    return {"ok": False, "type": "unknown", "scheme": scheme}


def _build_panel_env(
    *,
    env_name: str,
    domain: str,
    db_uri: str | None,
    redis_port: int | None = None,
    db_search_path: str | None = None,
) -> dict[str, str]:
    env: dict[str, str] = {
        "FLASK_ENV": _normalize_env_name(env_name),
    }

    if domain:
        env["PANEL_PUBLIC_BASE_URL"] = (
            "http://localhost" if domain.strip().lower() == "localhost" else f"http://{domain.strip()}"
        )

    env.setdefault(
        "PANEL_SECRET_KEY",
        os.environ.get("PANEL_SECRET_KEY") or os.environ.get("SECRET_KEY") or secrets.token_urlsafe(48),
    )

    db = _parse_db_uri(db_uri)
    if db.get("type") == "postgres":
        env["PANEL_DB_USER"] = db.get("user") or "paneluser"
        env["PANEL_DB_PASS"] = db.get("password") or ""
        env["PANEL_DB_HOST"] = db.get("host") or "127.0.0.1"
        env["PANEL_DB_PORT"] = db.get("port") or "5432"
        env["PANEL_DB_NAME"] = db.get("db_name") or "paneldb"
        # Preserve the operator-provided DB URL verbatim when available.
        # This is important for Postgres SSL options (e.g. ?sslmode=require)
        # so we do not drop query parameters.
        if isinstance(db_uri, str) and db_uri.strip():
            env["DATABASE_URL"] = db_uri.strip()
        else:
            env["DATABASE_URL"] = (
                f"postgresql+psycopg2://{quote_plus(env['PANEL_DB_USER'])}:{quote_plus(env['PANEL_DB_PASS'])}@"
                f"{env['PANEL_DB_HOST']}:{env['PANEL_DB_PORT']}/{env['PANEL_DB_NAME']}"
            )

        # Allow explicit override from the installer GUI/CLI.
        sp = (db_search_path or os.environ.get("PANEL_DB_SEARCH_PATH") or "public").strip()
        # Avoid unsafe characters in a value that is later used in a libpq
        # runtime option (-c search_path=...). Keep it conservative.
        if ("\n" in sp) or ("\r" in sp) or (";" in sp):
            sp = "public"
        env["PANEL_DB_SEARCH_PATH"] = sp
    else:
        # Default: local Postgres.
        env.setdefault("PANEL_DB_USER", os.environ.get("PANEL_DB_USER", "paneluser"))
        env.setdefault("PANEL_DB_PASS", os.environ.get("PANEL_DB_PASS", "panelpass"))
        env.setdefault("PANEL_DB_HOST", os.environ.get("PANEL_DB_HOST", "127.0.0.1"))
        env.setdefault("PANEL_DB_PORT", os.environ.get("PANEL_DB_PORT", "5432"))
        env.setdefault("PANEL_DB_NAME", os.environ.get("PANEL_DB_NAME", "paneldb"))
        env.setdefault(
            "DATABASE_URL",
            f"postgresql+psycopg2://{quote_plus(env['PANEL_DB_USER'])}:{quote_plus(env['PANEL_DB_PASS'])}@{env['PANEL_DB_HOST']}:{env['PANEL_DB_PORT']}/{env['PANEL_DB_NAME']}",
        )
        sp = (db_search_path or os.environ.get("PANEL_DB_SEARCH_PATH") or "public").strip()
        if ("\n" in sp) or ("\r" in sp) or (";" in sp):
            sp = "public"
        env.setdefault("PANEL_DB_SEARCH_PATH", sp)

    rp = int(redis_port) if redis_port else 6379
    env.setdefault("PANEL_REDIS_URL", f"redis://127.0.0.1:{rp}/0")

    return env


def _run_alembic_upgrade(*, python_exe: str, workdir: str, env: dict[str, str], progress_cb=None) -> dict:
    cmd = [python_exe, "-m", "alembic", "upgrade", "head"]
    if progress_cb:
        progress_cb("db", "panel", {"action": "alembic_upgrade", "cmd": " ".join(cmd)})
    try:
        subprocess.check_call(cmd, cwd=workdir, env=env)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e), "cmd": " ".join(cmd)}


def _run_ptero_eggs_sync(*, python_exe: str, workdir: str, env: dict[str, str], progress_cb=None) -> dict:
    """Best-effort sync of Ptero-Eggs templates into the database."""
    sentinel = "__PANEL_PTERO_SYNC__"
    code = (
        "import json\n"
        "from app import app, User\n"
        "from ptero_eggs_updater import PteroEggsUpdater\n"
        "with app.app_context():\n"
        "    admin = User.query.filter_by(role='system_admin').first()\n"
        "    if not admin:\n"
        "        print('" + sentinel + "' + json.dumps({'ok': False, 'error': 'no_system_admin_user'}))\n"
        "    else:\n"
        "        stats = PteroEggsUpdater().sync_templates(admin.id)\n"
        "        out = {'ok': bool(stats.get('success')), **stats}\n"
        "        print('" + sentinel + "' + json.dumps(out))\n"
    )
    cmd = [python_exe, "-c", code]
    if progress_cb:
        progress_cb("templates", "panel", {"action": "ptero_eggs_sync", "cmd": " ".join(cmd)})
    try:
        proc = subprocess.run(cmd, cwd=workdir, env=env, capture_output=True, text=True, timeout=1800)
        stdout = (proc.stdout or "").splitlines()
        line = next((ln for ln in reversed(stdout) if ln.startswith(sentinel)), None)
        if line is None:
            return {
                "ok": False,
                "error": "ptero-eggs sync produced no sentinel output",
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "").strip(),
                "stderr": (proc.stderr or "").strip(),
            }
        payload = line[len(sentinel) :].strip()
        try:
            data = json.loads(payload or "{}")
        except Exception:
            data = {"ok": False, "error": "ptero-eggs sync returned invalid JSON", "raw": payload}

        if proc.returncode != 0 and data.get("ok") is not True:
            data.setdefault("returncode", proc.returncode)
            data.setdefault("stderr", (proc.stderr or "").strip())
        return data
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "ptero-eggs sync timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
    venv_path: str | None = None,
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

    uri = (
        db_uri
        or os.environ.get("DATABASE_URL")
        or os.environ.get("SQLALCHEMY_DATABASE_URI")
        or f"postgresql+psycopg2://{os.environ.get('PANEL_DB_USER','paneluser')}:{os.environ.get('PANEL_DB_PASS','panelpass')}@{os.environ.get('PANEL_DB_HOST','127.0.0.1')}:{os.environ.get('PANEL_DB_PORT','5432')}/{os.environ.get('PANEL_DB_NAME','paneldb')}"
    )

    def _redact_db_uri(value: str) -> str:
        if not isinstance(value, str):
            return str(value)
        # Redact password in URIs like: scheme://user:pass@host/db
        # Keep it conservative; if parsing fails, fall back to a simple regex.
        try:
            from urllib.parse import urlsplit, urlunsplit

            parts = urlsplit(value)
            if parts.username and parts.password:
                netloc = parts.netloc
                # Replace ':password@' segment.
                netloc = netloc.replace(f":{parts.password}@", ":***@")
                return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
        except Exception:
            pass
        return re.sub(r"(//[^:/@]+:)([^@]+)(@)", r"\1***\3", value)

    if isinstance(uri, str) and uri.strip().lower().startswith("sqlite"):
        return {"ok": False, "created": False, "error": "SQLite is not supported", "email": email, "password_generated": generated}

    if progress_cb:
        progress_cb(
            "bootstrap",
            "panel",
            {"action": "ensure_default_admin_user", "email": email, "db_uri": _redact_db_uri(uri)},
        )

    try:
        # Import lazily so the installer can still run in minimal environments.
        from flask import Flask
        from app.db import db
        # Import models module to ensure all SQLAlchemy models are registered
        # before calling create_all(). Otherwise the app can 500 due to missing
        # tables (e.g. "no such table") after install.
        import src.panel.models as _panel_models  # noqa: F401
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
    except ModuleNotFoundError as e:
        # Common when running the installer with system Python (e.g. via SSH
        # wizard) before Panel deps are installed. If we have a venv that
        # *does* contain the deps, retry the bootstrap in a subprocess using
        # that interpreter.
        try:
            if venv_path and not os.path.abspath(sys.executable).startswith(os.path.abspath(venv_path)):
                vpy = os.path.join(venv_path, "bin", "python")
                if os.path.exists(vpy):
                    env = os.environ.copy()
                    env.setdefault("DATABASE_URL", uri)
                    env.setdefault("PANEL_ADMIN_EMAIL", email)
                    env.setdefault("PANEL_ADMIN_PASS", password)

                    sentinel = "__PANEL_BOOTSTRAP_RESULT__"
                    code = (
                        "import json, os, sys; "
                        "from tools.installer.core import ensure_default_admin_user; "
                        "res = ensure_default_admin_user(db_uri=os.environ.get('DATABASE_URL')); "
                        f"sys.stdout.write('{sentinel}' + json.dumps(res) + '\\n')"
                    )
                    proc = subprocess.run(
                        [vpy, "-c", code],
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if proc.returncode == 0:
                        try:
                            stdout = (proc.stdout or "").splitlines()
                            # Ignore any extra logs; parse only our sentinel line.
                            line = next((ln for ln in reversed(stdout) if ln.startswith(sentinel)), None)
                            if line is None:
                                # Fallback: attempt parsing the last non-empty line.
                                line = next((ln for ln in reversed(stdout) if ln.strip()), "")
                            if line.startswith(sentinel):
                                line = line[len(sentinel) :]
                            return json.loads(line.strip() or "{}")
                        except Exception:
                            return {
                                "ok": False,
                                "created": False,
                                "error": "default user bootstrap returned non-JSON output",
                                "stdout": (proc.stdout or "").strip(),
                                "stderr": (proc.stderr or "").strip(),
                                "email": email,
                                "password_generated": generated,
                            }
                    return {
                        "ok": False,
                        "created": False,
                        "error": "default user bootstrap failed in venv",
                        "returncode": proc.returncode,
                        "stdout": (proc.stdout or "").strip(),
                        "stderr": (proc.stderr or "").strip(),
                        "email": email,
                        "password_generated": generated,
                    }
        except Exception:
            # Fall through to the generic error handling below.
            pass

        if progress_cb:
            progress_cb("bootstrap", "panel", {"action": "ensure_default_admin_user_failed", "error": str(e)})
        return {"ok": False, "created": False, "error": str(e), "email": email, "password_generated": generated}
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
    install_requirements: bool = True,
    *,
    install_extras: bool = False,
    require_extras: bool = False,
    create_default_user: bool = True,
    admin_email: str | None = None,
    admin_password: str | None = None,
    db_uri: str | None = None,
    environment: str | None = None,
    redis_port: int | None = None,
    panel_env_file: str | None = None,
    db_search_path: str | None = None,
    sync_ptero_eggs: bool | None = None,
    require_ptero_eggs: bool = False,
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
    python_failed = None

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

                # Configure nginx to reverse-proxy :80 -> Panel :8080.
                # Do this even when nginx is already installed (skipped=True).
                if not dry_run and (res.get("installed") or res.get("skipped")):
                    try:
                        cfg_res = ng.configure_panel_reverse_proxy(
                            domain=(domain or "localhost"),
                            upstream_host="127.0.0.1",
                            upstream_port=8080,
                            listen_port=80,
                            dry_run=dry_run,
                            elevate=elevate,
                        )
                    except Exception as e:
                        cfg_res = {"ok": False, "error": str(e)}

                    actions.append({"component": "nginx", "result": {"panel_proxy": cfg_res}})
                    if progress_cb:
                        progress_cb("config", c, {"panel_proxy": cfg_res})

                    if isinstance(cfg_res, dict) and not cfg_res.get("ok", False):
                        errors.append({"component": "nginx", "error": "failed to configure panel reverse proxy", "details": cfg_res})

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
                if not dry_run:
                    if res.get("installed"):
                        try:
                            from .state import add_action
                            add_action({"component": "python", "meta": res})
                        except Exception:
                            log.debug("Failed to write install state for pythonenv")
                    else:
                        python_failed = res
                        err = {
                            "component": "python",
                            "error": res.get("error") or "python venv creation failed",
                            "details": res,
                        }
                        errors.append(err)
                        if progress_cb:
                            progress_cb("error", c, err)
                        # Hard-blocker: don't proceed to panel bootstrap/auto-start without a working venv.
                        break

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

    if (not dry_run) and python_failed:
        return {"status": "error", "actions": actions, "errors": errors}

    env_file = panel_env_file
    if auto_start or create_default_user:
        # Persist Panel runtime configuration so the service starts with the correct DB/secret/env.
        if not env_file:
            env_file = "/etc/panel/panel.env" if platform.system() == "Linux" else os.path.abspath("panel.env")

        panel_env = _build_panel_env(
            env_name=(environment or os.environ.get("FLASK_ENV") or "development"),
            domain=(domain or "localhost"),
            db_uri=db_uri,
            redis_port=redis_port,
            db_search_path=db_search_path,
        )

        if dry_run:
            env_res = {"ok": True, "dry_run": True, "path": env_file, "keys": sorted(panel_env.keys())}
        else:
            env_res = _write_env_file(env_file, panel_env)

        actions.append({"component": "panel", "result": {"env_file": env_res}})
        if progress_cb:
            progress_cb("config", "panel", {"env_file": env_res})
        if isinstance(env_res, dict) and not env_res.get("ok", False):
            errors.append({"component": "panel", "error": "failed to write env file", "details": env_res})
            return {"status": "error", "actions": actions, "errors": errors}

        # Apply to current process so subsequent steps use the same config.
        for k, v in panel_env.items():
            os.environ[str(k)] = str(v)

        # Best-effort: if an existing systemd unit is present, ensure it loads
        # the same EnvironmentFile we just wrote. This prevents stale DB creds
        # when the service predates the installer.
        try:
            if env_file:
                _best_effort_ensure_systemd_env_file(
                    unit_name="panel-gunicorn.service",
                    env_file=env_file,
                )
        except Exception:
            pass

        # If postgres is selected, ensure the app DB/user exist using the
        # resolved PANEL_DB_* env values (idempotent). This must work even
        # when `db_uri` was not explicitly provided.
        if (not dry_run) and ("postgres" in components):
            try:
                db_name = os.environ.get("PANEL_DB_NAME", "paneldb")
                db_user = os.environ.get("PANEL_DB_USER", "paneluser")
                db_pass = os.environ.get("PANEL_DB_PASS", "")
                db_host = os.environ.get("PANEL_DB_HOST", "127.0.0.1")
                db_port = os.environ.get("PANEL_DB_PORT", "5432")

                setup_res = pg.setup_database(
                    db_name=db_name,
                    db_user=db_user,
                    db_pass=db_pass or None,
                )
                actions.append({"component": "postgres", "result": {"setup_database": setup_res}})
                if progress_cb:
                    progress_cb("config", "postgres", {"setup_database": setup_res})

                # Fail fast if we still cannot connect as the app role.
                verify_res = pg.verify_connection(
                    db_name=db_name,
                    db_user=db_user,
                    db_pass=db_pass,
                    db_host=db_host,
                    db_port=db_port,
                )
                actions.append({"component": "postgres", "result": {"verify_connection": verify_res}})
                if progress_cb:
                    progress_cb("check", "postgres", {"verify_connection": verify_res})
                if not verify_res.get("ok"):
                    errors.append({
                        "component": "postgres",
                        "error": "database connection failed for app role",
                        "details": {
                            **verify_res,
                            "hint": "Check /etc/panel/panel.env PANEL_DB_USER/PANEL_DB_PASS, and ensure pg_hba.conf allows password auth for 127.0.0.1.",
                        },
                    })
                    return {"status": "error", "actions": actions, "errors": errors}
            except Exception as e:
                setup_res = {"created": False, "error": str(e)}
                actions.append({"component": "postgres", "result": {"setup_database": setup_res}})
                if progress_cb:
                    progress_cb("config", "postgres", {"setup_database": setup_res})

        # Ensure Python requirements exist before DB init/migrations.
        if not dry_run:
            try:
                from .py_requirements import (
                    find_panel_requirements_file,
                    check_requirements_installed,
                    install_requirements as _install_requirements,
                )
                from pathlib import Path

                req_path = find_panel_requirements_file()
                if not req_path:
                    req_res = {"ok": False, "error": "panel requirements file not found"}
                else:
                    req_res = check_requirements_installed(
                        venv_path=venv_path, requirements_path=req_path
                    )
                    if (not req_res.get("ok")) and install_requirements:
                        if progress_cb:
                            progress_cb(
                                "pip",
                                "panel",
                                {"action": "install_requirements", "requirements": req_path},
                            )
                        pip_res = _install_requirements(
                            venv_path=venv_path, requirements_path=req_path
                        )
                        if progress_cb:
                            progress_cb(
                                "pip",
                                "panel",
                                {"action": "install_requirements_result", **pip_res},
                            )
                        req_res = check_requirements_installed(
                            venv_path=venv_path, requirements_path=req_path
                        )
                        if not pip_res.get("ok"):
                            req_res.setdefault("pip_install", pip_res)

                actions.append({"component": "panel", "result": {"requirements": req_res}})
                if progress_cb:
                    progress_cb("requirements", "panel", req_res)
                if not req_res.get("ok"):
                    errors.append(
                        {
                            "component": "panel",
                            "error": "python requirements not satisfied",
                            "details": req_res,
                        }
                    )
                    return {"status": "error", "actions": actions, "errors": errors}

                # Optional: install heavyweight extras that enable advanced features.
                # Keep base install reliable: extras are best-effort and do not fail the install.
                if install_extras and install_requirements:
                    repo_root = Path(__file__).resolve().parents[2]
                    optional_files = [
                        repo_root / "requirements" / "requirements-extras.txt",
                        repo_root / "requirements" / "requirements-ml.txt",
                    ]
                    for opt in optional_files:
                        opt_path = str(opt)
                        if not opt.exists():
                            continue

                        # TensorFlow wheels are commonly unavailable on musl (e.g. Alpine).
                        try:
                            if opt.name == "requirements-ml.txt":
                                import platform as _pf

                                libc = (_pf.libc_ver()[0] or "").lower()
                                if libc and "musl" in libc:
                                    res = {
                                        "ok": True,
                                        "skipped": True,
                                        "requirements": opt_path,
                                        "reason": "ml optional requirements skipped on musl-based systems (TensorFlow wheels often unavailable)",
                                    }
                                    actions.append({"component": "panel", "result": {"optional_requirements": res}})
                                    if progress_cb:
                                        progress_cb("requirements", "panel", res)
                                    continue
                        except Exception:
                            pass

                        opt_res = check_requirements_installed(venv_path=venv_path, requirements_path=opt_path)
                        if (not opt_res.get("ok")):
                            if progress_cb:
                                progress_cb(
                                    "pip",
                                    "panel",
                                    {"action": "install_optional_requirements", "requirements": opt_path},
                                )
                            pip_res = _install_requirements(venv_path=venv_path, requirements_path=opt_path)
                            if progress_cb:
                                progress_cb(
                                    "pip",
                                    "panel",
                                    {"action": "install_optional_requirements_result", **pip_res},
                                )
                            opt_res = check_requirements_installed(venv_path=venv_path, requirements_path=opt_path)
                            if not pip_res.get("ok"):
                                opt_res.setdefault("pip_install", pip_res)

                        # Record the result but do not fail the install.
                        actions.append({"component": "panel", "result": {"optional_requirements": opt_res}})
                        if progress_cb:
                            progress_cb("requirements", "panel", opt_res)

                        if require_extras and (not opt_res.get("ok")):
                            errors.append(
                                {
                                    "component": "panel",
                                    "error": "optional requirements not satisfied",
                                    "details": opt_res,
                                }
                            )
                            return {"status": "error", "actions": actions, "errors": errors}
            except Exception as e:
                errors.append({"component": "panel", "error": "requirements check failed", "details": str(e)})
                return {"status": "error", "actions": actions, "errors": errors}

            # Run DB migrations.
            py = os.path.join(venv_path, "bin", "python")
            if not os.path.exists(py):
                py = "python"
            db_res = _run_alembic_upgrade(python_exe=py, workdir=os.getcwd(), env=os.environ.copy(), progress_cb=progress_cb)
            actions.append({"component": "panel", "result": {"db_migrate": db_res}})
            if progress_cb:
                progress_cb("db", "panel", db_res)
            if not db_res.get("ok"):
                errors.append({"component": "panel", "error": "database migration failed", "details": db_res})
                return {"status": "error", "actions": actions, "errors": errors}

            # Ensure a default admin user exists so the UI is accessible.
            if create_default_user:
                try:
                    user_res = ensure_default_admin_user(
                        admin_email=admin_email,
                        admin_password=admin_password,
                        db_uri=db_uri,
                        venv_path=venv_path,
                        progress_cb=progress_cb,
                    )
                    actions.append({"component": "panel", "result": {"default_user": user_res}})
                    if progress_cb:
                        progress_cb("bootstrap", "panel", user_res)
                    # Best-effort: do not fail the install if default user
                    # creation cannot run in this environment.
                except Exception as e:
                    if progress_cb:
                        progress_cb("bootstrap", "panel", {"ok": False, "created": False, "error": str(e)})

            # Optional: Sync Ptero-Eggs templates so server creation can seed from eggs.
            do_sync = sync_ptero_eggs
            if do_sync is None:
                do_sync = bool(install_extras)
            if do_sync:
                try:
                    sync_res = _run_ptero_eggs_sync(
                        python_exe=py,
                        workdir=os.getcwd(),
                        env=os.environ.copy(),
                        progress_cb=progress_cb,
                    )
                    actions.append({"component": "panel", "result": {"ptero_eggs_sync": sync_res}})
                    if progress_cb:
                        progress_cb("templates", "panel", sync_res)
                    if require_ptero_eggs and (not sync_res.get("ok")):
                        errors.append({"component": "panel", "error": "ptero-eggs sync failed", "details": sync_res})
                        return {"status": "error", "actions": actions, "errors": errors}
                except Exception as e:
                    sync_res = {"ok": False, "error": str(e)}
                    actions.append({"component": "panel", "result": {"ptero_eggs_sync": sync_res}})
                    if progress_cb:
                        progress_cb("templates", "panel", sync_res)
                    if require_ptero_eggs:
                        errors.append({"component": "panel", "error": "ptero-eggs sync failed", "details": sync_res})
                        return {"status": "error", "actions": actions, "errors": errors}

    # Attempt to start the Panel app service after install
    if not dry_run and auto_start:
        try:
            name = _service_name("panel")
            from .service_manager import service_exists, manager_available
            if not manager_available():
                # Common in LXC/containers: no systemd bus. Fall back to a
                # detached background process so installs are usable.
                bg_res = _start_panel_background(
                    venv_path=venv_path,
                    workdir=os.getcwd(),
                    port=8080,
                    env_file=env_file,
                )
                if progress_cb:
                    meta = {"service": name, "method": "background", **bg_res}
                    progress_cb("service", "panel", meta if isinstance(meta, dict) else {"service": name, "started": False})
                actions.append({"component": "panel", "result": {"auto_start": bg_res}})
            elif not service_exists(name):
                # Best-effort: create a systemd unit on Linux so auto-start can work.
                created = False
                try:
                    created = _ensure_panel_systemd_unit(
                        venv_path=venv_path,
                        workdir=os.getcwd(),
                        port=8080,
                        env_file=env_file,
                    )
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
