"""SSH-friendly terminal installer.

Provides a text-based flow suitable for remote/terminal sessions.
Streams progress and returns JSON summaries for automation.
"""
import argparse
import getpass
import re
import json
import logging
import os
import shutil
import sys
from typing import Any, Dict, List, Optional

from .core import install_all, uninstall_all, start_component_service, stop_component_service, get_component_service_status
from .db_utils import build_postgres_uri, is_postgres_uri, validate_postgres_ssl_options
from .deps import check_system_deps, suggest_install_commands

log = logging.getLogger(__name__)


def _progress_printer(step: str, component: str, meta: Dict[str, Any]):
    try:
        # Compact, machine-readable progress lines
        payload = {"step": step, "component": component, "meta": meta}
        print("PROGRESS:", json.dumps(payload, separators=(",", ":")))
    except Exception:
        print(f"PROGRESS: {step} {component} {meta}")


def build_parser():
    p = argparse.ArgumentParser(prog="panel-installer-ssh", description="Panel Installer (SSH/Terminal)")
    sub = p.add_subparsers(dest="cmd")

    ip = sub.add_parser("install", help="Install panel and components (streams progress)")
    ip.add_argument("--domain", default="localhost", help="Panel domain name")
    ip.add_argument("--components", default=",".join(["postgres","redis","nginx","python"]))
    ip.add_argument("--venv-path", default="/opt/panel/venv", help="Target path for Python venv when installing python component")
    ip.add_argument("--dry-run", action="store_true")
    ip.add_argument("--no-elevate", action="store_true", help="Do not attempt elevation (useful for CI)")
    ip.add_argument("--json", action="store_true", help="Emit final result JSON only (progress still streams)")
    ip.add_argument("--auto-start", dest="auto_start", action="store_true", help="Auto-start Panel app service after install")
    ip.add_argument("--no-auto-start", dest="auto_start", action="store_false", help="Do not auto-start Panel app service after install")
    ip.set_defaults(auto_start=True)

    ip.add_argument(
        "--create-default-user",
        dest="create_default_user",
        action="store_true",
        help="Create a default system admin user if none exists",
    )
    ip.add_argument(
        "--no-create-default-user",
        dest="create_default_user",
        action="store_false",
        help="Do not create a default system admin user",
    )
    ip.set_defaults(create_default_user=True)
    ip.add_argument("--admin-email", default=None, help="Admin username/email to create (Panel uses email as login)")
    ip.add_argument(
        "--admin-password",
        default=None,
        help="Admin password to set (WARNING: may be visible in shell history / process list). Prefer --admin-password-stdin.",
    )
    ip.add_argument(
        "--admin-password-stdin",
        action="store_true",
        help="Read admin password from stdin (single line).",
    )

    ip.add_argument(
        "--db-uri",
        default=None,
        help="Full PostgreSQL SQLAlchemy URL (e.g. postgresql+psycopg2://user:pass@host:5432/db?sslmode=require).",
    )
    ip.add_argument("--db-host", default=None, help="PostgreSQL host")
    ip.add_argument("--db-port", type=int, default=None, help="PostgreSQL port")
    ip.add_argument("--db-name", default=None, help="PostgreSQL database name")
    ip.add_argument("--db-user", default=None, help="PostgreSQL username")
    ip.add_argument(
        "--db-password",
        default=None,
        help="PostgreSQL password (WARNING: may be visible in shell history / process list). Prefer --db-password-stdin.",
    )
    ip.add_argument(
        "--db-password-stdin",
        action="store_true",
        help="Read PostgreSQL password from stdin (single line).",
    )
    ip.add_argument(
        "--db-search-path",
        default=None,
        help="PostgreSQL schema search_path (sets PANEL_DB_SEARCH_PATH; e.g. 'public' or 'my_schema,public').",
    )
    ip.add_argument(
        "--db-sslmode",
        default=None,
        help="PostgreSQL sslmode (disable|allow|prefer|require|verify-ca|verify-full)",
    )
    ip.add_argument("--db-sslrootcert", default=None, help="Path to CA/root certificate")
    ip.add_argument("--db-sslcert", default=None, help="Path to client certificate")
    ip.add_argument("--db-sslkey", default=None, help="Path to client key")

    up = sub.add_parser("uninstall", help="Uninstall panel via recorded state (streams progress)")
    up.add_argument("--preserve-data", action="store_true")
    up.add_argument("--dry-run", action="store_true")
    up.add_argument("--no-elevate", action="store_true", help="Do not require admin for dry-run")
    up.add_argument("--components", default=None, help="Comma-separated components to stop before rollback (e.g. postgres,redis)")
    up.add_argument("--json", action="store_true", help="Emit final result JSON only (progress still streams)")

    sp = sub.add_parser("service", help="Manage component services")
    sp.add_argument("action", choices=["start", "stop", "status"], help="Service action")
    sp.add_argument("--components", default=",".join(["postgres","redis","nginx"]), help="Comma-separated components to act on")

    cp = sub.add_parser("check", help="Check system dependencies")

    wz = sub.add_parser("wizard", help="Interactive guided installer (SSH)")
    wz.add_argument("--json", action="store_true", help="Emit final result JSON only (progress still streams)")

    return p


def main(argv: Optional[List[str]] = None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "install":
        comps = [c.strip() for c in args.components.split(",") if c.strip()]

        admin_password = args.admin_password
        db_password = getattr(args, "db_password", None)

        # Read from stdin in a stable order when both are requested.
        if getattr(args, "admin_password_stdin", False):
            # Read a single line from stdin. This avoids exposing the password in argv.
            admin_password = (sys.stdin.readline() or "").rstrip("\n")
        if getattr(args, "db_password_stdin", False):
            db_password = (sys.stdin.readline() or "").rstrip("\n")

        ssl_err = validate_postgres_ssl_options(
            sslmode=getattr(args, "db_sslmode", None),
            sslrootcert=getattr(args, "db_sslrootcert", None),
            sslcert=getattr(args, "db_sslcert", None),
            sslkey=getattr(args, "db_sslkey", None),
        )
        if ssl_err:
            parser.error(ssl_err)

        db_uri = None
        db_uri_raw = (getattr(args, "db_uri", None) or "").strip() or None
        any_db_parts = any(
            getattr(args, name, None)
            for name in (
                "db_host",
                "db_port",
                "db_name",
                "db_user",
                "db_password",
                "db_sslmode",
                "db_sslrootcert",
                "db_sslcert",
                "db_sslkey",
            )
        )
        if db_uri_raw:
            if any_db_parts:
                parser.error("--db-uri cannot be combined with --db-host/--db-port/--db-user/--db-password or SSL flags")
            if not is_postgres_uri(db_uri_raw):
                parser.error("Only PostgreSQL is supported for --db-uri")
            db_uri = db_uri_raw
        elif any_db_parts:
            host = (getattr(args, "db_host", None) or os.environ.get("PANEL_DB_HOST") or "127.0.0.1").strip()
            port = int(getattr(args, "db_port", None) or os.environ.get("PANEL_DB_PORT") or 5432)
            name = (getattr(args, "db_name", None) or os.environ.get("PANEL_DB_NAME") or "paneldb").strip()
            user = (getattr(args, "db_user", None) or os.environ.get("PANEL_DB_USER") or "paneluser").strip()
            password = (db_password if db_password is not None else os.environ.get("PANEL_DB_PASS"))
            if password is None:
                password = "panelpass"
            db_uri = build_postgres_uri(
                host=host,
                port=port,
                db_name=name,
                user=user,
                password=str(password),
                sslmode=getattr(args, "db_sslmode", None),
                sslrootcert=getattr(args, "db_sslrootcert", None),
                sslcert=getattr(args, "db_sslcert", None),
                sslkey=getattr(args, "db_sslkey", None),
            )

        result = install_all(
            args.domain,
            comps,
            elevate=(not args.no_elevate),
            dry_run=args.dry_run,
            progress_cb=_progress_printer,
            venv_path=args.venv_path,
            auto_start=args.auto_start,
            create_default_user=args.create_default_user,
            admin_email=args.admin_email,
            admin_password=admin_password,
            db_uri=db_uri,
            db_search_path=getattr(args, "db_search_path", None),
        )
        print(json.dumps(result) if args.json else result)
        return

    if args.cmd == "uninstall":
        comps = None
        if getattr(args, "components", None):
            comps = [c.strip() for c in args.components.split(",") if c.strip()]
        result = uninstall_all(
            preserve_data=args.preserve_data,
            dry_run=args.dry_run,
            components=comps,
            progress_cb=_progress_printer,
            elevate=(not args.no_elevate),
        )
        print(json.dumps(result) if args.json else result)
        return

    if args.cmd == "service":
        comps = [c.strip() for c in args.components.split(",") if c.strip()]
        results = []
        for c in comps:
            if args.action == "start":
                ok = start_component_service(c)
                results.append({"component": c, "started": ok})
            elif args.action == "stop":
                ok = stop_component_service(c)
                results.append({"component": c, "stopped": ok})
            elif args.action == "status":
                res = get_component_service_status(c)
                results.append({"component": c, **res})
        print({"status": "ok", "results": results})
        return

    if args.cmd == "check":
        missing = check_system_deps()
        print(missing)
        if missing:
            sugg = suggest_install_commands(missing)
            if sugg:
                print("\nSuggested install command:\n", sugg)
            else:
                print("\nNo known package manager detected to suggest commands.")
        return

    if args.cmd == "wizard":
        _run_wizard(json_only=args.json)
        return

    parser.print_help()


def _ask_input(prompt: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or (default or "")


def _ask_yes_no(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    while True:
        val = input(f"{prompt} ({d}): ").strip().lower()
        if not val:
            return default
        if val in ("y", "yes"): return True
        if val in ("n", "no"): return False
        print("Please answer 'y' or 'n'.")


def _parse_components(s: str) -> List[str]:
    return [c.strip() for c in s.split(',') if c.strip()]


def _validate_admin_email(value: str) -> str | None:
    v = (value or "").strip()
    if not v:
        return "Email must not be empty"
    # Keep validation light; Panel uses email as login identifier.
    if "@" not in v or v.startswith("@") or v.endswith("@"): 
        return "Email must look like an email address (e.g. admin@example.com)"
    return None


def _validate_password_complexity(password: str) -> str | None:
    # Mirror src/panel/models.py complexity rules so the installer fails fast.
    if len(password or "") < 12:
        return "Password must be at least 12 characters long"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one digit"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character"
    weak_passwords = {"password", "123456", "qwerty", "admin", "letmein", "password123"}
    if password.lower() in weak_passwords:
        return "Password is too common; choose a stronger password"
    return None


def _ask_admin_credentials(default_email: str = "admin@panel.local") -> tuple[str, str | None, bool]:
    """Return (email, password_or_none, password_generated).

    When password is None, the installer will auto-generate a strong password.
    """
    while True:
        email = _ask_input("Admin username/email (login email)", default=default_email).strip().lower()
        err = _validate_admin_email(email)
        if err:
            print(err)
            continue
        break

    print("Admin password: enter one now, or leave blank to auto-generate.")
    while True:
        pw1 = getpass.getpass("Admin password: ").strip()
        if not pw1:
            return email, None, True
        pw2 = getpass.getpass("Confirm password: ").strip()
        if pw1 != pw2:
            print("Passwords do not match. Try again.")
            continue
        perr = _validate_password_complexity(pw1)
        if perr:
            print(perr)
            continue
        return email, pw1, False


def _validate_pg_ident(value: str, field: str) -> str | None:
    v = (value or "").strip()
    if not v:
        return f"{field} must not be empty"
    # Match installer postgres.setup_database identifier rules.
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", v):
        return f"{field} contains unsupported characters: {v!r}"
    return None


def _ask_postgres_config() -> dict[str, str]:
    """Prompt for Postgres DB settings.

    Returns dict with keys: host, port, name, user, password, password_is_default,
    search_path, sslmode, sslrootcert, sslcert, sslkey.
    """
    host = _ask_input("PostgreSQL host", default=os.environ.get("PANEL_DB_HOST", "127.0.0.1")).strip()
    port = _ask_input("PostgreSQL port", default=os.environ.get("PANEL_DB_PORT", "5432")).strip()
    while True:
        if not port.isdigit() or not (1 <= int(port) <= 65535):
            print("Port must be a number between 1 and 65535")
            port = _ask_input("PostgreSQL port", default="5432").strip()
            continue
        break

    while True:
        name = _ask_input("PostgreSQL database name", default=os.environ.get("PANEL_DB_NAME", "paneldb")).strip()
        err = _validate_pg_ident(name, "db_name")
        if err:
            print(err)
            continue
        break

    while True:
        user = _ask_input("PostgreSQL username", default=os.environ.get("PANEL_DB_USER", "paneluser")).strip()
        err = _validate_pg_ident(user, "db_user")
        if err:
            print(err)
            continue
        break

    # Password can be any string; hide input.
    print("PostgreSQL password: enter one now, or leave blank to use the default 'panelpass'.")
    pw_input = getpass.getpass("PostgreSQL password: ").strip()
    password_is_default = not bool(pw_input)
    password = pw_input or os.environ.get("PANEL_DB_PASS", "panelpass")

    search_path = _ask_input(
        "PostgreSQL search_path (schema)",
        default=os.environ.get("PANEL_DB_SEARCH_PATH", "public"),
    ).strip() or "public"

    sslmode = _ask_input(
        "PostgreSQL sslmode (blank/disable/allow/prefer/require/verify-ca/verify-full)",
        default="",
    ).strip() or None
    sslrootcert = sslcert = sslkey = None
    while True:
        if sslmode and sslmode.lower() in ("verify-ca", "verify-full"):
            sslrootcert = _ask_input("PostgreSQL sslrootcert path", default="").strip() or None
        else:
            sslrootcert = _ask_input("PostgreSQL sslrootcert path (optional)", default="").strip() or None
        sslcert = _ask_input("PostgreSQL sslcert path (optional)", default="").strip() or None
        sslkey = _ask_input("PostgreSQL sslkey path (optional)", default="").strip() or None
        ssl_err = validate_postgres_ssl_options(
            sslmode=sslmode,
            sslrootcert=sslrootcert,
            sslcert=sslcert,
            sslkey=sslkey,
        )
        if ssl_err:
            print(ssl_err)
            # Allow adjusting without re-entering everything else.
            sslmode = _ask_input(
                "PostgreSQL sslmode (blank/disable/allow/prefer/require/verify-ca/verify-full)",
                default=(sslmode or ""),
            ).strip() or None
            continue
        break

    return {
        "host": host,
        "port": port,
        "name": name,
        "user": user,
        "password": password,
        "password_is_default": "true" if password_is_default else "false",
        "search_path": search_path,
        "sslmode": sslmode or "",
        "sslrootcert": sslrootcert or "",
        "sslcert": sslcert or "",
        "sslkey": sslkey or "",
    }


def _run_wizard(json_only: bool = False):
    print("Panel Installer (SSH Wizard)")
    print("This guided flow will help you install or uninstall components.")
    op = _ask_input("Choose operation [install|uninstall]", default="install").lower()
    if op not in ("install", "uninstall"):
        print("Unsupported operation. Aborting.")
        return

    if op == "install":
        domain = _ask_input("Domain", default="localhost")
        comps = _select_components_menu(
            choices=["postgres","redis","nginx","python"],
            preselected=["postgres","redis","nginx","python"],
            allow_empty=False,
        )
        if comps is None or not comps:
            print("No components selected. Aborting.")
            return
        dry_run = _ask_yes_no("Dry-run (simulate only)", default=True)
        no_elevate = _ask_yes_no("Skip elevation/admin", default=True)
        # If no-elevate, warn when system packages are selected and allow quick deselect
        if no_elevate:
            sys_comps = [c for c in comps if c in ("postgres", "redis", "nginx")]
            if sys_comps:
                print("\nNote: Without elevation, system packages may fail to install:")
                print(f"  Selected system components: {', '.join(sys_comps)}")
                print("  Suggest deselecting them or re-running with elevation.")
                if _ask_yes_no("Remove system components from selection now?", default=True):
                    comps = [c for c in comps if c not in sys_comps]
        # Auto-suggest a user-writable venv path when no-elevate is selected
        venv_path = "/opt/panel/venv"
        if "python" in comps:
            try:
                import os as _os
                if no_elevate:
                    home = _os.path.expanduser("~") or "/tmp"
                    suggested = _os.path.join(home, "panel", "venv")
                    venv_path = _ask_input("Python venv path", default=suggested)
                else:
                    venv_path = _ask_input("Python venv path", default=venv_path)
            except Exception:
                # Fallback to original prompt if home detection fails
                venv_path = _ask_input("Python venv path", default=venv_path)
        auto_start = _ask_yes_no("Auto-start Panel app after install", default=True)

        # Optional: allow customizing Postgres DB creds.
        db_uri = None
        db_search_path = None
        pg_cfg = None
        if "postgres" in comps:
            pg_cfg = _ask_postgres_config()
            db_search_path = (pg_cfg.get("search_path") or "public").strip() or "public"
            db_uri = build_postgres_uri(
                host=pg_cfg["host"],
                port=int(pg_cfg["port"]),
                db_name=pg_cfg["name"],
                user=pg_cfg["user"],
                password=pg_cfg["password"],
                sslmode=(pg_cfg.get("sslmode") or None),
                sslrootcert=(pg_cfg.get("sslrootcert") or None),
                sslcert=(pg_cfg.get("sslcert") or None),
                sslkey=(pg_cfg.get("sslkey") or None),
            )

        create_default_user = _ask_yes_no("Create default admin user", default=True)
        admin_email = None
        admin_password = None
        password_generated = False
        if create_default_user:
            admin_email, admin_password, password_generated = _ask_admin_credentials(default_email="admin@panel.local")
        print("\nSummary:")
        print(f"  Operation : install")
        print(f"  Domain    : {domain}")
        print(f"  Components: {', '.join(comps) or '(none)'}")
        if "python" in comps:
            print(f"  venv_path : {venv_path}")
            # Small note when no-elevate is set and venv path appears system-level
            try:
                import os as _os
                if no_elevate:
                    home = _os.path.expanduser("~") or ""
                    system_like = venv_path.startswith(('/opt', '/usr', '/var', '/etc')) and not venv_path.startswith(home)
                    if system_like:
                        print("  Note      : no-elevate + system-level venv path may fail (permissions)")
                        print("              Suggest a user path, e.g., ~/panel/venv")
                        if _ask_yes_no("Change venv path now?", default=True):
                            suggested = _os.path.join(home or "/tmp", "panel", "venv")
                            venv_path = _ask_input("Python venv path", default=suggested)
            except Exception:
                pass
            # Hint when service manager is absent
            try:
                from .service_manager import manager_available
                import platform as _pf
                if not manager_available():
                    osname = _pf.system()
                    print("  Note      : service manager not available")
                    if osname == "Linux":
                        print("              Linux: systemd (systemctl) missing; services won't auto-manage")
                        print("              Options: install systemd or use Docker Compose (docker compose up -d)")
                    elif osname == "Darwin":
                        print("              macOS: brew services not available; consider installing Homebrew")
                    elif osname == "Windows":
                        print("              Windows: Service Control (sc) not available; manage services manually")
            except Exception:
                pass
        print(f"  Dry-run   : {dry_run}")
        print(f"  No-elevate: {no_elevate}")
        if db_uri:
            # Avoid printing credentials.
            print(f"  Postgres  : {pg_cfg['user']}@{pg_cfg['host']}:{pg_cfg['port']}/{pg_cfg['name']}")
            if db_search_path:
                print(f"  Schema    : {db_search_path}")
            sslmode = (pg_cfg.get("sslmode") or "").strip()
            if sslmode:
                print(f"  SSL       : sslmode={sslmode}")
        if create_default_user:
            print(f"  Admin     : {admin_email}")
            print(f"  Password  : {'auto-generate' if password_generated else 'user-provided'}")
        else:
            print(f"  Admin     : (skip default admin creation)")
        if not _ask_yes_no("Proceed?", default=True):
            print("Aborted by user.")
            return

        # If the user requested elevation but we are not admin, do not call
        # install_all() directly. install_all() will re-exec the *same* argv to
        # elevate, which re-runs the wizard and looks like an infinite loop.
        # Instead, re-exec into the non-interactive `install` subcommand with
        # the captured selections so the elevated process performs the install.
        try:
            from .os_utils import is_admin

            if (not no_elevate) and (not dry_run) and (not is_admin()):
                if create_default_user and (not password_generated):
                    print(
                        "\nA custom admin password was provided, but the wizard needs to elevate and cannot safely pass it to the elevated process.\n"
                        "Re-run the wizard already elevated (e.g. 'sudo python3 -m tools.installer --ssh wizard') and try again."
                    )
                    return

                if pg_cfg and (pg_cfg.get("password_is_default") != "true"):
                    print(
                        "\nA custom PostgreSQL password was provided, but the wizard needs to elevate and cannot safely pass it to the elevated process.\n"
                        "Re-run the wizard already elevated (e.g. 'sudo python3 -m tools.installer --ssh wizard') and try again."
                    )
                    return

                elev = shutil.which("pkexec") or shutil.which("sudo")
                if not elev:
                    print(
                        "\nElevation is required but no helper was found (pkexec/sudo).\n"
                        "Re-run as root/admin or choose 'Skip elevation/admin'."
                    )
                    return

                cmd = [
                    sys.executable,
                    "-m",
                    "tools.installer",
                    "--ssh",
                    "install",
                    "--domain",
                    domain,
                    "--components",
                    ",".join(comps),
                ]
                if "python" in comps:
                    cmd += ["--venv-path", venv_path]
                if dry_run:
                    cmd.append("--dry-run")
                if no_elevate:
                    cmd.append("--no-elevate")
                if auto_start:
                    cmd.append("--auto-start")
                else:
                    cmd.append("--no-auto-start")
                if not create_default_user:
                    cmd.append("--no-create-default-user")
                elif admin_email:
                    cmd += ["--admin-email", admin_email]

                if pg_cfg:
                    cmd += [
                        "--db-host",
                        pg_cfg["host"],
                        "--db-port",
                        str(pg_cfg["port"]),
                        "--db-name",
                        pg_cfg["name"],
                        "--db-user",
                        pg_cfg["user"],
                    ]
                    if db_search_path:
                        cmd += ["--db-search-path", db_search_path]
                    sslmode = (pg_cfg.get("sslmode") or "").strip()
                    if sslmode:
                        cmd += ["--db-sslmode", sslmode]
                    for flag, key in (
                        ("--db-sslrootcert", "sslrootcert"),
                        ("--db-sslcert", "sslcert"),
                        ("--db-sslkey", "sslkey"),
                    ):
                        v = (pg_cfg.get(key) or "").strip()
                        if v:
                            cmd += [flag, v]
                if json_only:
                    cmd.append("--json")

                print(
                    f"\nElevation required; re-running install under {os.path.basename(elev)}..."
                )
                # Replace current process; elevated process runs install directly.
                os.execvp(elev, [os.path.basename(elev)] + cmd)
        except Exception as e:
            print(f"\nFailed to elevate and re-run install: {e}")
            return

        result = install_all(
            domain,
            comps,
            elevate=(not no_elevate),
            dry_run=dry_run,
            progress_cb=_progress_printer,
            venv_path=venv_path,
            auto_start=auto_start,
            create_default_user=create_default_user,
            admin_email=admin_email,
            admin_password=admin_password,
            db_uri=db_uri,
            db_search_path=db_search_path,
        )
        print(json.dumps(result) if json_only else result)
        return

    # uninstall
    preserve = _ask_yes_no("Preserve data during uninstall", default=True)
    dry_run = _ask_yes_no("Dry-run (simulate only)", default=True)
    no_elevate = _ask_yes_no("Skip elevation/admin", default=True)
    comps = _select_components_menu(
        choices=["postgres","redis","nginx"],
        preselected=[],
        allow_empty=True,
    )
    # None or empty => implies 'all' for stop phase (or no targeted pre-stop)
    if comps is not None and not comps:
        comps = None
    print("\nSummary:")
    print(f"  Operation : uninstall")
    print(f"  Preserve  : {preserve}")
    print(f"  Dry-run   : {dry_run}")
    print(f"  No-elevate: {no_elevate}")
    if comps:
        print(f"  Pre-stop  : {', '.join(comps)}")
    if not _ask_yes_no("Proceed?", default=True):
        print("Aborted by user.")
        return
    result = uninstall_all(
        preserve_data=preserve,
        dry_run=dry_run,
        components=comps,
        progress_cb=_progress_printer,
        elevate=(not no_elevate),
    )
    print(json.dumps(result) if json_only else result)
    return


def _select_components_menu(choices: List[str], preselected: Optional[List[str]] = None, allow_empty: bool = False) -> Optional[List[str]]:
    """Interactive number-based toggle menu for selecting components.

    - choices: available component names
    - preselected: initial selected items
    - allow_empty: whether empty selection is allowed (returns [])

    Returns list of selected components, [] if allowed and none chosen,
    or None if the user aborts.
    """
    selected = set(preselected or [])
    while True:
        print("\nSelect components (toggle by numbers, 'a' accept, 'n' none, 'q' abort)")
        for idx, name in enumerate(choices, start=1):
            mark = "[x]" if name in selected else "[ ]"
            print(f"  {idx}) {mark} {name}")
        resp = input("Enter numbers (e.g. 1 3), 'a' to accept: ").strip().lower()
        if resp in ("a", ""):  # accept
            if not selected and not allow_empty:
                print("Please select at least one component.")
                continue
            return list(selected)
        if resp in ("q", "quit", "exit"):
            return None
        if resp in ("n", "none"):
            selected.clear()
            if allow_empty:
                return []
            else:
                print("No selection. You can choose numbers or press 'a' to accept once selected.")
                continue
        if resp in ("all", "*", "@"):
            selected = set(choices)
            continue
        # toggle indices
        tokens = [t for t in re.split(r"[\s,]+", resp) if t]
        changed = False
        for t in tokens:
            if t.isdigit():
                i = int(t)
                if 1 <= i <= len(choices):
                    name = choices[i-1]
                    if name in selected:
                        selected.remove(name)
                    else:
                        selected.add(name)
                    changed = True
                else:
                    print(f"Ignoring out-of-range index: {t}")
            else:
                print(f"Ignoring invalid token: {t}")
        if not changed and tokens:
            print("No changes made. Enter valid indices, 'a' to accept, or 'q' to abort.")
