"""PostgreSQL installer helpers (Linux-focused PoC).

Provides:
 - is_installed()
 - install(dry_run=False)
 - setup_database(db_name='panel', db_user='panel', db_pass=None)

This module uses `tools.installer.deps.get_package_manager()` to pick an install command.
"""
import shutil
import subprocess
import logging
import os
import re
from ..deps import get_package_manager

log = logging.getLogger(__name__)


def is_installed():
    return shutil.which("psql") is not None


def install(dry_run=False, target=None, elevate=True):
    """Install PostgreSQL using the detected package manager.

    Returns a dict with details and, when dry_run=True, includes the command to run.
    """
    if is_installed():
        return {"installed": True, "skipped": True, "msg": "psql already available"}

    if not elevate:
        cmd_preview = "apt-get update && apt-get install -y postgresql postgresql-contrib"
        if get_package_manager() and get_package_manager() != "apt":
            cmd_preview = f"install postgresql via {get_package_manager()}"
        return {
            "installed": False,
            "skipped": False,
            "error": "elevation required to install system package 'postgresql'",
            "hint": "Re-run with elevation or install PostgreSQL manually",
            "cmd": cmd_preview,
        }

    pm = get_package_manager()
    if pm in ("apt", None):
        cmd = ["apt-get", "update", "&&", "apt-get", "install", "-y", "postgresql", "postgresql-contrib"]
        shell = True
    elif pm == "dnf":
        cmd = ["dnf", "install", "-y", "postgresql-server", "postgresql-contrib"]
        shell = False
    elif pm == "yum":
        cmd = ["yum", "install", "-y", "postgresql-server", "postgresql-contrib"]
        shell = False
    elif pm == "pacman":
        cmd = ["pacman", "-Sy", "--noconfirm", "postgresql"]
        shell = False
    elif pm == "apk":
        cmd = ["apk", "add", "postgresql", "postgresql-contrib"]
        shell = False
    elif pm == "brew":
        cmd = ["brew", "install", "postgresql"]
        shell = False
    elif pm in ("choco", "winget"):
        if pm == "choco":
            cmd = ["choco", "install", "postgresql", "-y"]
        else:
            cmd = ["winget", "install", "--id", "PostgreSQL", "-e"]
        shell = False
    else:
        # Unknown or non-Linux package manager, provide an informative message
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

        # Try starting/enabling service using systemctl if present
        try:
            subprocess.check_call(["systemctl", "enable", "postgresql"])
            subprocess.check_call(["systemctl", "start", "postgresql"])
        except Exception:
            log.debug("systemctl not available or enabling service failed; continuing")

        return {"installed": True, "skipped": False, "msg": "postgresql installed"}
    except subprocess.CalledProcessError as e:
        return {"installed": False, "error": str(e), "cmd": cmd_str}


def setup_database(db_name='panel', db_user='panel', db_pass=None):
    """Create or update a database + role for the Panel app.

    This is intended to be idempotent:
    - creates the role if missing
    - resets the role password if provided
    - creates the database if missing
    - ensures the database owner is the role

    NOTE: Requires superuser access via `sudo -u postgres`.
    """

    def _validate_ident(value: str, field: str) -> str | None:
        v = (value or "").strip()
        if not v:
            return f"{field} must not be empty"
        # Conservative identifier validation: avoids shell/SQL injection.
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", v):
            return f"{field} contains unsupported characters: {v!r}"
        return None

    err = _validate_ident(db_name, "db_name") or _validate_ident(db_user, "db_user")
    if err:
        return {"created": False, "error": err}

    if db_pass is None:
        db_pass = ""

    # Build commands as lists to avoid shell interpolation.
    psql_base = ["sudo", "-u", "postgres", "psql", "-X", "-v", "ON_ERROR_STOP=1"]
    psql_tac = psql_base + ["-tAc"]

    try:
        # 1) Ensure role exists; set password when provided.
        sql_role = (
            "DO $$\n"
            "DECLARE\n"
            "  v_user text := :'db_user';\n"
            "  v_pass text := :'db_pass';\n"
            "BEGIN\n"
            "  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = v_user) THEN\n"
            "    IF v_pass <> '' THEN\n"
            "      EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', v_user, v_pass);\n"
            "    ELSE\n"
            "      EXECUTE format('CREATE ROLE %I LOGIN', v_user);\n"
            "    END IF;\n"
            "  ELSE\n"
            "    IF v_pass <> '' THEN\n"
            "      EXECUTE format('ALTER ROLE %I WITH LOGIN PASSWORD %L', v_user, v_pass);\n"
            "    ELSE\n"
            "      EXECUTE format('ALTER ROLE %I WITH LOGIN', v_user);\n"
            "    END IF;\n"
            "  END IF;\n"
            "END\n"
            "$$;"
        )

        subprocess.check_call(
            psql_base
            + [
                "-v",
                f"db_user={db_user}",
                "-v",
                f"db_pass={db_pass}",
                "-tAc",
                sql_role,
            ]
        )

        # 2) Ensure database exists.
        exists = subprocess.check_output(
            psql_tac + [f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"],
            text=True,
        ).strip()
        if not exists:
            subprocess.check_call(
                ["sudo", "-u", "postgres", "psql", "-X", "-v", "ON_ERROR_STOP=1", "-c", f"CREATE DATABASE {db_name} OWNER {db_user};"]
            )

        # 3) Ensure ownership + basic privileges.
        subprocess.check_call(
            ["sudo", "-u", "postgres", "psql", "-X", "-v", "ON_ERROR_STOP=1", "-c", f"ALTER DATABASE {db_name} OWNER TO {db_user};"]
        )
        subprocess.check_call(
            ["sudo", "-u", "postgres", "psql", "-X", "-v", "ON_ERROR_STOP=1", "-c", f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"]
        )

        # 4) Ensure the role finds tables in public by default.
        try:
            subprocess.check_call(
                [
                    "sudo",
                    "-u",
                    "postgres",
                    "psql",
                    "-X",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    f"ALTER ROLE {db_user} IN DATABASE {db_name} SET search_path = public;",
                ]
            )
        except Exception:
            # Not fatal; app also forces search_path at connect-time.
            pass

        return {"created": True, "role": db_user, "database": db_name}
    except Exception as e:
        return {"created": False, "error": str(e), "role": db_user, "database": db_name}


def verify_connection(*, db_name: str, db_user: str, db_pass: str, db_host: str = "127.0.0.1", db_port: str = "5432") -> dict:
    """Verify we can connect as the application role.

    Uses `psql` with PGPASSWORD to avoid adding extra Python deps.
    """
    try:
        if not shutil.which("psql"):
            return {"ok": False, "error": "psql not found"}
        env = os.environ.copy()
        env["PGPASSWORD"] = db_pass or ""
        cmd = [
            "psql",
            f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-tAc",
            "SELECT 1",
        ]
        subprocess.check_call(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def uninstall(preserve_data=True, dry_run=False):
    """Uninstall PostgreSQL (best-effort). If preserve_data=True, only stops services and disables autostart; otherwise remove packages."""
    if dry_run:
        return {"uninstalled": False, "cmd": "(dry-run) stop/disable postgresql; optionally remove packages"}

    out = {"stopped": False, "disabled": False, "packages_removed": False}
    try:
        subprocess.check_call(["systemctl", "stop", "postgresql"])  # may fail on some systems
        out["stopped"] = True
    except Exception:
        pass

    try:
        subprocess.check_call(["systemctl", "disable", "postgresql"])  # may fail
        out["disabled"] = True
    except Exception:
        pass

    if not preserve_data:
        pm = get_package_manager()
        try:
            if pm in ("apt", None):
                subprocess.check_call(["apt-get", "remove", "-y", "postgresql", "postgresql-contrib"])
            elif pm == "dnf":
                subprocess.check_call(["dnf", "remove", "-y", "postgresql-server"])
            elif pm == "yum":
                subprocess.check_call(["yum", "remove", "-y", "postgresql-server"])
            elif pm == "pacman":
                subprocess.check_call(["pacman", "-Rns", "--noconfirm", "postgresql"])            
            out["packages_removed"] = True
        except Exception as e:
            out["packages_error"] = str(e)

    return out
