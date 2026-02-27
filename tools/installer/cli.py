import argparse
import logging
import json
import os
import sys
from .core import install_all, uninstall_all, start_component_service, stop_component_service, get_component_service_status
from .db_utils import build_postgres_uri, is_postgres_uri, validate_postgres_ssl_options

log = logging.getLogger(__name__)


def build_parser():
    p = argparse.ArgumentParser(prog="panel-installer")
    sub = p.add_subparsers(dest="cmd")

    ip = sub.add_parser("install", help="Install panel and components")
    ip.add_argument("--domain", default="localhost", help="Panel domain name")
    ip.add_argument("--components", default=",".join(["postgres","redis","nginx","python"]))
    ip.add_argument("--venv-path", default="/opt/panel/venv", help="Target path for Python venv when installing python component")
    ip.add_argument("--dry-run", action="store_true")
    ip.add_argument("--no-elevate", action="store_true", help="Do not attempt elevation (useful for CI)")
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
    ip.add_argument("--json", action="store_true", help="Emit structured JSON output")

    up = sub.add_parser("uninstall", help="Uninstall panel")
    up.add_argument("--preserve-data", action="store_true")
    up.add_argument("--dry-run", action="store_true")
    up.add_argument("--no-elevate", action="store_true", help="Do not require admin for dry-run")
    up.add_argument("--components", default=None, help="Comma-separated components to stop before rollback (e.g. postgres,redis)")
    up.add_argument("--json", action="store_true", help="Emit structured JSON output")

    cp = sub.add_parser("check", help="Check system dependencies")
    cp.add_argument("--json", action="store_true", help="Emit structured JSON output")

    sp = sub.add_parser("service", help="Manage component services")
    sp.add_argument("action", choices=["start", "stop", "status"], help="Service action")
    sp.add_argument("--components", default=",".join(["postgres","redis","nginx"]), help="Comma-separated components to act on")
    sp.add_argument("--json", action="store_true", help="Emit structured JSON output")

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "install":
        comps = [c.strip() for c in args.components.split(",") if c.strip()]
        admin_password = args.admin_password

        db_password = getattr(args, "db_password", None)

        # Stdin parsing: if both are requested, read admin password first then DB password.
        if getattr(args, "admin_password_stdin", False):
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
            venv_path=args.venv_path,
            auto_start=args.auto_start,
            create_default_user=args.create_default_user,
            admin_email=args.admin_email,
            admin_password=admin_password,
            db_uri=db_uri,
            db_search_path=getattr(args, "db_search_path", None),
        )
        print(json.dumps(result) if args.json else result)
    elif args.cmd == "uninstall":
        comps = None
        if getattr(args, "components", None):
            comps = [c.strip() for c in args.components.split(",") if c.strip()]
        result = uninstall_all(preserve_data=args.preserve_data, dry_run=args.dry_run, components=comps, elevate=(not args.no_elevate))
        print(json.dumps(result) if args.json else result)
    elif args.cmd == "check":
        from .deps import check_system_deps, suggest_install_commands
        missing = check_system_deps()
        if args.json:
            sugg = suggest_install_commands(missing) if missing else None
            print(json.dumps({"missing": missing, "suggestion": sugg}))
        else:
            print(missing)
            if missing:
                sugg = suggest_install_commands(missing)
                if sugg:
                    print("\nSuggested install command:\n", sugg)
                else:
                    print("\nNo known package manager detected to suggest commands.")
    elif args.cmd == "service":
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
        output = {"status": "ok", "results": results}
        print(json.dumps(output) if args.json else output)
    else:
        parser.print_help()
